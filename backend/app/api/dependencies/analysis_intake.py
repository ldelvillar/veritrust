"""HTTP adapter of the analysis intake: who uses it, with which intake, and how a refusal answers."""

from fastapi import Depends, Request
from starlette.responses import JSONResponse

from app.api.dependencies.check_rate_limit import check_rate_limit
from app.api.dependencies.plan import current_plan
from app.core.analysis_lifecycle import AnalysisIntake, AnalysisRefused, Submitter
from app.core.config import get_settings
from app.core.errors import make_error_detail
from app.core.plans import PlanLimits
from app.schemas.errors import ErrorCode

# HTTP status of each refusal reason, which a test keeps in step with REFUSAL_CODES.
REFUSAL_HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.ALLOWANCE_EXHAUSTED: 402,
    ErrorCode.PLAN_REQUIRED: 403,
    ErrorCode.ANALYSIS_NOT_FOUND: 404,
    ErrorCode.ANALYSIS_NOT_RETRYABLE: 409,
    ErrorCode.ANALYSIS_NOT_REANALYZABLE: 409,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.TEXT_TOO_LONG_FOR_PLAN: 413,
    ErrorCode.INVALID_FILE: 415,
    ErrorCode.ANALYSIS_SAVE_FAILED: 500,
    ErrorCode.ANALYSIS_FETCH_FAILED: 500,
    ErrorCode.ANALYSIS_RETRY_FAILED: 500,
    ErrorCode.ANALYSIS_REANALYZE_FAILED: 500,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
}


async def web_submitter(
    user: dict = Depends(check_rate_limit),
    limits: PlanLimits = Depends(current_plan),
) -> Submitter:
    """Identify the web user opening the Analysis and their Plan, after charging their rate limit."""
    return Submitter(
        user_id=user["sub"],
        origin="web",
        limits=limits,
        notify_email=user.get("email"),
    )


async def analysis_intake(request: Request) -> AnalysisIntake:
    """Return the process's intake, or one without a queue that refuses with 503 when there is no lifespan."""
    intake = getattr(request.app.state, "analysis_intake", None)
    if intake is None:
        # Never raise here, as a 503 from a dependency would preempt the body's 422.
        return AnalysisIntake(None, max_file_bytes=get_settings().max_file_bytes)
    return intake


def refusal_response(exc: AnalysisRefused) -> JSONResponse:
    """Build the HTTP response of a refusal with the error contract's detail."""
    return JSONResponse(
        status_code=REFUSAL_HTTP_STATUS[exc.code],
        content={"detail": make_error_detail(exc.code)},
    )
