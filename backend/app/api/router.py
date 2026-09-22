"""Este módulo contiene todas las rutas de la API."""

from fastapi import APIRouter

from app.api.routes.analysis import router as analysis_router
from app.api.routes.config import router as config_router
from app.api.routes.contact import router as contact_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health import router as health_router
from app.api.routes.history import router as history_router
from app.api.routes.share import router as share_router
from app.schemas.errors import ErrorResponse

# El handler de main.py da forma estructurada a los 422; sin esto FastAPI documentaría la suya.
_VALIDATION_ERROR_RESPONSES: dict[int | str, dict] = {422: {"model": ErrorResponse}}

api_router = APIRouter()

api_router.include_router(
    analysis_router,
    prefix="/analysis",
    tags=["Analysis"],
    responses=_VALIDATION_ERROR_RESPONSES,
)
api_router.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["Dashboard"],
    responses=_VALIDATION_ERROR_RESPONSES,
)
api_router.include_router(
    history_router,
    prefix="/history",
    tags=["History"],
    responses=_VALIDATION_ERROR_RESPONSES,
)
api_router.include_router(
    share_router,
    prefix="/shared",
    tags=["Share"],
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
