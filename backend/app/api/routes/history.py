"""Este módulo contiene los endpoints relacionados con el historial de análisis del usuario."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.api.dependencies.get_current_user import get_current_user
from app.core.errors import make_error_detail
from app.core.history_export import build_history_csv
from app.db.history import delete_all_user_analyses, get_pending_analyses_summary
from app.db.history_query import export_history as export_user_history
from app.db.history_query import search_history
from app.db.pool import DatabaseError
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.history import (
    DeleteAllResponse,
    HistoryQuery,
    HistoryResponse,
    PendingAnalysesSummary,
)

router = APIRouter()


_GET_HISTORY_ERROR_RESPONSES: dict[int | str, dict] = {
    401: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}

_GET_PENDING_ERROR_RESPONSES: dict[int | str, dict] = {
    401: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}

_EXPORT_ERROR_RESPONSES: dict[int | str, dict] = {
    200: {"content": {"text/csv": {}}, "description": "Historial en formato CSV."},
    401: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}

_DELETE_ALL_ERROR_RESPONSES: dict[int | str, dict] = {
    401: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


@router.get("", response_model=HistoryResponse, responses=_GET_HISTORY_ERROR_RESPONSES)
async def get_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    query: HistoryQuery = Depends(),
    user=Depends(get_current_user),
):
    """Endpoint para listar el historial de análisis del usuario autenticado."""
    try:
        result = await search_history(
            user_id=user["sub"], query=query, page=page, page_size=page_size
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.HISTORY_FETCH_FAILED),
        ) from e

    return {
        "status": "success",
        "items": result.items,
        "count": result.total,
        "page": page,
        "page_size": page_size,
        "verdict_counts": result.verdict_counts,
    }


@router.get(
    "/pending",
    response_model=PendingAnalysesSummary,
    responses=_GET_PENDING_ERROR_RESPONSES,
)
async def get_pending_analyses(user=Depends(get_current_user)):
    """Resumen de los análisis en curso, para el indicador global del menú."""
    user_id = user["sub"]

    try:
        return await get_pending_analyses_summary(user_id=user_id)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.HISTORY_FETCH_FAILED),
        ) from e


@router.get("/export", responses=_EXPORT_ERROR_RESPONSES)
async def export_history(
    query: HistoryQuery = Depends(),
    user=Depends(get_current_user),
):
    """Exporta como CSV los análisis done que encuentra la consulta del usuario."""
    try:
        records = await export_user_history(user_id=user["sub"], query=query)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.HISTORY_FETCH_FAILED),
        ) from e

    return Response(
        content=build_history_csv(records),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="historial-veritrust.csv"'
        },
    )


@router.delete(
    "", response_model=DeleteAllResponse, responses=_DELETE_ALL_ERROR_RESPONSES
)
async def delete_history(user=Depends(get_current_user)):
    """Elimina todo el historial de análisis del usuario autenticado."""
    user_id = user["sub"]

    try:
        deleted_count = await delete_all_user_analyses(user_id=user_id)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.HISTORY_DELETE_FAILED),
        ) from e

    return {"status": "deleted", "deleted_count": deleted_count}
