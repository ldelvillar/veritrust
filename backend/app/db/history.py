"""Persistence of each History Analysis: reads, file, public link and deletions, while the lifecycle writes the status."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.db.pool import DatabaseError, _build_database_error, get_pool
from app.schemas.analysis import AnalysisStatus, AnalysisStatusResponse
from app.schemas.history import (
    AnalysisHistoryItem,
    PendingAnalysesSummary,
    PublicAnalysisReport,
)

# Columns _map_history_record feeds on, where only the by-id query brings the whole report.
_HISTORY_COLUMNS = (
    "id",
    "user_id",
    "source_type",
    "origin",
    "input_text",
    "input_url",
    "label",
    "confidence",
    "evidence_coverage",
    "explanation",
    "created_at",
    "completed_at",
    "status",
    "error_code",
    "claims",
    "sources",
    "file_filename",
    "share_token",
)
_HISTORY_SELECT = ", ".join(_HISTORY_COLUMNS)

# Marks a row older than the History window, which with no window (NULL) it never is.
_HIDDEN_SELECT = "created_at < %s::timestamptz AS hidden"


class HiddenAnalysis(LookupError):
    """The Analysis exists but falls outside the History window of its owner's Plan."""


def _map_history_record(row: dict[str, Any]) -> AnalysisHistoryItem:
    """Map an SQL row to a typed History record."""
    return AnalysisHistoryItem(
        analysis_id=str(row["id"]),
        user_id=str(row["user_id"]),
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
        explanation=str(row["explanation"]) if row["explanation"] is not None else None,
        created_at=str(row["created_at"]),
        completed_at=(
            str(row["completed_at"]) if row["completed_at"] is not None else None
        ),
        status=row["status"],
        error_code=row["error_code"],
        claims=row["claims"],
        sources=row["sources"],
        file_filename=row["file_filename"],
        share_token=row["share_token"],
        # stage is not in _HISTORY_COLUMNS because the by-id query adds it separately.
        stage=row.get("stage"),
    )


async def get_pending_analyses_summary(*, user_id: str) -> PendingAnalysesSummary:
    """Count the user's ``pending`` analyses and point at the most recent one."""
    pool = await get_pool()

    query = """
        SELECT id, COUNT(*) OVER () AS total
        FROM public.analysis_history
        WHERE user_id = %s AND status = 'pending'
        ORDER BY created_at DESC
        LIMIT 1
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id,))
                row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudieron consultar los análisis en curso en la base de datos."
            )
        ) from exc

    if not row:
        return PendingAnalysesSummary(count=0, newest_analysis_id=None)

    return PendingAnalysesSummary(count=int(row[1]), newest_analysis_id=str(row[0]))


async def get_user_analysis_by_id(
    *, user_id: str, analysis_id: str, visible_since: datetime | None
) -> AnalysisHistoryItem | None:
    """Fetch an own Analysis by id, raising HiddenAnalysis if it is older than ``visible_since``."""
    pool = await get_pool()

    query = f"""
        SELECT {_HISTORY_SELECT}, stage, {_HIDDEN_SELECT}
        FROM public.analysis_history
        WHERE user_id = %s AND id = %s
        LIMIT 1
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (visible_since, user_id, analysis_id))
                row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo consultar el análisis en la base de datos."
            )
        ) from exc

    if not row:
        return None
    if row["hidden"]:
        raise HiddenAnalysis(analysis_id)

    return _map_history_record(row)


async def get_user_analysis_status(
    *, user_id: str, analysis_id: str, visible_since: datetime | None
) -> AnalysisStatusResponse | None:
    """Fetch the status and stage of an own Analysis, raising HiddenAnalysis if it is older than ``visible_since``."""
    pool = await get_pool()

    query = f"""
        SELECT status, stage, {_HIDDEN_SELECT}
        FROM public.analysis_history
        WHERE user_id = %s AND id = %s
        LIMIT 1
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (visible_since, user_id, analysis_id))
                row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo consultar el estado del análisis en la base de datos."
            )
        ) from exc

    if not row:
        return None
    if row["hidden"]:
        raise HiddenAnalysis(analysis_id)

    return AnalysisStatusResponse(status=row["status"], stage=row["stage"])


async def get_analysis_file(
    *, user_id: str, analysis_id: str, visible_since: datetime | None
) -> tuple[bytes, str | None] | None:
    """Return ``(file_data, file_filename)`` of an own file, raising HiddenAnalysis if it is older than ``visible_since``."""
    pool = await get_pool()

    # A hidden file is not read, since the binary can weigh 10 MB and would be discarded.
    query = f"""
        SELECT CASE WHEN created_at < %s::timestamptz THEN NULL ELSE file_data END,
               file_filename, {_HIDDEN_SELECT}
        FROM public.analysis_history
        WHERE user_id = %s AND id = %s AND source_type = 'file'
        LIMIT 1
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    query, (visible_since, visible_since, user_id, analysis_id)
                )
                row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo consultar el archivo en la base de datos."
            )
        ) from exc

    if not row:
        return None
    if row[2]:
        raise HiddenAnalysis(analysis_id)
    if row[0] is None:
        return None

    return bytes(row[0]), row[1]


