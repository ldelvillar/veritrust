"""History query: la única traducción de la búsqueda, los filtros y el orden del historial a SQL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.core.verdict import CREDIBILITY_SQL, VERDICT_KINDS
from app.db.pool import DatabaseError, _build_database_error, get_pool
from app.schemas.history import (
    HistoryExportItem,
    HistoryListItem,
    HistoryQuery,
    HistoryVerdictCounts,
)

# Cláusulas ORDER BY por clave del orden validado; nunca se interpola entrada del usuario.
_ORDER_BY = {
    "recent": "created_at DESC",
    "oldest": "created_at ASC",
    "credibility_high": f"{CREDIBILITY_SQL} DESC NULLS LAST, created_at DESC",
    "credibility_low": f"{CREDIBILITY_SQL} ASC NULLS LAST, created_at DESC",
}

_DATE_RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90}

# Un agregado por veredicto, en el orden de VERDICT_KINDS; el total va primero.
_FACET_SELECT = ", ".join(
    ["COUNT(*)", *("COUNT(*) FILTER (WHERE verdict = %s)" for _ in VERDICT_KINDS)]
)

# Columnas del listado: la tabla no pinta el informe, así que no se traen ni se envían.
_HISTORY_LIST_COLUMNS = (
    "id",
    "source_type",
    "origin",
    "input_url",
    "label",
    "confidence",
    "evidence_coverage",
    "created_at",
    "status",
    "stage",
    "error_code",
    "file_filename",
    "share_token",
)

# El texto pegado llega a 10.000 caracteres y la fila solo lo usa como título: se recorta en SQL.
HISTORY_LIST_TEXT_CHARS = 300

_HISTORY_LIST_SELECT = ", ".join(
    (
        *_HISTORY_LIST_COLUMNS,
        f"LEFT(input_text, {HISTORY_LIST_TEXT_CHARS}) AS input_text",
    )
)

# Columnas del CSV: el informe tampoco se exporta, pero el texto va entero y con su duración.
_HISTORY_EXPORT_COLUMNS = (
    "id",
    "source_type",
    "origin",
    "input_text",
    "input_url",
    "label",
    "confidence",
    "evidence_coverage",
    "created_at",
    "completed_at",
    "status",
    "file_filename",
)
_HISTORY_EXPORT_SELECT = ", ".join(_HISTORY_EXPORT_COLUMNS)

_EXPORT_MAX_ROWS = 10_000


@dataclass(frozen=True)
class HistoryPage:
    """Una página del historial con su total y el facet de veredicto de la misma consulta."""

    items: list[HistoryListItem]
    total: int
    verdict_counts: HistoryVerdictCounts


def _map_history_list_record(row: dict[str, Any]) -> HistoryListItem:
    """Mapea una fila del listado a un ítem tipado, sin el cuerpo del informe."""
    return HistoryListItem(
        analysis_id=str(row["id"]),
        source_type=row["source_type"],
        origin=row["origin"],
        input_text=row["input_text"],
        input_url=row["input_url"],
        label=str(row["label"]) if row["label"] is not None else None,
        confidence=float(row["confidence"]) if row["confidence"] is not None else None,
        evidence_coverage=(
            float(row["evidence_coverage"])
            if row["evidence_coverage"] is not None
            else None
        ),
        created_at=str(row["created_at"]),
        status=row["status"],
        stage=row["stage"],
        error_code=row["error_code"],
        file_filename=row["file_filename"],
        share_token=row["share_token"],
    )


def _map_history_export_record(row: dict[str, Any]) -> HistoryExportItem:
    """Mapea una fila de la exportación a un ítem tipado, sin el cuerpo del informe."""
    return HistoryExportItem(
        analysis_id=str(row["id"]),
        source_type=row["source_type"],
        origin=row["origin"],
        input_text=row["input_text"],
        input_url=row["input_url"],
        label=str(row["label"]) if row["label"] is not None else None,
        confidence=float(row["confidence"]) if row["confidence"] is not None else None,
        evidence_coverage=(
            float(row["evidence_coverage"])
            if row["evidence_coverage"] is not None
            else None
        ),
        created_at=str(row["created_at"]),
        completed_at=(
            str(row["completed_at"]) if row["completed_at"] is not None else None
        ),
        status=row["status"],
        file_filename=row["file_filename"],
    )


def _where(user_id: str, query: HistoryQuery, now: datetime) -> tuple[str, list[Any]]:
    """Traduce la consulta a un WHERE parametrizado con un predicado por filtro activo."""
    clauses = ["user_id = %s"]
    params: list[Any] = [user_id]

    if query.status != "all":
        clauses.append("status = %s")
        params.append(query.status)

    if query.search:
        # Solo lo que la fila muestra como título: el texto, la URL o el nombre del archivo.
        clauses.append(
            "("
            "COALESCE(input_text, '') ILIKE %s OR "
            "COALESCE(input_url, '') ILIKE %s OR "
            "COALESCE(file_filename, '') ILIKE %s"
            ")"
        )
        params.extend([f"%{query.search}%"] * 3)

    if query.source_type != "all":
        clauses.append("source_type = %s")
        params.append(query.source_type)

    # Igualdad sobre la columna verdict (indexable); las filas pending/failed la tienen NULL.
    if query.verdict != "all":
        clauses.append("verdict = %s")
        params.append(query.verdict)

    if query.date_range != "all":
        clauses.append("created_at >= %s")
        params.append(now - timedelta(days=_DATE_RANGE_DAYS[query.date_range]))

    return " AND ".join(clauses), params


async def search_history(
    *, user_id: str, query: HistoryQuery, page: int, page_size: int
) -> HistoryPage:
    """Devuelve una página del historial, su total y el facet de veredicto de la consulta."""
    pool = await get_pool()
    now = datetime.now(timezone.utc)

    # El facet es la consulta sin su propio filtro; el total es una de sus celdas.
    facet_sql, facet_params = _where(
        user_id, query.model_copy(update={"verdict": "all"}), now
    )
    facet_query = f"""
        SELECT {_FACET_SELECT}
        FROM public.analysis_history
        WHERE {facet_sql}
    """

    where_sql, where_params = _where(user_id, query, now)
    page_query = f"""
        SELECT {_HISTORY_LIST_SELECT}
        FROM public.analysis_history
        WHERE {where_sql}
        ORDER BY {_ORDER_BY[query.sort]}
        LIMIT %s OFFSET %s
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # El SQL se compone de cláusulas fijas y parametrizadas, no de entrada cruda.
                await cur.execute(facet_query, (*VERDICT_KINDS, *facet_params))  # pyright: ignore[reportArgumentType]
                facet_row = await cur.fetchone()
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    page_query,  # pyright: ignore[reportArgumentType]
                    (*where_params, page_size, (page - 1) * page_size),
                )
                rows = await cur.fetchall()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo consultar el historial en la base de datos."
            )
        ) from exc

    # Un agregado sin GROUP BY siempre devuelve una fila.
    assert facet_row is not None
    by_verdict = dict(zip(VERDICT_KINDS, map(int, facet_row[1:])))
    verdict_counts = HistoryVerdictCounts(total=int(facet_row[0]), **by_verdict)
    total = (
        verdict_counts.total if query.verdict == "all" else by_verdict[query.verdict]
    )

    return HistoryPage(
        items=[_map_history_list_record(row) for row in rows],
        total=total,
        verdict_counts=verdict_counts,
    )


async def export_history(
    *, user_id: str, query: HistoryQuery
) -> list[HistoryExportItem]:
    """Devuelve los análisis done que encuentra la consulta, sin paginar, para el CSV."""
    pool = await get_pool()
    where_sql, where_params = _where(user_id, query, datetime.now(timezone.utc))

    export_query = f"""
        SELECT {_HISTORY_EXPORT_SELECT}
        FROM public.analysis_history
        WHERE {where_sql} AND status = 'done'
        ORDER BY {_ORDER_BY[query.sort]}
        LIMIT %s
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(export_query, (*where_params, _EXPORT_MAX_ROWS))  # pyright: ignore[reportArgumentType]
                rows = await cur.fetchall()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo exportar el historial en la base de datos."
            )
        ) from exc

    return [_map_history_export_record(row) for row in rows]
