"""Este módulo contiene los mensajes de error que devuelve la API al cliente."""

ERROR_MEMORY_LIMIT = (
    "Los servidores están al límite de su capacidad en este momento. "
    "Por favor, inténtalo de nuevo más tarde. Si el problema persiste, "
    "contacta al soporte técnico para que pueda escalar el problema."
)

ERROR_CONNECTION = (
    "El servidor está en mantenimiento o no responde. "
    "Por favor, inténtalo de nuevo más tarde. Si el problema persiste, "
    "contacta al soporte técnico para que pueda escalar el problema."
)

ERROR_INTERNAL = (
    "Ocurrió un error interno durante el análisis de la noticia. "
    "Por favor, inténtalo de nuevo más tarde. Si el problema persiste, "
    "contacta al soporte técnico para que pueda escalar el problema."
)

ERROR_NO_MEDICAL_CLAIMS = (
    "No se detectaron afirmaciones medicas verificables en el texto."
)
