"""Persistencia del historial de análisis: altas, actualizaciones y consultas."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional, Sequence

import psycopg
from psycopg.types.json import Jsonb

from app.db.pool import DatabaseError, _build_database_error, get_pool
from app.schemas.analysis import AnalysisRequest
from app.schemas.history import AnalysisHistoryItem

logger = logging.getLogger(__name__)

_VALID_SOURCE_TYPES = {"text", "file", "url"}


def _normalize_confidence(confidence: Any) -> float:
    """Convierte confidence a float y valida el rango [0, 1]."""
    try:
        value = float(confidence)
    except (TypeError, ValueError) as exc:
        raise DatabaseError(f"Confidence no es numerico: {confidence!r}.") from exc

    if not 0.0 <= value <= 1.0:
        raise DatabaseError(f"Confidence fuera de rango [0, 1]: {value}.")

    return value


def _map_history_record(row: Sequence[Any]) -> AnalysisHistoryItem:
    """Mapea una fila SQL a un registro de historial tipado."""
    return AnalysisHistoryItem(
        analysis_id=str(row[0]),
        user_id=str(row[1]),
        source_type=str(row[2]),
        input_text=row[3],
        input_url=row[4],
        label=str(row[5]) if row[5] is not None else None,
        confidence=float(row[6]) if row[6] is not None else None,
        explanation=str(row[7]) if row[7] is not None else None,
        created_at=str(row[8]),
        status=str(row[9]),
        error_code=row[10],
        claims=row[11],
        sources=row[12],
    )


def _sanitize_history_query_params(
    *,
    limit: int,
    offset: int,
    source_type: Optional[str],
    score_sort_order: str,
) -> tuple[int, int, Optional[str], str]:
    """Normaliza límites, filtros y orden para consultas de historial."""
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    safe_source_type = source_type if source_type in _VALID_SOURCE_TYPES else None
    safe_score_sort = "ASC" if score_sort_order.lower() == "asc" else "DESC"
    return safe_limit, safe_offset, safe_source_type, safe_score_sort


def _build_history_where_clause(
    *,
    user_id: str,
    search_query: Optional[str],
    source_type: Optional[str],
    created_after: Optional[datetime],
) -> tuple[str, list[Any]]:
    """Construye cláusula WHERE y parámetros para historial paginado."""
    where_clauses = ["user_id = %s", "status = 'done'"]
    where_params: list[Any] = [user_id]

    normalized_search = (search_query or "").strip()
    if normalized_search:
        like_pattern = f"%{normalized_search}%"
        where_clauses.append(
            "("
            "COALESCE(input_text, '') ILIKE %s OR "
            "COALESCE(input_url, '') ILIKE %s OR "
            "COALESCE(label, '') ILIKE %s OR "
            "COALESCE(source_type, '') ILIKE %s"
            ")"
        )
        where_params.extend([like_pattern, like_pattern, like_pattern, like_pattern])

    if source_type:
        where_clauses.append("source_type = %s")
        where_params.append(source_type)

    if created_after is not None:
        where_clauses.append("created_at >= %s")
        where_params.append(created_after)

    return " AND ".join(where_clauses), where_params


def _build_history_queries(where_sql: str, safe_score_sort: str) -> tuple[str, str]:
    """Genera consultas SQL para conteo y listado de historial."""
    count_query = f"""
        SELECT COUNT(*)
        FROM public.analysis_history
        WHERE {where_sql}
    """

    list_query = """
        SELECT
            id,
            user_id,
            source_type,
            input_text,
            input_url,
            label,
            confidence,
            explanation,
            created_at,
            status,
            error_code,
            claims,
            sources
        FROM public.analysis_history
        WHERE {where_sql}
        ORDER BY confidence {safe_score_sort}, created_at DESC
        LIMIT %s OFFSET %s
    """.format(where_sql=where_sql, safe_score_sort=safe_score_sort)

    return count_query, list_query


async def create_pending_analysis(
    *,
    user_id: str,
    request: AnalysisRequest,
) -> str:
    """Inserta un análisis en estado ``pending`` y devuelve su id."""
    pool = await get_pool()

    source_type = request.source_type.value
    input_text = request.text if source_type in {"text", "file"} else None
    input_url = str(request.url) if source_type == "url" and request.url else None

    query = """
        INSERT INTO public.analysis_history
        (user_id, source_type, input_text, input_url, status)
        VALUES (%s, %s, %s, %s, 'pending')
        RETURNING id
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id, source_type, input_text, input_url))
                inserted_row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error("No se pudo guardar el analisis en la base de datos.")
        ) from exc

    if not inserted_row:
        raise DatabaseError("No se pudo obtener el id del análisis guardado.")

    return str(inserted_row[0])


