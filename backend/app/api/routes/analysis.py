"""Este módulo contiene los endpoints relacionados con los análisis de noticas."""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.errors import OllamaConnectionError, ainvoke_graph
from app.api.dependencies.check_rate_limit import check_rate_limit
from app.api.dependencies.get_current_user import get_current_user
from app.core.errors import make_error_detail
from app.db.main import (
    HistoryDatabaseError,
    get_user_analysis_by_id,
    save_successful_analysis,
)
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.history import AnalysisHistoryItem
from app.utils.extract_text_from_url import URLExtractionError, extract_text_from_url

router = APIRouter()
logger = logging.getLogger(__name__)


_POST_ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"model": ErrorResponse},
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
    """Endpoint para analizar una noticia utilizando el sistema multiagente."""
    user_id = user["sub"]

    verification_system = getattr(request.app.state, "verification_system", None)
    if verification_system is None:
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        )

    try:
        text = (
            await asyncio.to_thread(extract_text_from_url, str(body.url))
            if body.url
            else body.text
        )
    except URLExtractionError as e:
        raise HTTPException(
            status_code=400,
            detail=make_error_detail(ErrorCode.URL_EXTRACTION, str(e)),
        ) from e

    initial_state: dict[str, object] = {
        "input_text": text,
        "extracted_statements": [],
        "translated_statements": [],
        "label": "",
        "confidence": 0.0,
        "medical_explanation": "",
    }

    try:
        # Ejecutar el grafo (traduce errores conocidos a tipos del dominio)
        result = await ainvoke_graph(verification_system, initial_state)

        # Obtener los resultados
        label = result.get("label") or None
        confidence = result.get("confidence") or None
        explanation = result.get("medical_explanation") or None

        if not explanation:
            raise HTTPException(
                status_code=422,
                detail=make_error_detail(ErrorCode.NO_MEDICAL_CLAIMS),
            )

        # Guardar el análisis exitoso en la base de datos
        analysis_id = await save_successful_analysis(
            user_id=user_id,
            request=body,
            label=str(label),
            confidence=confidence,
            explanation=str(explanation),
        )

        return {
            "status": "success",
            "analysis_id": analysis_id,
            "label": label,
            "confidence": confidence,
            "explanation": explanation,
        }
    except HTTPException:
        raise
    except HistoryDatabaseError as e:
        logger.exception("No se pudo guardar el análisis")
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_SAVE_FAILED),
        ) from e
    except OllamaConnectionError as e:
        logger.exception("No se pudo conectar al servidor de Ollama")
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.CONNECTION),
        ) from e
    except Exception as e:
        logger.exception("Error inesperado al analizar la noticia")
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.INTERNAL),
        ) from e


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
    except HistoryDatabaseError as e:
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
        created_at=record.created_at,
    )
