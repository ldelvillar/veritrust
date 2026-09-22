"""Dependencia que valida el id de análisis de la ruta antes de consultar la base de datos."""

from uuid import UUID

from fastapi import HTTPException

from app.core.errors import make_error_detail
from app.schemas.errors import ErrorCode


async def valid_analysis_id(analysis_id: str) -> str:
    """Devuelve el id de la ruta si es un UUID o responde 400 con INVALID_ANALYSIS_ID."""
    try:
        UUID(analysis_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=make_error_detail(ErrorCode.INVALID_ANALYSIS_ID),
        ) from e

    return analysis_id
