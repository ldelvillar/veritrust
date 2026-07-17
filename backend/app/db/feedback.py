"""Persistencia de las valoraciones de veredicto: alta y consulta de la activa."""

from __future__ import annotations

from typing import Any, Optional, Sequence

import psycopg

from app.db.pool import DatabaseError, _build_database_error, get_pool
from app.schemas.feedback import AnalysisFeedback


def _map_feedback_row(row: Sequence[Any]) -> AnalysisFeedback:
    """Mapea una fila SQL a una valoración tipada."""
    return AnalysisFeedback(
        is_correct=bool(row[0]),
        suggested_verdict=row[1],
        comment=row[2],
        created_at=str(row[3]),
    )


async def create_analysis_feedback(
    *,
    user_id: str,
    analysis_id: str,
    is_correct: bool,
    suggested_verdict: Optional[str],
    comment: Optional[str],
) -> AnalysisFeedback | None:
    """Guarda la valoración de un análisis ``done`` propio y la devuelve.

    Toma un snapshot del veredicto/label valorados desde la propia fila. Devuelve
    ``None`` si el análisis no está ``done`` o ya tiene una valoración activa
    (posterior al ``created_at`` de la fila, que un re-análisis reinicia).
    """
    pool = await get_pool()

    query = """
        INSERT INTO public.analysis_feedback
            (analysis_id, user_id, is_correct, suggested_verdict, comment,
             verdict_snapshot, label_snapshot)
        SELECT h.id, h.user_id, %s, %s, %s, h.verdict, h.label
        FROM public.analysis_history h
        WHERE h.user_id = %s AND h.id = %s AND h.status = 'done'
          AND NOT EXISTS (
              SELECT 1 FROM public.analysis_feedback f
              WHERE f.analysis_id = h.id AND f.created_at >= h.created_at
          )
        RETURNING is_correct, suggested_verdict, comment, created_at
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    query,
                    (is_correct, suggested_verdict, comment, user_id, analysis_id),
                )
                row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo guardar la valoración en la base de datos."
            )
        ) from exc

    if not row:
        return None

    return _map_feedback_row(row)


async def get_analysis_feedback(
    *, user_id: str, analysis_id: str
) -> AnalysisFeedback | None:
    """Devuelve la valoración activa de un análisis propio, o ``None``.

    Solo cuenta la valoración posterior al ``created_at`` de la fila: un
    re-análisis lo reinicia y deja las valoraciones previas como dato histórico.
    """
    pool = await get_pool()

    query = """
        SELECT f.is_correct, f.suggested_verdict, f.comment, f.created_at
        FROM public.analysis_feedback f
        JOIN public.analysis_history h ON h.id = f.analysis_id
        WHERE h.user_id = %s AND h.id = %s AND f.created_at >= h.created_at
        ORDER BY f.created_at DESC
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
                "No se pudo consultar la valoración en la base de datos."
            )
        ) from exc

    if not row:
        return None

    return _map_feedback_row(row)
