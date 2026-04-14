"""Este módulo contiene los endpoints relacionados con el dashboard del usuario."""

from fastapi import APIRouter, HTTPException, Depends

from src.api.utils import get_current_user
from src.api.database import (
    DashboardSummary,
    HistoryDatabaseError,
    get_user_dashboard_summary,
)


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_dashboard_summary(user=Depends(get_current_user)):
    """Endpoint para obtener métricas agregadas del dashboard del usuario."""
    user_id = user["sub"]

    try:
        summary: DashboardSummary = get_user_dashboard_summary(user_id=user_id)
    except HistoryDatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail="No se pudo recuperar el dashboard.",
        ) from e

    return {
        "status": "success",
        "kpis": summary.kpis.__dict__,
        "trend": [point.__dict__ for point in summary.trend],
        "source_breakdown": [item.__dict__ for item in summary.source_breakdown],
        "domain_breakdown": [item.__dict__ for item in summary.domain_breakdown],
        "alerts": [item.__dict__ for item in summary.alerts],
    }
