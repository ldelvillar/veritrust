"""Este módulo contiene los endpoints relacionados con el historial de análisis del usuario."""

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Query, HTTPException, Depends

from src.api.database import HistoryDatabaseError, list_user_analysis_history
from src.api.utils import get_current_user


router = APIRouter(prefix="/history", tags=["Historial"])


def _get_date_threshold(
    date_range: Literal["all", "7d", "30d", "90d"],
) -> datetime | None:
    if date_range == "all":
        return None

    days = {"7d": 7, "30d": 30, "90d": 90}[date_range]
    return datetime.now(timezone.utc) - timedelta(days=days)


@router.get("")
def get_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    source_type: Literal["all", "text", "file", "url"] = "all",
    date_range: Literal["all", "7d", "30d", "90d"] = "all",
    score_sort: Literal["desc", "asc"] = "desc",
    user=Depends(get_current_user),
):
    """Endpoint para listar el historial de análisis del usuario autenticado."""
    user_id = user["sub"]
    offset = (page - 1) * page_size

    try:
        records, total_count = list_user_analysis_history(
            user_id=user_id,
            limit=page_size,
            offset=offset,
            search_query=search,
            source_type=None if source_type == "all" else source_type,
            created_after=_get_date_threshold(date_range),
            score_sort_order=score_sort,
        )
    except HistoryDatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail="No se pudo recuperar el historial de análisis.",
        ) from e

    return {
        "status": "success",
        "items": [record.__dict__ for record in records],
        "count": total_count,
        "page": page,
        "page_size": page_size,
    }
