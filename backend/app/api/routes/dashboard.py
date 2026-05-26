"""Este módulo contiene los endpoints relacionados con el dashboard del usuario."""

from fastapi import APIRouter, HTTPException, Depends

from app.api.dependencies.get_current_user import get_current_user
from app.schemas.dashboard import DashboardSummaryResponse

from app.db.main import (
    HistoryDatabaseError,
    get_user_dashboard_summary,
)

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(user=Depends(get_current_user)):
    """Endpoint para obtener métricas agregadas del dashboard del usuario."""
    user_id = user["sub"]

    try:
        return get_user_dashboard_summary(user_id=user_id)
    except HistoryDatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail="No se pudo recuperar el dashboard.",
        ) from e
