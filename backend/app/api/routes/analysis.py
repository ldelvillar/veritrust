"""Este módulo contiene los endpoints relacionados con los análisis de noticas."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Request
from app.utils.extract_text_from_url import extract_text_from_url, URLExtractionError
from app.db.main import (
    HistoryDatabaseError,
    get_user_analysis_by_id,
    save_successful_analysis,
)
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.schemas.history import AnalysisHistoryItem
from app.api.dependencies.get_current_user import get_current_user
from app.api.dependencies.check_rate_limit import check_rate_limit
from app.schemas.errors import ErrorCode, ErrorResponse
from app.core.errors import make_error_detail

router = APIRouter()
logger = logging.getLogger(__name__)


_POST_ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}

_GET_ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


@router.post(
    "",
    response_model=AnalysisResponse,
    responses=_POST_ERROR_RESPONSES,
)
def analyze_news(
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
        text = extract_text_from_url(str(body.url)) if body.url else body.text
    except URLExtractionError as e:
        raise HTTPException(
            status_code=400,
            detail=make_error_detail(ErrorCode.URL_EXTRACTION, str(e)),
        ) from e

    initial_state = {
        "input_text": text,
        "extracted_statements": [],
        "translated_statements": [],
        "label": "",
        "confidence": "",
        "medical_explanation": "",
    }

    try:
        # Ejecutar el grafo
        result = verification_system.invoke(initial_state)

        # Obtener los resultados
        label = result.get("label", "Indefinida")
        confidence = result.get("confidence", "Indefinida")
        explanation = result.get(
            "medical_explanation", "No se pudo obtener la explicación médica."
        )

        if not explanation:
            raise HTTPException(
                status_code=422,
                detail=make_error_detail(ErrorCode.NO_MEDICAL_CLAIMS),
            )

        # Guardar el análisis exitoso en la base de datos
        analysis_id = save_successful_analysis(
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
    except Exception as e:
        error_msg = str(e).lower()
        logger.exception("Error al analizar la noticia: %s", error_msg)

        # Traducir errores del sistema a códigos para el usuario
        if "model requires more system memory" in error_msg:
            code = ErrorCode.MEMORY_LIMIT
        elif "connection refused" in error_msg or "connect call failed" in error_msg:
            code = ErrorCode.CONNECTION
        else:
            code = ErrorCode.INTERNAL

        raise HTTPException(
            status_code=500,
            detail=make_error_detail(code),
        ) from e


@router.get(
    "/{analysis_id}",
    response_model=AnalysisHistoryItem,
    responses=_GET_ERROR_RESPONSES,
)
def get_analysis_detail(analysis_id: str, user=Depends(get_current_user)):
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
        record = get_user_analysis_by_id(user_id=user_id, analysis_id=analysis_id)
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
