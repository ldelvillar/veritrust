"""Persistencia de cada análisis del historial: lectura, archivo, enlace público y borrados; el estado lo escribe el ciclo de vida."""

from __future__ import annotations

import secrets
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.db.pool import DatabaseError, _build_database_error, get_pool
from app.schemas.analysis import AnalysisStatusResponse
from app.schemas.history import (
    AnalysisHistoryItem,
    PendingAnalysesSummary,
    PublicAnalysisReport,
)

# Columnas que alimenta _map_history_record: solo la consulta por id trae el informe entero.
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


def _map_history_record(row: dict[str, Any]) -> AnalysisHistoryItem:
    """Mapea una fila SQL a un registro de historial tipado."""
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
        # stage no está en _HISTORY_COLUMNS: lo añade aparte la consulta por id.
        stage=row.get("stage"),
    )


async def get_pending_analyses_summary(*, user_id: str) -> PendingAnalysesSummary:
    """Cuenta los análisis ``pending`` del usuario y señala el más reciente."""
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
    *, user_id: str, analysis_id: str
) -> AnalysisHistoryItem | None:
    """Obtiene un analisis por id para un usuario autenticado."""
    pool = await get_pool()

    query = f"""
        SELECT {_HISTORY_SELECT}, stage
        FROM public.analysis_history
        WHERE user_id = %s AND id = %s
        LIMIT 1
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (user_id, analysis_id))
                row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo consultar el análisis en la base de datos."
            )
        ) from exc

    if not row:
        return None

    return _map_history_record(row)


async def get_user_analysis_status(
    *, user_id: str, analysis_id: str
) -> AnalysisStatusResponse | None:
    """Obtiene solo el estado y la etapa de un análisis propio para el sondeo."""
    pool = await get_pool()

    query = """
        SELECT status, stage
        FROM public.analysis_history
        WHERE user_id = %s AND id = %s
        LIMIT 1
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (user_id, analysis_id))
                row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo consultar el estado del análisis en la base de datos."
            )
        ) from exc

    if not row:
        return None

    return AnalysisStatusResponse(status=row["status"], stage=row["stage"])


async def get_analysis_file(
    *, user_id: str, analysis_id: str
) -> tuple[bytes, str | None] | None:
    """Devuelve ``(file_data, file_filename)`` del archivo propio del usuario, o None."""
    pool = await get_pool()

    query = """
        SELECT file_data, file_filename
        FROM public.analysis_history
        WHERE user_id = %s AND id = %s AND source_type = 'file'
        LIMIT 1
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id, analysis_id))
                row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo consultar el archivo en la base de datos."
            )
        ) from exc

    if not row or row[0] is None:
        return None

    return bytes(row[0]), row[1]


async def delete_user_analysis(*, user_id: str, analysis_id: str) -> bool:
    """Elimina un análisis propio del usuario. Devuelve True si borró una fila."""
    pool = await get_pool()

    query = "DELETE FROM public.analysis_history WHERE user_id = %s AND id = %s"

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id, analysis_id))
                return cur.rowcount > 0
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo eliminar el análisis en la base de datos."
            )
        ) from exc


async def delete_all_user_analyses(*, user_id: str) -> int:
    """Elimina todos los análisis propios del usuario. Devuelve cuántas filas borró."""
    pool = await get_pool()

    query = "DELETE FROM public.analysis_history WHERE user_id = %s"

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id,))
                return cur.rowcount
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo eliminar el historial en la base de datos."
            )
        ) from exc


async def set_analysis_share_token(*, user_id: str, analysis_id: str) -> str | None:
    """Activa el enlace público de un análisis ``done`` propio y devuelve el token.

    Idempotente: si ya estaba compartido, conserva y devuelve el token existente.
    Devuelve ``None`` si la fila no existe o no está en estado ``done``.
    """
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
    """Desactiva el enlace público de un análisis propio. True si cambió una fila."""
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


async def get_shared_analysis_by_token(*, token: str) -> PublicAnalysisReport | None:
    """Obtiene la vista pública de un informe compartido por su token, o ``None``."""
    pool = await get_pool()

    query = """
        SELECT
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

    return PublicAnalysisReport(
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
