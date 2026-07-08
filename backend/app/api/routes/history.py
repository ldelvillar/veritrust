"""Este módulo contiene los endpoints relacionados con el historial de análisis del usuario."""

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.api.dependencies.get_current_user import get_current_user
from app.core.credibility import classify_verdict
from app.core.errors import make_error_detail
from app.db.history import (
    count_history_source_type_facets,
    count_history_verdict_facets,
    delete_all_user_analyses,
    export_user_analysis_history,
    list_user_analysis_history,
)
from app.db.pool import DatabaseError
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.history import (
    AnalysisHistoryItem,
    DeleteAllResponse,
    HistoryResponse,
)

router = APIRouter()


_GET_HISTORY_ERROR_RESPONSES: dict[int | str, dict] = {
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

# BOM para que Excel detecte UTF-8 al abrir el CSV.
_UTF8_BOM = "﻿"

# Caracteres iniciales que Excel/Sheets interpretan como fórmula (inyección CSV).
_CSV_FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")


def _neutralize_csv_formula(value: str) -> str:
    """Antepone una comilla simple si el texto podría abrirse como fórmula en Excel."""
    if value.startswith(_CSV_FORMULA_TRIGGERS):
        return "'" + value
    return value


_EXPORT_VERDICT_LABELS = {"real": "Verdadera", "fake": "Falsa", "uncertain": "Incierta"}
_EXPORT_SOURCE_LABELS = {
    "text": "Texto pegado",
    "file": "Carga de archivo",
    "url": "Enlace",
}


def _get_date_threshold(
    date_range: Literal["all", "7d", "30d", "90d"],
) -> datetime | None:
    if date_range == "all":
        return None

    days = {"7d": 7, "30d": 30, "90d": 90}[date_range]
    return datetime.now(timezone.utc) - timedelta(days=days)


@router.get("", response_model=HistoryResponse, responses=_GET_HISTORY_ERROR_RESPONSES)
async def get_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    source_type: Literal["all", "text", "file", "url"] = "all",
    verdict: Literal["all", "real", "fake", "uncertain"] = "all",
    status: Literal["all", "done", "pending", "failed"] = "all",
    date_range: Literal["all", "7d", "30d", "90d"] = "all",
    sort: Literal["recent", "oldest", "credibility_high", "credibility_low"] = "recent",
    user=Depends(get_current_user),
):
    """Endpoint para listar el historial de análisis del usuario autenticado."""
    user_id = user["sub"]
    offset = (page - 1) * page_size

    try:
        records, total_count = await list_user_analysis_history(
            user_id=user_id,
            limit=page_size,
            offset=offset,
            search_query=search,
            source_type=None if source_type == "all" else source_type,
            created_after=_get_date_threshold(date_range),
            sort=sort,
            verdict=None if verdict == "all" else verdict,
            status=None if status == "all" else status,
        )
        # Conteos globales por veredicto (independientes del filtro de veredicto).
        verdict_counts = await count_history_verdict_facets(
            user_id=user_id,
            search_query=search,
            source_type=None if source_type == "all" else source_type,
            created_after=_get_date_threshold(date_range),
        )
        # Conteos globales por tipo de fuente (independientes del filtro de tipo).
        source_type_counts = await count_history_source_type_facets(
            user_id=user_id,
            search_query=search,
            verdict=None if verdict == "all" else verdict,
            created_after=_get_date_threshold(date_range),
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.HISTORY_FETCH_FAILED),
        ) from e

    items = [
        AnalysisHistoryItem(
            analysis_id=record.analysis_id,
            user_id=record.user_id,
            source_type=record.source_type,
            input_text=record.input_text,
            input_url=record.input_url,
            label=record.label,
            confidence=record.confidence,
            explanation=record.explanation,
            status=record.status,
            error_code=record.error_code,
            created_at=record.created_at,
            file_filename=record.file_filename,
        )
        for record in records
    ]

    return {
        "status": "success",
        "items": items,
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "verdict_counts": verdict_counts,
        "source_type_counts": source_type_counts,
    }


def _build_history_csv(records: list[AnalysisHistoryItem]) -> bytes:
    """Serializa el historial a CSV UTF-8 con BOM (compatible con Excel)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Fecha", "Tipo", "Entrada", "Veredicto", "Credibilidad"])
    for record in records:
        entrada = _neutralize_csv_formula(record.input_url or record.input_text or "")
        verdict = _EXPORT_VERDICT_LABELS.get(classify_verdict(record.label), "")
        credibility = "" if record.credibility is None else str(record.credibility)
        writer.writerow(
            [
                record.created_at,
                _EXPORT_SOURCE_LABELS.get(record.source_type, record.source_type),
                entrada,
                verdict,
                credibility,
            ]
        )
    return (_UTF8_BOM + buffer.getvalue()).encode("utf-8")


@router.get("/export", responses=_EXPORT_ERROR_RESPONSES)
async def export_history(
    search: str | None = Query(default=None, max_length=200),
    source_type: Literal["all", "text", "file", "url"] = "all",
    verdict: Literal["all", "real", "fake", "uncertain"] = "all",
    date_range: Literal["all", "7d", "30d", "90d"] = "all",
    sort: Literal["recent", "oldest", "credibility_high", "credibility_low"] = "recent",
    user=Depends(get_current_user),
):
    """Exporta todo el historial filtrado del usuario como un fichero CSV."""
    user_id = user["sub"]

    try:
        records = await export_user_analysis_history(
            user_id=user_id,
            search_query=search,
            source_type=None if source_type == "all" else source_type,
            created_after=_get_date_threshold(date_range),
            sort=sort,
            verdict=None if verdict == "all" else verdict,
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.HISTORY_FETCH_FAILED),
        ) from e

    return Response(
        content=_build_history_csv(records),
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
