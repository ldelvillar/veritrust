"""Persistencia del historial de análisis: altas, actualizaciones y consultas."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime
from typing import Any, Optional, Sequence

import psycopg
from psycopg.types.json import Jsonb

from app.core.credibility import CREDIBILITY_SQL_EXPR, VERDICTS, classify_verdict
from app.db.pool import DatabaseError, _build_database_error, get_pool
from app.schemas.analysis import AnalysisRequest, SourceType
from app.schemas.history import (
    AnalysisHistoryItem,
    HistorySourceTypeCounts,
    HistoryVerdictCounts,
    PublicAnalysisReport,
)

logger = logging.getLogger(__name__)

# Vocabulario único: derivado del enum SourceType para no divergir del contrato.
_VALID_SOURCE_TYPES = {source_type.value for source_type in SourceType}
_VALID_VERDICTS = set(VERDICTS)
_VALID_STATUSES = {"done", "pending", "failed"}

# Cláusulas ORDER BY saneadas por clave; nunca se interpola entrada cruda del usuario.
_SORT_ORDER_BY = {
    "recent": "created_at DESC",
    "oldest": "created_at ASC",
    "credibility_high": f"{CREDIBILITY_SQL_EXPR} DESC NULLS LAST, created_at DESC",
    "credibility_low": f"{CREDIBILITY_SQL_EXPR} ASC NULLS LAST, created_at DESC",
}

_DEFAULT_SORT = "recent"


def _normalize_confidence(confidence: Any) -> float:
    """Convierte confidence a float y valida el rango [0, 1]."""
    try:
        value = float(confidence)
    except (TypeError, ValueError) as exc:
        raise DatabaseError(f"Confidence no es numerico: {confidence!r}.") from exc

    if not 0.0 <= value <= 1.0:
        raise DatabaseError(f"Confidence fuera de rango [0, 1]: {value}.")

    return value


def _coerce_optional_fraction(value: Any) -> float | None:
    """Convierte una fracción opcional a float validando [0, 1]; ``None`` pasa tal cual."""
    if value is None:
        return None
    try:
        fraction = float(value)
    except (TypeError, ValueError) as exc:
        raise DatabaseError(f"Fraccion no es numerica: {value!r}.") from exc

    if not 0.0 <= fraction <= 1.0:
        raise DatabaseError(f"Fraccion fuera de rango [0, 1]: {fraction}.")

    return fraction


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
        evidence_coverage=float(row[7]) if row[7] is not None else None,
        explanation=str(row[8]) if row[8] is not None else None,
        created_at=str(row[9]),
        status=str(row[10]),
        error_code=row[11],
        claims=row[12],
        sources=row[13],
        file_filename=row[14],
        share_token=row[15],
        stage=row[16] if len(row) > 16 else None,
    )


def _sanitize_history_query_params(
    *,
    limit: int,
    offset: int,
    source_type: Optional[str],
    sort: str,
) -> tuple[int, int, Optional[str], str]:
    """Normaliza límites, filtros y orden para consultas de historial."""
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    safe_source_type = source_type if source_type in _VALID_SOURCE_TYPES else None
    safe_order_by = _SORT_ORDER_BY.get(sort, _SORT_ORDER_BY[_DEFAULT_SORT])
    return safe_limit, safe_offset, safe_source_type, safe_order_by


def _build_history_where_clause(
    *,
    user_id: str,
    search_query: Optional[str],
    source_type: Optional[str],
    created_after: Optional[datetime],
    verdict: Optional[str] = None,
    status: Optional[str] = None,
) -> tuple[str, list[Any]]:
    """Construye cláusula WHERE y parámetros para historial paginado."""
    where_clauses = ["user_id = %s"]
    where_params: list[Any] = [user_id]

    # status=None lista cualquier estado (en curso, completado o fallido).
    if status in _VALID_STATUSES:
        where_clauses.append("status = %s")
        where_params.append(status)

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

    # Igualdad sobre la columna verdict (indexable); las filas pending/failed la tienen NULL.
    if verdict in _VALID_VERDICTS:
        where_clauses.append("verdict = %s")
        where_params.append(verdict)

    if created_after is not None:
        where_clauses.append("created_at >= %s")
        where_params.append(created_after)

    return " AND ".join(where_clauses), where_params


def _build_history_queries(where_sql: str, safe_order_by: str) -> tuple[str, str]:
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
            evidence_coverage,
            explanation,
            created_at,
            status,
            error_code,
            claims,
            sources,
            file_filename,
            share_token
        FROM public.analysis_history
        WHERE {where_sql}
        ORDER BY {order_by}
        LIMIT %s OFFSET %s
    """.format(where_sql=where_sql, order_by=safe_order_by)

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


