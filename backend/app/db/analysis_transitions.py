"""Status and stage writes of an Analysis and the Usage of its Runs, used only by ``app.core.analysis_lifecycle``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Literal, Sequence

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.plans import PlanLimits, month_window, remaining
from app.core.verdict import Verdict
from app.db.billing import usage_this_month
from app.db.pool import DatabaseError, _build_database_error, get_pool

# Serialises one user's openings until their transaction ends.
_LOCK_ALLOWANCE = "SELECT pg_advisory_xact_lock(hashtext('allowance:' || %s))"

# An Analysis's first done Run counts as an analysis and each later one as a reanalysis.
_RECORD_RUN_USAGE = """
    INSERT INTO public.usage_events (user_id, kind, analysis_id)
    VALUES (
        %s,
        CASE WHEN EXISTS (SELECT 1 FROM public.usage_events WHERE analysis_id = %s)
             THEN 'reanalysis' ELSE 'analysis' END,
        %s
    )
"""


class AllowanceExhausted(Exception):
    """The user has no free Runs left in this month's Allowance, and nothing was written."""


@asynccontextmanager
async def _transaction(context: str) -> AsyncIterator[psycopg.AsyncConnection]:
    """Open a pool transaction and translate any psycopg error to DatabaseError."""
    pool = await get_pool()
    try:
        async with pool.connection() as conn, conn.transaction():
            yield conn
    except psycopg.Error as exc:
        raise DatabaseError(_build_database_error(context)) from exc


async def _claim_allowance(
    conn: psycopg.AsyncConnection, user_id: str, limits: PlanLimits
) -> None:
    """Lock the user's openings and raise AllowanceExhausted if their month's Allowance is used up."""
    async with conn.cursor() as cur:
        await cur.execute(_LOCK_ALLOWANCE, (user_id,))
    start, end = month_window(datetime.now(UTC))
    usage = await usage_this_month(user_id, start, end, conn)
    if remaining(limits, usage.used, usage.pending) == 0:
        raise AllowanceExhausted(user_id)


def _normalize_confidence(confidence: Any) -> float:
    """Convert confidence to float and validate the [0, 1] range."""
    try:
        value = float(confidence)
    except (TypeError, ValueError) as exc:
        raise DatabaseError(f"Confidence no es numerico: {confidence!r}.") from exc

    if not 0.0 <= value <= 1.0:
        raise DatabaseError(f"Confidence fuera de rango [0, 1]: {value}.")

    return value


def _coerce_optional_fraction(value: Any) -> float | None:
    """Convert an optional fraction to float validating [0, 1], passing ``None`` through."""
    if value is None:
        return None
    try:
        fraction = float(value)
    except (TypeError, ValueError) as exc:
        raise DatabaseError(f"Fraccion no es numerica: {value!r}.") from exc

    if not 0.0 <= fraction <= 1.0:
        raise DatabaseError(f"Fraccion fuera de rango [0, 1]: {fraction}.")

    return fraction


async def insert_pending(
    *,
    user_id: str,
    origin: str,
    source_type: str,
    input_text: str | None,
    input_url: str | None,
    limits: PlanLimits,
) -> str:
    """Insert a ``pending`` text or URL Analysis if it fits the Plan's Allowance and return its id."""
    query = """
        INSERT INTO public.analysis_history
        (user_id, source_type, origin, input_text, input_url, max_input_chars, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        RETURNING id
    """
    return await _insert(
        query,
        (user_id, source_type, origin, input_text, input_url, limits.max_input_chars),
        "No se pudo guardar el analisis en la base de datos.",
        user_id=user_id,
        limits=limits,
    )


async def insert_pending_file(
    *, user_id: str, origin: str, filename: str, data: bytes, limits: PlanLimits
) -> str:
    """Insert a ``pending`` file Analysis with its binary if it fits the Plan's Allowance and return its id."""
    query = """
        INSERT INTO public.analysis_history
        (user_id, source_type, origin, file_data, file_filename, max_input_chars, status)
        VALUES (%s, 'file', %s, %s, %s, %s, 'pending')
        RETURNING id
    """
    return await _insert(
        query,
        (user_id, origin, data, filename, limits.max_input_chars),
        "No se pudo guardar el archivo en la base de datos.",
        user_id=user_id,
        limits=limits,
    )


async def _insert(
    query: str,
    params: tuple[Any, ...],
    context: str,
    *,
    user_id: str,
    limits: PlanLimits,
) -> str:
    """Check the Allowance and run an INSERT … RETURNING id in the same transaction."""
    async with _transaction(context) as conn:
        await _claim_allowance(conn, user_id, limits)
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            inserted_row = await cur.fetchone()

    if not inserted_row:
        raise DatabaseError("No se pudo obtener el id del análisis guardado.")

    return str(inserted_row[0])


