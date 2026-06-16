"""Este módulo contiene los endpoints relacionados con el dashboard del usuario."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies.get_current_user import get_current_user
from app.core.errors import make_error_detail
from app.db.dashboard import get_user_dashboard_summary
from app.db.pool import DatabaseError
from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.errors import ErrorCode, ErrorResponse

router = APIRouter()


_GET_SUMMARY_ERROR_RESPONSES: dict[int | str, dict] = {
    401: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    responses=_GET_SUMMARY_ERROR_RESPONSES,
)
async def get_dashboard_summary(
    trend_days: int = Query(default=14, ge=7, le=90),
    user=Depends(get_current_user),
):
    """Endpoint para obtener métricas agregadas del dashboard del usuario."""
    user_id = user["sub"]

    try:
        return await get_user_dashboard_summary(user_id=user_id, trend_days=trend_days)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.DASHBOARD_FETCH_FAILED),
        ) from e
