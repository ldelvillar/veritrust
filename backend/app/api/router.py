"""All the API routes."""

from fastapi import APIRouter

from app.api.routes.account import router as account_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.billing import clerk_webhook_router
from app.api.routes.billing import router as billing_router
from app.api.routes.billing import webhook_router as billing_webhook_router
from app.api.routes.config import router as config_router
from app.api.routes.contact import router as contact_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health import router as health_router
from app.api.routes.history import router as history_router
from app.api.routes.share import router as share_router
from app.schemas.errors import ErrorResponse

# The main.py handler shapes 422s, and without this FastAPI would document its own.
_VALIDATION_ERROR_RESPONSES: dict[int | str, dict] = {422: {"model": ErrorResponse}}

# get_current_user answers 401 for the token or API key and 503 when Clerk does not respond.
_AUTHENTICATED_ERROR_RESPONSES: dict[int | str, dict] = {
    **_VALIDATION_ERROR_RESPONSES,
    401: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}

api_router = APIRouter()

api_router.include_router(
    analysis_router,
    prefix="/analysis",
    tags=["Analysis"],
    responses=_AUTHENTICATED_ERROR_RESPONSES,
)
api_router.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["Dashboard"],
    responses=_AUTHENTICATED_ERROR_RESPONSES,
)
api_router.include_router(
    history_router,
    prefix="/history",
    tags=["History"],
    responses=_AUTHENTICATED_ERROR_RESPONSES,
)
api_router.include_router(
    account_router,
    prefix="/account",
    tags=["Account"],
    responses=_AUTHENTICATED_ERROR_RESPONSES,
)
api_router.include_router(
    share_router,
    prefix="/shared",
    tags=["Share"],
    responses=_VALIDATION_ERROR_RESPONSES,
)
api_router.include_router(
    billing_router,
    prefix="/billing",
    tags=["Billing"],
    responses=_AUTHENTICATED_ERROR_RESPONSES,
)
# Stripe calls the webhook server to server, so there is no user, only the body signature.
api_router.include_router(
    billing_webhook_router,
    prefix="/billing",
    tags=["Billing"],
    responses=_VALIDATION_ERROR_RESPONSES,
)
# Like Stripe's, Clerk calls server to server and is authenticated only by the Svix signature.
api_router.include_router(
    clerk_webhook_router,
    prefix="/webhooks",
    tags=["Webhooks"],
    responses=_VALIDATION_ERROR_RESPONSES,
)
api_router.include_router(
    contact_router,
    prefix="/contact",
    tags=["Contact"],
    responses=_VALIDATION_ERROR_RESPONSES,
)
api_router.include_router(config_router, prefix="/config", tags=["Config"])
api_router.include_router(health_router, tags=["Health"])