async def create_pending_file_analysis(
    *,
    user_id: str,
    filename: str,
    data: bytes,
) -> str:
    """Inserta un análisis ``pending`` de tipo ``file`` guardando el binario."""
    pool = await get_pool()

    query = """
        INSERT INTO public.analysis_history
        (user_id, source_type, file_data, file_filename, status)
        VALUES (%s, 'file', %s, %s, 'pending')
        RETURNING id
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id, data, filename))
                inserted_row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error("No se pudo guardar el archivo en la base de datos.")
        ) from exc

    if not inserted_row:
        raise DatabaseError("No se pudo obtener el id del análisis guardado.")

    return str(inserted_row[0])


async def set_analysis_input_text(*, analysis_id: str, input_text: str) -> None:
    """Persiste el texto extraído de un archivo antes de ejecutar el pipeline."""
    pool = await get_pool()

    query = "UPDATE public.analysis_history SET input_text = %s WHERE id = %s"

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (input_text, analysis_id))
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo actualizar el texto del análisis en la base de datos."
            )
        ) from exc


async def set_analysis_stage(*, analysis_id: str, stage: str) -> None:
    """Registra el agente activo de un análisis en curso para el sondeo del detalle."""
    pool = await get_pool()

    query = (
        "UPDATE public.analysis_history SET stage = %s "
        "WHERE id = %s AND status = 'pending'"
    )

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (stage, analysis_id))
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo actualizar la etapa del análisis en la base de datos."
            )
        ) from exc


async def complete_analysis(
    *,
    analysis_id: str,
    label: str,
    confidence: Any,
    explanation: str,
    claims: Optional[list[dict]] = None,
    sources: Optional[list[dict]] = None,
    evidence_coverage: Any = None,
) -> None:
    """Marca un análisis pendiente como ``done`` con su resultado."""
    pool = await get_pool()
    confidence_value = _normalize_confidence(confidence)
    coverage_value = _coerce_optional_fraction(evidence_coverage)
    # El veredicto se deriva una sola vez aquí; label queda como texto de presentación.
    verdict_value = classify_verdict(label)

    query = """
        UPDATE public.analysis_history
        SET label = %s,
            verdict = %s,
            confidence = %s,
            evidence_coverage = %s,
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
                        verdict_value,
                        confidence_value,
                        coverage_value,
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


async def list_stale_pending_analysis_ids(*, older_than_seconds: int) -> list[str]:
    """Lista los ids de filas ``pending`` más antiguas que el umbral (candidatas del reaper)."""
    pool = await get_pool()

    query = """
        SELECT id::text
        FROM public.analysis_history
        WHERE status = 'pending'
          AND created_at < NOW() - make_interval(secs => %s)
    """

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


async def fail_stale_pending_analyses(
    *, analysis_ids: Sequence[str], older_than_seconds: int, error_code: str
) -> int:
    """Marca como ``failed`` las filas indicadas si siguen ``pending`` y estancadas.

    Devuelve cuántas filas se reciclaron. Re-verifica estado y antigüedad para no
    pisar un análisis reabierto (retry reinicia ``created_at``) entre la lectura
    de candidatas y esta escritura.
    """
    if not analysis_ids:
        return 0

    pool = await get_pool()

    query = """
        UPDATE public.analysis_history
        SET status = 'failed', error_code = %s
        WHERE id::text = ANY(%s)
          AND status = 'pending'
          AND created_at < NOW() - make_interval(secs => %s)
    """

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


