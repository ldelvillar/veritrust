"""Consultas analíticas agregadas para el dashboard del usuario."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Sequence
from urllib.parse import urlparse

import psycopg

from app.db.pool import DatabaseError, _build_database_error, get_pool
from app.schemas.dashboard import (
    DashboardAlertItem,
    DashboardDomainBreakdownItem,
    DashboardKpis,
    DashboardSourceBreakdownItem,
    DashboardSummaryResponse,
    DashboardTrendPoint,
)

logger = logging.getLogger(__name__)


def _sanitize_dashboard_params(*, trend_days: int, alert_limit: int) -> tuple[int, int]:
    """Normaliza parámetros de dashboard para mantener límites seguros."""
    safe_trend_days = max(7, min(trend_days, 90))
    safe_alert_limit = max(1, min(alert_limit, 20))
    return safe_trend_days, safe_alert_limit


def _extract_kpis_values(
    kpi_row: Sequence[Any] | None,
) -> tuple[int, float, int, int, int, int]:
    """Extrae valores de KPI con defaults cuando no hay resultados."""
    total_analyses = int(kpi_row[0] or 0) if kpi_row else 0
    average_confidence = float(kpi_row[1] or 0.0) if kpi_row else 0.0
    reliable_total = int(kpi_row[2] or 0) if kpi_row else 0
    current_week_total = int(kpi_row[3] or 0) if kpi_row else 0
    previous_week_total = int(kpi_row[4] or 0) if kpi_row else 0
    active_alerts = int(kpi_row[5] or 0) if kpi_row else 0
    return (
        total_analyses,
        average_confidence,
        reliable_total,
        current_week_total,
        previous_week_total,
        active_alerts,
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
    """Convierte una proporción [0, 1] en porcentaje acotado a [0, 100]."""
    if value is None:
        return 0.0
    return round(max(0.0, min(100.0, value * 100)), 1)


def _extract_domain(url: str | None) -> str | None:
    """Devuelve el host en minúsculas de una URL, o None si no es válida."""
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
            ) AS previous_week_total,
            SUM(
                CASE
                    WHEN LOWER(COALESCE(label, '')) LIKE 'fals%%'
                      OR LOWER(COALESCE(label, '')) LIKE 'fake%%'
                    THEN 1
                    ELSE 0
                END
            ) AS active_alerts
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
          AND (
              LOWER(COALESCE(label, '')) LIKE 'fals%%'
              OR LOWER(COALESCE(label, '')) LIKE 'fake%%'
          )
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
        raise DatabaseError(
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
        active_alerts,
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
            active_alerts=active_alerts,
        ),
        trend=trend_points,
        source_breakdown=source_breakdown,
        domain_breakdown=domain_breakdown,
        alerts=alerts,
    )