async def complete_analysis(
    *,
    analysis_id: str,
    label: str,
    confidence: Any,
    explanation: str,
    claims: Optional[list[dict]] = None,
    sources: Optional[list[dict]] = None,
) -> None:
    """Marca un análisis pendiente como ``done`` con su resultado."""
    pool = await get_pool()
    confidence_value = _normalize_confidence(confidence)

    query = """
        UPDATE public.analysis_history
        SET label = %s,
            confidence = %s,
            explanation = %s,
            claims = %s,
            sources = %s,
            status = 'done',
            error_code = NULL
        WHERE id = %s
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    query,
                    (
                        label,
                        confidence_value,
                        explanation,
                        Jsonb(claims) if claims else None,
                        Jsonb(sources) if sources else None,
                        analysis_id,
                    ),
                )
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error("No se pudo guardar el analisis en la base de datos.")
        ) from exc


async def fail_analysis(*, analysis_id: str, error_code: str) -> None:
    """Marca un análisis pendiente como ``failed`` con un código de error estable."""
    pool = await get_pool()

    query = """
        UPDATE public.analysis_history
        SET status = 'failed', error_code = %s
        WHERE id = %s
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (error_code, analysis_id))
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo actualizar el analisis en la base de datos."
            )
        ) from exc


async def fail_stale_pending_analyses(
    *, older_than_seconds: int, error_code: str
) -> int:
    """Marca como ``failed`` las filas ``pending`` más antiguas que el umbral.

    Devuelve cuántas filas se reciclaron. Es la red de seguridad para análisis
    encolados cuyo worker murió o cuyo trabajo expiró sin actualizar la fila.
    """
    pool = await get_pool()

    query = """
        UPDATE public.analysis_history
        SET status = 'failed', error_code = %s
        WHERE status = 'pending'
          AND created_at < NOW() - make_interval(secs => %s)
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (error_code, older_than_seconds))
                return cur.rowcount
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo reciclar análisis atascados en la base de datos."
            )
        ) from exc


async def list_user_analysis_history(
    *,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    search_query: Optional[str] = None,
    source_type: Optional[str] = None,
    created_after: Optional[datetime] = None,
    score_sort_order: str = "desc",
) -> tuple[list[AnalysisHistoryItem], int]:
    """Lista historial paginado del usuario y devuelve tambien el total."""
    pool = await get_pool()

    safe_limit, safe_offset, safe_source_type, safe_score_sort = (
        _sanitize_history_query_params(
            limit=limit,
            offset=offset,
            source_type=source_type,
            score_sort_order=score_sort_order,
        )
    )
    where_sql, where_params = _build_history_where_clause(
        user_id=user_id,
        search_query=search_query,
        source_type=safe_source_type,
        created_after=created_after,
    )
    count_query, list_query = _build_history_queries(where_sql, safe_score_sort)

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # where_sql/safe_score_sort son valores saneados, no entrada cruda.
                await cur.execute(count_query, tuple(where_params))  # pyright: ignore[reportArgumentType]
                count_row = await cur.fetchone()
                total_count = int(count_row[0]) if count_row else 0

                await cur.execute(list_query, (*where_params, safe_limit, safe_offset))  # pyright: ignore[reportArgumentType]
                rows = await cur.fetchall()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo consultar el historial en la base de datos."
            )
        ) from exc

    records = [_map_history_record(row) for row in rows]

    return records, total_count


_EXPORT_MAX_ROWS = 10_000


async def export_user_analysis_history(
    *,
    user_id: str,
    search_query: Optional[str] = None,
    source_type: Optional[str] = None,
    created_after: Optional[datetime] = None,
    score_sort_order: str = "desc",
) -> list[AnalysisHistoryItem]:
    """Lista todo el historial filtrado del usuario para exportarlo (sin paginar)."""
    pool = await get_pool()

    _, _, safe_source_type, safe_score_sort = _sanitize_history_query_params(
        limit=1,
        offset=0,
        source_type=source_type,
        score_sort_order=score_sort_order,
    )
    where_sql, where_params = _build_history_where_clause(
        user_id=user_id,
        search_query=search_query,
        source_type=safe_source_type,
        created_after=created_after,
    )

    export_query = """
        SELECT
            id,
            user_id,
            source_type,
            input_text,
            input_url,
            label,
            confidence,
            explanation,
            created_at,
            status,
            error_code,
            claims,
            sources
        FROM public.analysis_history
        WHERE {where_sql}
        ORDER BY confidence {safe_score_sort}, created_at DESC
        LIMIT %s
    """.format(where_sql=where_sql, safe_score_sort=safe_score_sort)

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(export_query, (*where_params, _EXPORT_MAX_ROWS))  # pyright: ignore[reportArgumentType]
                rows = await cur.fetchall()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo exportar el historial en la base de datos."
            )
        ) from exc

    return [_map_history_record(row) for row in rows]


async def get_user_analysis_by_id(
    *, user_id: str, analysis_id: str
) -> AnalysisHistoryItem | None:
    """Obtiene un analisis por id para un usuario autenticado."""
    pool = await get_pool()

    query = """
        SELECT
            id,
            user_id,
            source_type,
            input_text,
            input_url,
            label,
            confidence,
            explanation,
            created_at,
            status,
            error_code,
            claims,
            sources
        FROM public.analysis_history
        WHERE user_id = %s AND id = %s
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
                "No se pudo consultar el análisis en la base de datos."
            )
        ) from exc

    if not row:
        return None

    return _map_history_record(row)


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
