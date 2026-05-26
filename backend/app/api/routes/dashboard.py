"""Este módulo contiene los endpoints relacionados con el dashboard del usuario."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.get_current_user import get_current_user
from app.core.errors import make_error_detail
from app.db.main import (
    HistoryDatabaseError,
    get_user_dashboard_summary,
)
from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.errors import ErrorCode, ErrorResponse

router = APIRouter()


_GET_SUMMARY_ERROR_RESPONSES: dict[int | str, dict] = {
    500: {"model": ErrorResponse},
}


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    responses=_GET_SUMMARY_ERROR_RESPONSES,
)
async def get_dashboard_summary(user=Depends(get_current_user)):
    """Endpoint para obtener métricas agregadas del dashboard del usuario."""
    user_id = user["sub"]

    try:
        return await get_user_dashboard_summary(user_id=user_id)
    except HistoryDatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.DASHBOARD_FETCH_FAILED),
        ) from e
