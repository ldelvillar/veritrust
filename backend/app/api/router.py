"""Este módulo contiene todas las rutas de la API."""

from fastapi import APIRouter

from app.api.routes.analysis import router as analysis_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health import router as health_router
from app.api.routes.history import router as history_router

api_router = APIRouter()

api_router.include_router(analysis_router, prefix="/analysis", tags=["Analysis"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(history_router, prefix="/history", tags=["History"])
api_router.include_router(health_router, tags=["Health"])
