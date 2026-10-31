"""History query, the only translation of the History search, filters and sort into SQL."""

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

# ORDER BY clauses by validated sort key, never interpolating user input.
_ORDER_BY = {
    "recent": "created_at DESC",
    "oldest": "created_at ASC",
    "credibility_high": f"{CREDIBILITY_SQL} DESC NULLS LAST, created_at DESC",
    "credibility_low": f"{CREDIBILITY_SQL} ASC NULLS LAST, created_at DESC",
}

_DATE_RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90}

# One aggregate per Verdict in VERDICT_KINDS order, with the total first.
_FACET_SELECT = ", ".join(
    ["COUNT(*)", *("COUNT(*) FILTER (WHERE verdict = %s)" for _ in VERDICT_KINDS)]
)

# List columns, without the report, since the table never draws it.
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

# Pasted text reaches 10,000 characters and the row only uses it as a title, so SQL trims it.
HISTORY_LIST_TEXT_CHARS = 300

_HISTORY_LIST_SELECT = ", ".join(
    (
        *_HISTORY_LIST_COLUMNS,
        f"LEFT(input_text, {HISTORY_LIST_TEXT_CHARS}) AS input_text",
    )
)

# CSV columns, still without the report but with the full text and end time.
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
    """One History page with its total and the Verdict Facet of the same query."""

    items: list[HistoryListItem]
    total: int
    verdict_counts: HistoryVerdictCounts


def _map_history_list_record(row: dict[str, Any]) -> HistoryListItem:
    """Map a list row to a typed item, without the report body."""
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
    """Map an export row to a typed item, without the report body."""
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


def _where(
    user_id: str, query: HistoryQuery, now: datetime, visible_since: datetime | None
) -> tuple[str, list[Any]]:
    """Translate the query to a parameterised WHERE with one predicate per active filter and the History window."""
    clauses = ["user_id = %s"]
    params: list[Any] = [user_id]

    # The History window is a Plan entitlement, not a filter, so it stays apart from HistoryQuery.
    if visible_since is not None:
        clauses.append("created_at >= %s")
        params.append(visible_since)

    if query.status != "all":
        clauses.append("status = %s")
        params.append(query.status)

    if query.search:
        # Only what the row shows as a title: the text, the URL or the file name.
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

    # Equality on the indexable verdict column, which pending and failed rows have NULL.
    if query.verdict != "all":
        clauses.append("verdict = %s")
        params.append(query.verdict)

    if query.date_range != "all":
        clauses.append("created_at >= %s")
        params.append(now - timedelta(days=_DATE_RANGE_DAYS[query.date_range]))

    return " AND ".join(clauses), params


async def search_history(
    *,
    user_id: str,
    query: HistoryQuery,
    page: int,
    page_size: int,
    visible_since: datetime | None,
) -> HistoryPage:
    """Return a page of the visible History, its total and the query's Verdict Facet."""
    pool = await get_pool()
    now = datetime.now(timezone.utc)

    # The Facet is the query without its own filter, so the total is one of its cells.
    facet_sql, facet_params = _where(
        user_id, query.model_copy(update={"verdict": "all"}), now, visible_since
    )
    facet_query = f"""
        SELECT {_FACET_SELECT}
        FROM public.analysis_history
        WHERE {facet_sql}
    """

    where_sql, where_params = _where(user_id, query, now, visible_since)
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
                # The SQL is built from fixed, parameterised clauses, not raw input.
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

    # An aggregate without GROUP BY always returns one row.
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
    *, user_id: str, query: HistoryQuery, visible_since: datetime | None
) -> list[HistoryExportItem]:
    """Return the visible done analyses the query finds, unpaginated, for the CSV."""
    pool = await get_pool()
    where_sql, where_params = _where(
        user_id, query, datetime.now(timezone.utc), visible_since
    )

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