async def list_user_analysis_history(
    *,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    search_query: Optional[str] = None,
    source_type: Optional[str] = None,
    created_after: Optional[datetime] = None,
    sort: str = "recent",
    verdict: Optional[str] = None,
    status: Optional[str] = None,
) -> tuple[list[AnalysisHistoryItem], int]:
    """Lista historial paginado del usuario y devuelve tambien el total."""
    pool = await get_pool()

    safe_limit, safe_offset, safe_source_type, safe_order_by = (
        _sanitize_history_query_params(
            limit=limit,
            offset=offset,
            source_type=source_type,
            sort=sort,
        )
    )
    where_sql, where_params = _build_history_where_clause(
        user_id=user_id,
        search_query=search_query,
        source_type=safe_source_type,
        created_after=created_after,
        verdict=verdict,
        status=status,
    )
    count_query, list_query = _build_history_queries(where_sql, safe_order_by)

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # where_sql/safe_order_by son valores saneados, no entrada cruda.
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


async def count_history_verdict_facets(
    *,
    user_id: str,
    search_query: Optional[str] = None,
    source_type: Optional[str] = None,
    created_after: Optional[datetime] = None,
) -> HistoryVerdictCounts:
    """Cuenta el historial por veredicto, ignorando el propio filtro de veredicto.

    Son conteos globales (no de la página actual): cada uno coincide con cuántas
    filas vería la tabla al pulsar esa tarjeta, conservando el resto de filtros.
    """
    pool = await get_pool()
    safe_source_type = source_type if source_type in _VALID_SOURCE_TYPES else None
    where_sql, where_params = _build_history_where_clause(
        user_id=user_id,
        search_query=search_query,
        source_type=safe_source_type,
        created_after=created_after,
    )

    facets_query = f"""
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN verdict = 'real' THEN 1 ELSE 0 END), 0) AS real_total,
            COALESCE(SUM(CASE WHEN verdict = 'fake' THEN 1 ELSE 0 END), 0) AS fake_total,
            COALESCE(SUM(CASE WHEN verdict = 'uncertain' THEN 1 ELSE 0 END), 0)
                AS uncertain_total
        FROM public.analysis_history
        WHERE {where_sql}
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # where_sql es texto saneado (cláusulas parametrizadas), no entrada cruda.
                await cur.execute(facets_query, tuple(where_params))  # pyright: ignore[reportArgumentType]
                row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo consultar el resumen del historial en la base de datos."
            )
        ) from exc

    if not row:
        return HistoryVerdictCounts(total=0, real=0, fake=0, uncertain=0)

    return HistoryVerdictCounts(
        total=int(row[0] or 0),
        real=int(row[1] or 0),
        fake=int(row[2] or 0),
        uncertain=int(row[3] or 0),
    )


async def count_history_source_type_facets(
    *,
    user_id: str,
    search_query: Optional[str] = None,
    verdict: Optional[str] = None,
    created_after: Optional[datetime] = None,
) -> HistorySourceTypeCounts:
    """Cuenta el historial por tipo de fuente, ignorando el propio filtro de tipo.

    Son conteos globales (no de la página actual): cada uno coincide con cuántas
    filas vería la tabla al pulsar ese chip, conservando el resto de filtros.
    """
    pool = await get_pool()
    safe_verdict = verdict if verdict in _VALID_VERDICTS else None
    where_sql, where_params = _build_history_where_clause(
        user_id=user_id,
        search_query=search_query,
        source_type=None,
        created_after=created_after,
        verdict=safe_verdict,
    )

    facets_query = f"""
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN source_type = 'text' THEN 1 ELSE 0 END), 0) AS text_total,
            COALESCE(SUM(CASE WHEN source_type = 'url' THEN 1 ELSE 0 END), 0) AS url_total,
            COALESCE(SUM(CASE WHEN source_type = 'file' THEN 1 ELSE 0 END), 0) AS file_total
        FROM public.analysis_history
        WHERE {where_sql}
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # where_sql es texto saneado (cláusulas parametrizadas), no entrada cruda.
                await cur.execute(facets_query, tuple(where_params))  # pyright: ignore[reportArgumentType]
                row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo consultar el resumen del historial en la base de datos."
            )
        ) from exc

    if not row:
        return HistorySourceTypeCounts(total=0, text=0, url=0, file=0)

    return HistorySourceTypeCounts(
        total=int(row[0] or 0),
        text=int(row[1] or 0),
        url=int(row[2] or 0),
        file=int(row[3] or 0),
    )