async def delete_user_analysis(
    *, user_id: str, analysis_id: str
) -> AnalysisStatus | None:
    """Delete an own Analysis of the user and return the status it had, or None if it did not exist."""
    pool = await get_pool()

    query = """
        DELETE FROM public.analysis_history
        WHERE user_id = %s AND id = %s
        RETURNING status
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id, analysis_id))
                row = await cur.fetchone()
                return row[0] if row else None
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo eliminar el análisis en la base de datos."
            )
        ) from exc


@dataclass(frozen=True)
class DeletedHistory:
    """How many analyses were deleted and the ids of those still ``pending``."""

    count: int
    pending_ids: list[str]


async def delete_all_user_analyses(*, user_id: str) -> DeletedHistory:
    """Delete all of the user's own analyses and report which had a pending Run."""
    pool = await get_pool()

    query = """
        DELETE FROM public.analysis_history
        WHERE user_id = %s
        RETURNING id, status
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id,))
                rows = await cur.fetchall()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo eliminar el historial en la base de datos."
            )
        ) from exc

    return DeletedHistory(
        count=len(rows),
        pending_ids=[str(row[0]) for row in rows if row[1] == "pending"],
    )


async def set_analysis_share_token(*, user_id: str, analysis_id: str) -> str | None:
    """Turn on the public link of an own ``done`` Analysis and return its token, reusing an existing one, or ``None`` if the row is missing or not ``done``."""
    pool = await get_pool()
    new_token = secrets.token_urlsafe(32)

    query = """
        UPDATE public.analysis_history
        SET share_token = COALESCE(share_token, %s)
        WHERE user_id = %s AND id = %s AND status = 'done'
        RETURNING share_token
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (new_token, user_id, analysis_id))
                row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo activar el enlace público en la base de datos."
            )
        ) from exc

    return str(row[0]) if row else None


async def clear_analysis_share_token(*, user_id: str, analysis_id: str) -> bool:
    """Turn off the public link of an own Analysis, True if a row changed."""
    pool = await get_pool()

    query = """
        UPDATE public.analysis_history
        SET share_token = NULL
        WHERE user_id = %s AND id = %s
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id, analysis_id))
                return cur.rowcount > 0
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo desactivar el enlace público en la base de datos."
            )
        ) from exc


async def get_shared_analysis_by_token(
    *, token: str
) -> tuple[str, PublicAnalysisReport] | None:
    """Fetch the owner and public view of a report shared by its token, or ``None``."""
    pool = await get_pool()

    query = """
        SELECT
            user_id,
            source_type,
            input_text,
            input_url,
            label,
            confidence,
            evidence_coverage,
            explanation,
            created_at,
            completed_at,
            status,
            claims,
            sources,
            file_filename
        FROM public.analysis_history
        WHERE share_token = %s AND status = 'done'
        LIMIT 1
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (token,))
                row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo consultar el informe compartido en la base de datos."
            )
        ) from exc

    if not row:
        return None

    return str(row["user_id"]), PublicAnalysisReport(
        source_type=row["source_type"],
        input_text=row["input_text"],
        input_url=row["input_url"],
        label=str(row["label"]) if row["label"] is not None else None,
        confidence=float(row["confidence"]) if row["confidence"] is not None else None,
        evidence_coverage=(
            float(row["evidence_coverage"])
            if row["evidence_coverage"] is not None
            else None
        ),
        explanation=str(row["explanation"]) if row["explanation"] is not None else None,
        created_at=str(row["created_at"]),
        completed_at=(
            str(row["completed_at"]) if row["completed_at"] is not None else None
        ),
        status=row["status"],
        claims=row["claims"],
        sources=row["sources"],
        file_filename=row["file_filename"],
    )
