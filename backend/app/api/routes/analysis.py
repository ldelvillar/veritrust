"""Este módulo contiene los endpoints relacionados con los análisis de noticas."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from redis.exceptions import RedisError

from app.api.dependencies.check_rate_limit import check_rate_limit
from app.api.dependencies.get_current_user import get_current_user
from app.core.errors import make_error_detail
from app.db.history import (
    create_pending_analysis,
    fail_analysis,
    get_user_analysis_by_id,
)
from app.db.pool import DatabaseError
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.history import AnalysisHistoryItem

router = APIRouter()
logger = logging.getLogger(__name__)


_POST_ERROR_RESPONSES: dict[int | str, dict] = {
    401: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}

_GET_ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


@router.post(
    "",
    response_model=AnalysisResponse,
    responses=_POST_ERROR_RESPONSES,
)
async def analyze_news(
    body: AnalysisRequest,
    request: Request,
    user: dict = Depends(check_rate_limit),
):
    """Encola el análisis de una noticia y devuelve su id en estado ``pending``.

    El pipeline multiagente (extracción de URL incluida) es lento, así que no se
    ejecuta dentro del request: se reserva una fila ``pending`` y se encola un
    trabajo en arq que el worker procesa. El cliente navega al detalle y hace
    polling de ``GET /analysis/{id}`` hasta que ``status`` deja de ser ``pending``.
    """
    user_id = user["sub"]

    arq_pool = getattr(request.app.state, "arq_pool", None)
    if arq_pool is None:
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        )

    try:
        analysis_id = await create_pending_analysis(user_id=user_id, request=body)
    except DatabaseError as e:
        logger.exception("No se pudo crear el análisis pendiente")
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_SAVE_FAILED),
        ) from e

    try:
        await arq_pool.enqueue_job(
            "run_analysis",
            analysis_id,
            body.source_type.value,
            body.text,
            str(body.url) if body.url else None,
        )
    except (OSError, RedisError) as e:
        # Sin encolado no hay quien procese la fila: la marcamos failed para que
        # no quede pending indefinidamente y el cliente deje de hacer polling.
        logger.exception("No se pudo encolar el análisis %s", analysis_id)
        try:
            await fail_analysis(
                analysis_id=analysis_id,
                error_code=ErrorCode.SERVICE_UNAVAILABLE.value,
            )
        except DatabaseError:
            logger.exception(
                "No se pudo marcar como failed el análisis %s", analysis_id
            )
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        ) from e

    return {"status": "pending", "analysis_id": analysis_id}


@router.get(
    "/{analysis_id}",
    response_model=AnalysisHistoryItem,
    responses=_GET_ERROR_RESPONSES,
)
async def get_analysis_detail(analysis_id: str, user=Depends(get_current_user)):
    """Endpoint para obtener un análisis específico del usuario autenticado."""
    user_id = user["sub"]

    try:
        # Validación rápida para evitar consultas con ids inválidos.
        UUID(analysis_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=make_error_detail(ErrorCode.INVALID_ANALYSIS_ID),
        ) from e

    try:
        record = await get_user_analysis_by_id(user_id=user_id, analysis_id=analysis_id)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_FETCH_FAILED),
        ) from e

    if not record:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(ErrorCode.ANALYSIS_NOT_FOUND),
        )

    return AnalysisHistoryItem(
        analysis_id=record.analysis_id,
        user_id=record.user_id,
        source_type=record.source_type,
        input_text=record.input_text,
        input_url=record.input_url,
        label=record.label,
        confidence=record.confidence,
        explanation=record.explanation,
        status=record.status,
        error_code=record.error_code,
        created_at=record.created_at,
    )
