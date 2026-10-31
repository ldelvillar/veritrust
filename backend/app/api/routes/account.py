"""Endpoints of the user's account: the full export of their data."""

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.dependencies.get_current_user import get_current_user
from app.core.errors import make_error_detail
from app.core.history_export import build_history_csv
from app.db.history_query import export_history
from app.db.pool import DatabaseError
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.history import HistoryQuery

router = APIRouter()


_EXPORT_ERROR_RESPONSES: dict[int | str, dict] = {
    200: {"content": {"text/csv": {}}, "description": "Todos los análisis en CSV."},
    401: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


@router.get("/export", responses=_EXPORT_ERROR_RESPONSES)
async def export_account(user=Depends(get_current_user)):
    """Exporta como CSV todos los análisis done del usuario, ocultos incluidos, en cualquier Plan (RGPD art. 20)."""
    try:
        records = await export_history(
            user_id=user["sub"], query=HistoryQuery(), visible_since=None
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.HISTORY_FETCH_FAILED),
        ) from e

    return Response(
        content=build_history_csv(records),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="veritrust-mis-datos.csv"'
        },
    )