async def reopen(
    *,
    user_id: str,
    analysis_id: str,
    from_status: Literal["failed", "done"],
    limits: PlanLimits,
) -> bool:
    """Return an own Analysis still in ``from_status`` to ``pending`` if it fits the Plan's Allowance, True if it changed."""
    # created_at restarts for the reaper and the previous result is erased so aggregates stop counting it.
    query = """
        UPDATE public.analysis_history
        SET status = 'pending',
            label = NULL,
            verdict = NULL,
            confidence = NULL,
            evidence_coverage = NULL,
            explanation = NULL,
            claims = NULL,
            sources = NULL,
            pipeline = NULL,
            error_code = NULL,
            stage = NULL,
            created_at = NOW(),
            completed_at = NULL
        WHERE user_id = %s AND id = %s AND status = %s
    """
    async with _transaction(
        "No se pudo reabrir el análisis en la base de datos."
    ) as conn:
        await _claim_allowance(conn, user_id, limits)
        async with conn.cursor() as cur:
            await cur.execute(query, (user_id, analysis_id, from_status))
            return cur.rowcount > 0


async def load_pending_content(analysis_id: str) -> dict[str, Any] | None:
    """Return the input of a ``pending`` Analysis (type, text, URL, file and character cap), or None."""
    query = """
        SELECT source_type, input_text, input_url, file_data, file_filename,
               max_input_chars
        FROM public.analysis_history
        WHERE id = %s AND status = 'pending'
    """
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (analysis_id,))
                return await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo cargar la entrada del análisis en la base de datos."
            )
        ) from exc


async def fail(*, analysis_id: str, error_code: str) -> bool:
    """Fail an Analysis that is still ``pending``, True if it changed."""
    query = """
        UPDATE public.analysis_history
        SET status = 'failed', error_code = %s, completed_at = NOW()
        WHERE id = %s AND status = 'pending'
    """
    return await _update(
        query,
        (error_code, analysis_id),
        "No se pudo actualizar el analisis en la base de datos.",
    )


async def set_stage(*, analysis_id: str, stage: str) -> bool:
    """Record the active stage of an Analysis and return False if it is no longer ``pending``."""
    query = (
        "UPDATE public.analysis_history SET stage = %s "
        "WHERE id = %s AND status = 'pending'"
    )
    return await _update(
        query,
        (stage, analysis_id),
        "No se pudo actualizar la etapa del análisis en la base de datos.",
    )


async def set_input_text(*, analysis_id: str, input_text: str) -> None:
    """Store the text extracted from a file while the Analysis is still ``pending``."""
    query = (
        "UPDATE public.analysis_history SET input_text = %s "
        "WHERE id = %s AND status = 'pending'"
    )
    await _update(
        query,
        (input_text, analysis_id),
        "No se pudo actualizar el texto del análisis en la base de datos.",
    )


async def complete(
    *,
    analysis_id: str,
    verdict: Verdict,
    explanation: str | None,
    sources: list[dict],
    pipeline: dict,
) -> bool:
    """Move a still ``pending`` Analysis to ``done`` with its Verdict and record its Run in the Usage, True if it changed."""
    confidence_value = _normalize_confidence(verdict.confidence)
    coverage_value = _coerce_optional_fraction(verdict.evidence_coverage)
    claims = [
        {"text": claim.text, "label": claim.label, "confidence": claim.confidence}
        for claim in verdict.claims
    ]
    query = """
        UPDATE public.analysis_history
        SET label = %s,
            verdict = %s,
            confidence = %s,
            evidence_coverage = %s,
            explanation = %s,
            claims = %s,
            sources = %s,
            pipeline = %s,
            status = 'done',
            error_code = NULL,
            completed_at = NOW()
        WHERE id = %s AND status = 'pending'
        RETURNING user_id
    """
    params = (
        verdict.label,
        verdict.kind,
        confidence_value,
        coverage_value,
        explanation,
        Jsonb(claims) if claims else None,
        Jsonb(sources) if sources else None,
        Jsonb(pipeline) if pipeline else None,
        analysis_id,
    )
    # The Run consumes its unit in the same transaction, so a done without Usage is impossible.
    async with _transaction(
        "No se pudo guardar el analisis en la base de datos."
    ) as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            row = await cur.fetchone()
            if row is None:
                return False
            await cur.execute(_RECORD_RUN_USAGE, (row[0], analysis_id, analysis_id))
    return True


async def list_stale_pending_ids(*, older_than_seconds: int) -> list[str]:
    """List the ``pending`` ids older than the threshold, the orphan candidates."""
    query = """
        SELECT id::text
        FROM public.analysis_history
        WHERE status = 'pending'
          AND created_at < NOW() - make_interval(secs => %s)
    """
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (older_than_seconds,))
                rows = await cur.fetchall()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo consultar análisis atascados en la base de datos."
            )
        ) from exc

    return [str(row[0]) for row in rows]


async def fail_stale(
    *, analysis_ids: Sequence[str], older_than_seconds: int, error_code: str
) -> int:
    """Fail the given ids if they are still ``pending`` and orphaned, returning how many."""
    # Recheck status and age, since a Retry between the read and this write restarts created_at.
    query = """
        UPDATE public.analysis_history
        SET status = 'failed', error_code = %s, completed_at = NOW()
        WHERE id::text = ANY(%s)
          AND status = 'pending'
          AND created_at < NOW() - make_interval(secs => %s)
    """
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    query, (error_code, list(analysis_ids), older_than_seconds)
                )
                return cur.rowcount
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo reciclar análisis atascados en la base de datos."
            )
        ) from exc


async def _update(query: str, params: tuple[Any, ...], context: str) -> bool:
    """Run an UPDATE and return whether any row changed."""
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return cur.rowcount > 0
    except psycopg.Error as exc:
        raise DatabaseError(_build_database_error(context)) from exc
