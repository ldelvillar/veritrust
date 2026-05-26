"""Mensajes localizados y factoría de detail estructurado para errores de la API."""

from typing import Any

from app.schemas.errors import ErrorCode, ErrorDetail


_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.MEMORY_LIMIT: (
        "Los servidores están al límite de su capacidad en este momento. "
        "Por favor, inténtalo de nuevo más tarde. Si el problema persiste, "
        "contacta al soporte técnico para que pueda escalar el problema."
    ),
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
    ErrorCode.SERVICE_UNAVAILABLE: (
        "El servicio de análisis no está disponible temporalmente."
    ),
    ErrorCode.URL_EXTRACTION: (
        "No se pudo extraer el contenido de la URL proporcionada."
    ),
    ErrorCode.INVALID_ANALYSIS_ID: "El id de análisis no es válido.",
    ErrorCode.ANALYSIS_NOT_FOUND: "Análisis no encontrado.",
    ErrorCode.ANALYSIS_FETCH_FAILED: "No se pudo recuperar el análisis.",
}


def make_error_detail(
    code: ErrorCode, message: str | None = None
) -> dict[str, Any]:
    """Construye un detail estructurado (dict JSON-ready) para HTTPException.

    Usa el mensaje canónico del código salvo que se pase uno explícito.
    Devolvemos dict porque Starlette serializa el detail con ``json.dumps``,
    que no sabe encodear instancias de Pydantic. El schema sigue siendo
    ``ErrorDetail`` (lo usamos como fuente de validación y para OpenAPI).
    """
    return ErrorDetail(
        code=code, message=message or _MESSAGES[code]
    ).model_dump(mode="json")
