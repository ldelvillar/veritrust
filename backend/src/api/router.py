"""Este módulo contiene todas las rutas de la API."""

from fastapi import APIRouter

from src.api.routes.analysis import router as analysis_router
from src.api.routes.dashboard import router as dashboard_router
from src.api.routes.history import router as history_router


api_router = APIRouter()

api_router.include_router(analysis_router)
api_router.include_router(dashboard_router)
api_router.include_router(history_router)
