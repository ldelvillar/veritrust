"""Este módulo contiene los endpoints relacionados con los análisis de noticas."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Request
from src.utils.extract_text_from_url import extract_text_from_url, URLExtractionError
from src.api.database import (
    HistoryDatabaseError,
    get_user_analysis_by_id,
    save_successful_analysis,
)
from src.api.schemas import AnalyzeRequest
from src.api.utils import check_rate_limit, get_current_user
from src.api.messages import (
    ERROR_MEMORY_LIMIT,
    ERROR_CONNECTION,
    ERROR_INTERNAL,
    ERROR_NO_MEDICAL_CLAIMS,
)

router = APIRouter(prefix="/analysis", tags=["Analysis"])
logger = logging.getLogger(__name__)


@router.post("")
def analyze_news(
    body: AnalyzeRequest,
    request: Request,
    user=Depends(get_current_user),
):
    """Endpoint para analizar una noticia utilizando el sistema multiagente."""
    user_id = user["sub"]

    check_rate_limit(user_id)
    verification_system = getattr(request.app.state, "verification_system", None)
    if verification_system is None:
        raise HTTPException(
            status_code=503,
            detail="El servicio de análisis no está disponible temporalmente.",
        )

    try:
        text = extract_text_from_url(str(body.url)) if body.url else body.text
    except URLExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

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
            return {
                "status": "error",
                "message": ERROR_NO_MEDICAL_CLAIMS,
                "explanations": "",
            }

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
    except Exception as e:
        error_msg = str(e).lower()
        logger.exception("Error al analizar la noticia: %s", error_msg)

        # Traducir errores a mensajes para el usuario
        if "model requires more system memory" in error_msg:
            friendly_msg = ERROR_MEMORY_LIMIT
        elif "connection refused" in error_msg or "connect call failed" in error_msg:
            friendly_msg = ERROR_CONNECTION
        else:
            friendly_msg = ERROR_INTERNAL

        raise HTTPException(status_code=500, detail=friendly_msg) from e


@router.get("/{analysis_id}")
def get_analysis_detail(analysis_id: str, user=Depends(get_current_user)):
    """Endpoint para obtener un análisis específico del usuario autenticado."""
    user_id = user["sub"]

    try:
        # Validación rápida para evitar consultas con ids inválidos.
        UUID(analysis_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail="El id de análisis no es válido."
        ) from e

    try:
        record = get_user_analysis_by_id(user_id=user_id, analysis_id=analysis_id)
    except HistoryDatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail="No se pudo recuperar el análisis.",
        ) from e

    if not record:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")

    return {
        "status": "success",
        "item": record.__dict__,
    }
