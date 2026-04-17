"""Este módulo contiene los endpoints relacionados con el dashboard del usuario."""

from fastapi import APIRouter, HTTPException, Depends

from app.schemas.dashboard import (
    DashboardSummaryResponse,
    DashboardKpis,
    DashboardTrendPoint,
    DashboardSourceBreakdownItem,
    DashboardDomainBreakdownItem,
    DashboardAlertItem,
)

from app.api.dependencies.get_current_user import get_current_user
from app.api.database import (
    HistoryDatabaseError,
    get_user_dashboard_summary,
)


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(user=Depends(get_current_user)):
    """Endpoint para obtener métricas agregadas del dashboard del usuario."""
    user_id = user["sub"]

    try:
        summary = get_user_dashboard_summary(user_id=user_id)
    except HistoryDatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail="No se pudo recuperar el dashboard.",
        ) from e

    return DashboardSummaryResponse(
        status="success",
        kpis=DashboardKpis(**summary.kpis.__dict__),
        trend=[DashboardTrendPoint(**point.__dict__) for point in summary.trend],
        source_breakdown=[
            DashboardSourceBreakdownItem(**item.__dict__)
            for item in summary.source_breakdown
        ],
        domain_breakdown=[
            DashboardDomainBreakdownItem(**item.__dict__)
            for item in summary.domain_breakdown
        ],
        alerts=[DashboardAlertItem(**item.__dict__) for item in summary.alerts],
    )
