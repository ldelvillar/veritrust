"""Utilidades de persistencia para guardar y consultar el historial de analisis."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional, Sequence
from urllib.parse import urlparse

import psycopg
from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings
from app.schemas.analysis import AnalysisRequest
from app.schemas.dashboard import (
    DashboardAlertItem,
    DashboardDomainBreakdownItem,
    DashboardKpis,
    DashboardSourceBreakdownItem,
    DashboardSummaryResponse,
    DashboardTrendPoint,
)
from app.schemas.history import AnalysisHistoryItem

logger = logging.getLogger(__name__)

_DATABASE_CONFIGURATION_HINT = (
    "Revisa DATABASE_URL y que el servicio de PostgreSQL esté accesible."
)
_VALID_SOURCE_TYPES = {"text", "file", "url"}


class HistoryDatabaseError(RuntimeError):
    """Error base para operaciones de persistencia del historial."""


def _build_connection_string() -> str:
    """Obtiene la cadena de conexion desde la configuracion central."""

    db_url = get_settings().database_url
    if not db_url:
        raise HistoryDatabaseError(
            "No se encontro la variable de entorno DATABASE_URL."
        )

    return db_url


_pool: AsyncConnectionPool | None = None


async def get_pool() -> AsyncConnectionPool:
    """Devuelve un pool async compartido, abriéndolo bajo demanda.

    El lifespan de la aplicación llama a este helper al arrancar para pagar el
    handshake una sola vez; los tests parchean las funciones DB del módulo, por
    lo que el pool nunca se inicializa durante la suite.
    """

    global _pool
    if _pool is None:
        conninfo = _build_connection_string()
        pool = AsyncConnectionPool(conninfo, min_size=1, max_size=10, open=False)
        await pool.open()
        _pool = pool
    return _pool


async def close_pool() -> None:
    """Cierra el pool si está abierto. Llamado desde el lifespan."""

    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _build_database_error(context_message: str) -> str:
    """Construye mensajes de error de BD consistentes para todas las operaciones."""

    return f"{context_message} {_DATABASE_CONFIGURATION_HINT}"


def _normalize_confidence(confidence: Any) -> float:
    """Convierte confidence a float y valida el rango [0, 1]."""

    try:
        value = float(confidence)
    except (TypeError, ValueError) as exc:
        raise HistoryDatabaseError(
            f"Confidence no es numerico: {confidence!r}."
        ) from exc

    if not 0.0 <= value <= 1.0:
        raise HistoryDatabaseError(f"Confidence fuera de rango [0, 1]: {value}.")

    return value


def _map_history_record(row: Sequence[Any]) -> AnalysisHistoryItem:
    """Mapea una fila SQL a un registro de historial tipado.

    Las columnas de resultado (label/confidence/explanation) son NULL mientras
    el análisis está ``pending`` y se rellenan cuando el worker termina.
    """

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
            error_code
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
    """Inserta un análisis en estado ``pending`` y devuelve su id.

    La ruta llama a esto de forma síncrona para reservar un id antes de encolar
    el trabajo en arq; el worker rellena el resultado más tarde. Propaga
    ``HistoryDatabaseError`` si la inserción falla (sin id no se puede encolar
    nada ni navegar al detalle).
    """

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
        raise HistoryDatabaseError(
            _build_database_error("No se pudo guardar el analisis en la base de datos.")
        ) from exc

    if not inserted_row:
        raise HistoryDatabaseError("No se pudo obtener el id del análisis guardado.")

    return str(inserted_row[0])


async def complete_analysis(
    *,
    analysis_id: str,
    label: str,
    confidence: Any,
    explanation: str,
) -> None:
    """Marca un análisis pendiente como ``done`` con su resultado. Usado por el worker."""

    pool = await get_pool()
    confidence_value = _normalize_confidence(confidence)

    query = """
        UPDATE public.analysis_history
        SET label = %s,
            confidence = %s,
            explanation = %s,
            status = 'done',
            error_code = NULL
        WHERE id = %s
    """

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    query, (label, confidence_value, explanation, analysis_id)
                )
    except psycopg.Error as exc:
        raise HistoryDatabaseError(
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
        raise HistoryDatabaseError(
            _build_database_error(
                "No se pudo actualizar el analisis en la base de datos."
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
                # count_query/list_query are str from .format() — pyright
                # cannot trace them back to LiteralString, but the dynamic
                # components (where_sql, safe_score_sort) are sanitized.
                await cur.execute(count_query, tuple(where_params))  # pyright: ignore[reportArgumentType]
                count_row = await cur.fetchone()
                total_count = int(count_row[0]) if count_row else 0

                await cur.execute(list_query, (*where_params, safe_limit, safe_offset))  # pyright: ignore[reportArgumentType]
                rows = await cur.fetchall()
    except psycopg.Error as exc:
        raise HistoryDatabaseError(
            _build_database_error(
                "No se pudo consultar el historial en la base de datos."
            )
        ) from exc

    records = [_map_history_record(row) for row in rows]

    return records, total_count


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
            error_code
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
        raise HistoryDatabaseError(
            _build_database_error(
                "No se pudo consultar el análisis en la base de datos."
            )
        ) from exc

    if not row:
        return None

    return _map_history_record(row)


def _sanitize_dashboard_params(*, trend_days: int, alert_limit: int) -> tuple[int, int]:
    """Normaliza parámetros de dashboard para mantener límites seguros."""

    safe_trend_days = max(7, min(trend_days, 90))
    safe_alert_limit = max(1, min(alert_limit, 20))
    return safe_trend_days, safe_alert_limit


def _extract_kpis_values(
    kpi_row: Sequence[Any] | None,
) -> tuple[int, float, int, int, int]:
    """Extrae valores de KPI con defaults cuando no hay resultados."""

    total_analyses = int(kpi_row[0] or 0) if kpi_row else 0
    average_confidence = float(kpi_row[1] or 0.0) if kpi_row else 0.0
    reliable_total = int(kpi_row[2] or 0) if kpi_row else 0
    current_week_total = int(kpi_row[3] or 0) if kpi_row else 0
    previous_week_total = int(kpi_row[4] or 0) if kpi_row else 0
    return (
        total_analyses,
        average_confidence,
        reliable_total,
        current_week_total,
        previous_week_total,
    )


def _calculate_reliable_rate(*, reliable_total: int, total_analyses: int) -> float:
    """Calcula porcentaje de análisis etiquetados como fiables."""

    if total_analyses == 0:
        return 0.0
    return round((reliable_total / total_analyses) * 100, 1)


def _calculate_week_over_week_delta(
    *, current_week_total: int, previous_week_total: int
) -> float:
    """Calcula variación semanal porcentual con manejo de división por cero."""

    if previous_week_total == 0:
        return 0.0 if current_week_total == 0 else 100.0

    return round(
        ((current_week_total - previous_week_total) / previous_week_total) * 100,
        1,
    )


def _round_percentage(value: float | None) -> float:
    if value is None:
        return 0.0
    return round(max(0.0, min(100.0, value * 100)), 1)


def _extract_domain(url: str | None) -> str | None:
    if not url:
        return None

    try:
        host = urlparse(url).hostname
    except ValueError:
        return None

    return host.lower() if host else None


def _build_trend_points(
    *, trend_rows: Sequence[Sequence[Any]], trend_start_date: date, trend_days: int
) -> list[DashboardTrendPoint]:
    """Construye una serie diaria continua para tendencia de dashboard."""

    trend_map: dict[date, tuple[int, float]] = {}
    for row in trend_rows:
        row_day: date = row[0]
        row_total = int(row[1] or 0)
        row_avg_confidence = float(row[2] or 0.0)
        trend_map[row_day] = (row_total, row_avg_confidence)

    trend_points: list[DashboardTrendPoint] = []
    for day_offset in range(trend_days):
        point_day = trend_start_date + timedelta(days=day_offset)
        point_total, point_avg_confidence = trend_map.get(point_day, (0, 0.0))
        trend_points.append(
            DashboardTrendPoint(
                date=point_day.isoformat(),
                total=point_total,
                average_confidence=round(point_avg_confidence * 100, 1),
            )
        )

    return trend_points


def _build_source_breakdown(
    source_rows: Sequence[Sequence[Any]],
) -> list[DashboardSourceBreakdownItem]:
    """Mapea la distribución por fuente para el dashboard."""

    return [
        DashboardSourceBreakdownItem(
            source_type=str(row[0]),
            total=int(row[1] or 0),
            average_confidence=_round_percentage(float(row[2] or 0.0)),
        )
        for row in source_rows
    ]


def _build_domain_breakdown(
    *, domain_rows: Sequence[Sequence[Any]], limit: int = 5
) -> list[DashboardDomainBreakdownItem]:
    """Agrega y ordena dominios de URL por frecuencia para el dashboard."""

    domain_aggregates: dict[str, dict[str, float]] = {}
    for row in domain_rows:
        domain = _extract_domain(row[0])
        if not domain:
            continue

        confidence = float(row[1] or 0.0)
        if domain not in domain_aggregates:
            domain_aggregates[domain] = {"total": 0.0, "sum_confidence": 0.0}

        domain_aggregates[domain]["total"] += 1
        domain_aggregates[domain]["sum_confidence"] += confidence

    sorted_domains = sorted(
        domain_aggregates.items(),
        key=lambda item: item[1]["total"],
        reverse=True,
    )[:limit]

    return [
        DashboardDomainBreakdownItem(
            domain=domain,
            total=int(values["total"]),
            average_confidence=_round_percentage(
                values["sum_confidence"] / values["total"]
            ),
        )
        for domain, values in sorted_domains
        if values["total"] > 0
    ]


def _build_alerts(alert_rows: Sequence[Sequence[Any]]) -> list[DashboardAlertItem]:
    """Mapea filas de alertas (baja credibilidad) para el dashboard."""

    return [
        DashboardAlertItem(
            id=str(row[0]),
            source_type=str(row[1]),
            input_text=row[2],
            input_url=row[3],
            label=str(row[4]),
            confidence=float(row[5] or 0.0),
            created_at=str(row[6]),
        )
        for row in alert_rows
    ]


async def get_user_dashboard_summary(
    *, user_id: str, trend_days: int = 14, alert_limit: int = 5
) -> DashboardSummaryResponse:
    """Obtiene métricas agregadas para el dashboard del usuario."""

    pool = await get_pool()
    safe_trend_days, safe_alert_limit = _sanitize_dashboard_params(
        trend_days=trend_days,
        alert_limit=alert_limit,
    )

    kpis_query = """
        SELECT
            COUNT(*) AS total_analyses,
            AVG(confidence) AS average_confidence,
            SUM(
                CASE
                    WHEN LOWER(COALESCE(label, '')) LIKE 'verdad%%'
                      OR LOWER(COALESCE(label, '')) LIKE 'true%%'
                    THEN 1
                    ELSE 0
                END
            ) AS reliable_total,
            SUM(
                CASE
                    WHEN created_at >= NOW() - INTERVAL '7 days'
                    THEN 1
                    ELSE 0
                END
            ) AS current_week_total,
            SUM(
                CASE
                    WHEN created_at < NOW() - INTERVAL '7 days'
                     AND created_at >= NOW() - INTERVAL '14 days'
                    THEN 1
                    ELSE 0
                END
            ) AS previous_week_total
        FROM public.analysis_history
        WHERE user_id = %s AND status = 'done'
    """

    trend_query = """
        SELECT
            DATE(created_at) AS day,
            COUNT(*) AS total,
            AVG(confidence) AS average_confidence
        FROM public.analysis_history
        WHERE user_id = %s
          AND status = 'done'
          AND created_at >= %s
        GROUP BY day
        ORDER BY day ASC
    """

    source_query = """
        SELECT
            source_type,
            COUNT(*) AS total,
            AVG(confidence) AS average_confidence
        FROM public.analysis_history
        WHERE user_id = %s AND status = 'done'
        GROUP BY source_type
        ORDER BY total DESC
    """

    domain_query = """
        SELECT
            input_url,
            confidence
        FROM public.analysis_history
        WHERE user_id = %s
          AND status = 'done'
          AND input_url IS NOT NULL
    """

    alerts_query = """
        SELECT
            id,
            source_type,
            input_text,
            input_url,
            label,
            confidence,
            created_at
        FROM public.analysis_history
        WHERE user_id = %s
          AND status = 'done'
          AND confidence <= 0.35
        ORDER BY created_at DESC
        LIMIT %s
    """

    trend_start_date = datetime.now(timezone.utc).date() - timedelta(
        days=safe_trend_days - 1
    )

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(kpis_query, (user_id,))
                kpi_row = await cur.fetchone()

                await cur.execute(trend_query, (user_id, trend_start_date))
                trend_rows = await cur.fetchall()

                await cur.execute(source_query, (user_id,))
                source_rows = await cur.fetchall()

                await cur.execute(domain_query, (user_id,))
                domain_rows = await cur.fetchall()

                await cur.execute(alerts_query, (user_id, safe_alert_limit))
                alert_rows = await cur.fetchall()
    except psycopg.Error as exc:
        raise HistoryDatabaseError(
            _build_database_error(
                "No se pudo consultar el resumen del dashboard en la base de datos."
            )
        ) from exc

    (
        total_analyses,
        average_confidence,
        reliable_total,
        current_week_total,
        previous_week_total,
    ) = _extract_kpis_values(kpi_row)

    reliable_rate = _calculate_reliable_rate(
        reliable_total=reliable_total,
        total_analyses=total_analyses,
    )
    week_over_week_delta = _calculate_week_over_week_delta(
        current_week_total=current_week_total,
        previous_week_total=previous_week_total,
    )

    trend_points = _build_trend_points(
        trend_rows=trend_rows,
        trend_start_date=trend_start_date,
        trend_days=safe_trend_days,
    )
    source_breakdown = _build_source_breakdown(source_rows)
    domain_breakdown = _build_domain_breakdown(domain_rows=domain_rows, limit=5)
    alerts = _build_alerts(alert_rows)

    return DashboardSummaryResponse(
        status="success",
        kpis=DashboardKpis(
            total_analyses=total_analyses,
            reliable_rate=reliable_rate,
            average_confidence=_round_percentage(average_confidence),
            week_over_week_delta=week_over_week_delta,
        ),
        trend=trend_points,
        source_breakdown=source_breakdown,
        domain_breakdown=domain_breakdown,
        alerts=alerts,
    )
