"""Mensajes localizados y factoría de detail estructurado para errores de la API."""

from typing import Any

from app.schemas.errors import ErrorCode, ErrorDetail

_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.CONNECTION: (
        "Los servidores están en mantenimiento o no responden. "
        "Por favor, inténtalo de nuevo más tarde. Si el problema persiste, "
        "contacta al soporte técnico para que pueda escalar el problema."
    ),
    ErrorCode.INTERNAL: (
        "Ocurrió un error interno durante el análisis de la noticia. "
        "Por favor, inténtalo de nuevo más tarde. Si el problema persiste, "
        "contacta al soporte técnico para que pueda escalar el problema."
    ),
    ErrorCode.NO_MEDICAL_CLAIMS: (
        "No se detectaron afirmaciones medicas verificables en el texto."
    ),
    ErrorCode.ANALYSIS_SAVE_FAILED: (
        "El análisis se completó pero no se pudo guardar. "
        "Por favor, inténtalo de nuevo en unos momentos."
    ),
    ErrorCode.SERVICE_UNAVAILABLE: (
        "El servicio de análisis no está disponible temporalmente."
    ),
    ErrorCode.URL_EXTRACTION: (
        "No se pudo extraer el contenido de la URL proporcionada."
    ),
    ErrorCode.INVALID_ANALYSIS_ID: "El id de análisis no es válido.",
    ErrorCode.ANALYSIS_NOT_FOUND: "Análisis no encontrado.",
    ErrorCode.ANALYSIS_FETCH_FAILED: "No se pudo recuperar el análisis.",
    ErrorCode.ANALYSIS_DELETE_FAILED: "No se pudo eliminar el análisis.",
    ErrorCode.HISTORY_FETCH_FAILED: "No se pudo recuperar el historial de análisis.",
    ErrorCode.DASHBOARD_FETCH_FAILED: "No se pudo recuperar el dashboard.",
    ErrorCode.RATE_LIMIT: (
        "Has superado el límite de peticiones. Intenta de nuevo en un minuto."
    ),
    ErrorCode.UNAUTHENTICATED: "Falta la cabecera de autenticación.",
    ErrorCode.INVALID_TOKEN: "El token de autenticación no es válido.",
    ErrorCode.EXPIRED_TOKEN: "El token de autenticación ha expirado.",
}


def make_error_detail(code: ErrorCode, message: str | None = None) -> dict[str, Any]:
    """
    Construye un detail estructurado (dict JSON-ready) para HTTPException.
    Usa el mensaje canónico del código salvo que se pase uno explícito.
    """
    return ErrorDetail(code=code, message=message or _MESSAGES[code]).model_dump(
        mode="json"
    )
