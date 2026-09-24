"""Adaptador HTTP de la entrada de análisis: quién la usa, con qué intake y cómo responde un rechazo."""

from fastapi import Depends, Request
from starlette.responses import JSONResponse

from app.api.dependencies.check_rate_limit import check_rate_limit
from app.core.analysis_lifecycle import AnalysisIntake, AnalysisRefused, Submitter
from app.core.config import get_settings
from app.core.errors import make_error_detail
from app.schemas.errors import ErrorCode

# Estado HTTP de cada motivo de rechazo; un test vigila que cubra REFUSAL_CODES.
REFUSAL_HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.ANALYSIS_NOT_FOUND: 404,
    ErrorCode.ANALYSIS_NOT_RETRYABLE: 409,
    ErrorCode.ANALYSIS_NOT_REANALYZABLE: 409,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.INVALID_FILE: 415,
    ErrorCode.ANALYSIS_SAVE_FAILED: 500,
    ErrorCode.ANALYSIS_FETCH_FAILED: 500,
    ErrorCode.ANALYSIS_RETRY_FAILED: 500,
    ErrorCode.ANALYSIS_REANALYZE_FAILED: 500,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
}


async def web_submitter(user: dict = Depends(check_rate_limit)) -> Submitter:
    """Identifica al usuario web que abre el análisis, tras descontar su rate limit."""
    return Submitter(user_id=user["sub"], origin="web", notify_email=user.get("email"))


async def analysis_intake(request: Request) -> AnalysisIntake:
    """Devuelve la entrada del proceso; sin lifespan, una sin cola que rechaza con 503."""
    intake = getattr(request.app.state, "analysis_intake", None)
    if intake is None:
        # Nunca lanza aquí: un 503 desde una dependencia se adelantaría al 422 del cuerpo.
        return AnalysisIntake(None, max_file_bytes=get_settings().max_file_bytes)
    return intake


def refusal_response(exc: AnalysisRefused) -> JSONResponse:
    """Construye la respuesta HTTP de un rechazo con el detail del contrato de errores."""
    return JSONResponse(
        status_code=REFUSAL_HTTP_STATUS[exc.code],
        content={"detail": make_error_detail(exc.code)},
    )
