"""Tipos del contrato de errores estructurados de la API."""

from enum import Enum

from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Códigos estables que el frontend puede usar para identificar errores."""

    CONNECTION = "CONNECTION"
    INTERNAL = "INTERNAL"
    NO_MEDICAL_CLAIMS = "NO_MEDICAL_CLAIMS"
    ANALYSIS_SAVE_FAILED = "ANALYSIS_SAVE_FAILED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    URL_EXTRACTION = "URL_EXTRACTION"
    INVALID_ANALYSIS_ID = "INVALID_ANALYSIS_ID"
    ANALYSIS_NOT_FOUND = "ANALYSIS_NOT_FOUND"
    ANALYSIS_FETCH_FAILED = "ANALYSIS_FETCH_FAILED"
    ANALYSIS_DELETE_FAILED = "ANALYSIS_DELETE_FAILED"
    HISTORY_FETCH_FAILED = "HISTORY_FETCH_FAILED"
    DASHBOARD_FETCH_FAILED = "DASHBOARD_FETCH_FAILED"
    RATE_LIMIT = "RATE_LIMIT"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    INVALID_TOKEN = "INVALID_TOKEN"
    EXPIRED_TOKEN = "EXPIRED_TOKEN"


class ErrorDetail(BaseModel):
    """Forma del campo `detail` que se envía en HTTPException."""

    code: ErrorCode
    message: str


class ErrorResponse(BaseModel):
    """Cuerpo completo de un error: {"detail": ErrorDetail}.

    Se usa en el parámetro ``responses`` de las rutas para documentar el
    contrato de errores en OpenAPI y, vía openapi-typescript, en el frontend.
    """

    detail: ErrorDetail