_EXPORT_MAX_ROWS = 10_000


async def export_user_analysis_history(
    *,
    user_id: str,
    search_query: Optional[str] = None,
    source_type: Optional[str] = None,
    created_after: Optional[datetime] = None,
    sort: str = "recent",
    verdict: Optional[str] = None,
) -> list[AnalysisHistoryItem]:
    """Lista todo el historial filtrado del usuario para exportarlo (sin paginar)."""
    pool = await get_pool()

    _, _, safe_source_type, safe_order_by = _sanitize_history_query_params(
        limit=1,
        offset=0,
        source_type=source_type,
        sort=sort,
    )
    where_sql, where_params = _build_history_where_clause(
        user_id=user_id,
        search_query=search_query,
        source_type=safe_source_type,
        created_after=created_after,
        verdict=verdict,
        status="done",
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
            evidence_coverage,
            explanation,
            created_at,
            status,
            error_code,
            claims,
            sources,
            file_filename,
            share_token
        FROM public.analysis_history
        WHERE {where_sql}
        ORDER BY {order_by}
        LIMIT %s
    """.format(where_sql=where_sql, order_by=safe_order_by)

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
            evidence_coverage,
            explanation,
            created_at,
            status,
            error_code,
            claims,
            sources,
            file_filename,
            share_token,
            stage
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


async def get_file_data_by_id(*, analysis_id: str) -> tuple[bytes, str | None] | None:
    """Devuelve ``(file_data, file_filename)`` de un análisis por id (uso del worker)."""
    pool = await get_pool()

    query = """
        SELECT file_data, file_filename
        FROM public.analysis_history
        WHERE id = %s AND source_type = 'file'
        LIMIT 1
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (analysis_id,))
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


async def reset_failed_analysis_to_pending(*, user_id: str, analysis_id: str) -> bool:
    """Reabre a ``pending`` un análisis ``failed`` propio. Devuelve True si cambió una fila."""
    pool = await get_pool()

    # created_at se reinicia a NOW(); stage se limpia para no mostrar la etapa del intento previo.
    query = """
        UPDATE public.analysis_history
        SET status = 'pending', error_code = NULL, stage = NULL, created_at = NOW()
        WHERE user_id = %s AND id = %s AND status = 'failed'
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id, analysis_id))
                return cur.rowcount > 0
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error("No se pudo reabrir el análisis en la base de datos.")
        ) from exc


async def reset_done_analysis_to_pending(*, user_id: str, analysis_id: str) -> bool:
    """Reabre a ``pending`` un análisis ``done`` propio para volver a analizarlo.

    Devuelve True si cambió una fila. Borra el resultado previo para no contarlo en
    agregados mientras se re-ejecuta; conserva la entrada, el archivo y el share_token.
    """
    pool = await get_pool()

    # created_at se reinicia a NOW(); el veredicto se limpia para
    # no seguir sumando en dashboard/historial mientras la fila está pending.
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
            error_code = NULL,
            stage = NULL,
            created_at = NOW()
        WHERE user_id = %s AND id = %s AND status = 'done'
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id, analysis_id))
                return cur.rowcount > 0
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error("No se pudo reabrir el análisis en la base de datos.")
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
            async with conn.cursor() as cur:
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
        source_type=str(row[0]),
        input_text=row[1],
        input_url=row[2],
        label=str(row[3]) if row[3] is not None else None,
        confidence=float(row[4]) if row[4] is not None else None,
        evidence_coverage=float(row[5]) if row[5] is not None else None,
        explanation=str(row[6]) if row[6] is not None else None,
        created_at=str(row[7]),
        status=str(row[8]),
        claims=row[9],
        sources=row[10],
        file_filename=row[11],
    )
