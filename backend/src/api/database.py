"""Utilidades de persistencia para guardar y consultar el historial de analisis."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from urllib.parse import urlparse
from typing import Any, Optional

from dotenv import load_dotenv
import psycopg2

from src.api.schemas import AnalyzeRequest

load_dotenv()

logger = logging.getLogger(__name__)


class HistoryDatabaseError(RuntimeError):
    """Error base para operaciones de persistencia del historial."""


@dataclass(frozen=True)
class HistoryRecord:
    """Representa una fila de historial de analisis."""

    id: str
    user_id: str
    source_type: str
    input_text: Optional[str]
    input_url: Optional[str]
    label: str
    confidence: float
    explanation: str
    created_at: str


@dataclass(frozen=True)
class DashboardKpis:
    """Resumen principal de métricas para el dashboard."""

    total_analyses: int
    reliable_rate: float
    average_confidence: float
    week_over_week_delta: float


@dataclass(frozen=True)
class DashboardTrendPoint:
    """Punto de tendencia diaria para el dashboard."""

    date: str
    total: int
    average_confidence: float


@dataclass(frozen=True)
class DashboardSourceBreakdownItem:
    """Distribución de análisis por tipo de fuente."""

    source_type: str
    total: int
    average_confidence: float


@dataclass(frozen=True)
class DashboardDomainBreakdownItem:
    """Distribución de análisis por dominio de URL."""

    domain: str
    total: int
    average_confidence: float


@dataclass(frozen=True)
class DashboardAlertItem:
    """Elemento de alerta para análisis de baja credibilidad."""

    id: str
    source_type: str
    input_text: Optional[str]
    input_url: Optional[str]
    label: str
    confidence: float
    created_at: str


@dataclass(frozen=True)
class DashboardSummary:
    """Respuesta consolidada para poblar el dashboard inicial."""

    kpis: DashboardKpis
    trend: list[DashboardTrendPoint]
    source_breakdown: list[DashboardSourceBreakdownItem]
    domain_breakdown: list[DashboardDomainBreakdownItem]
    alerts: list[DashboardAlertItem]


def _build_connection_string() -> str:
    """Obtiene la cadena de conexion desde la variable DATABASE_URL."""

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HistoryDatabaseError(
            "No se encontro la variable de entorno DATABASE_URL."
        )

    return db_url


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


def save_analysis_history(
    *,
    user_id: str,
    source_type: str,
    input_text: Optional[str],
    input_url: Optional[str],
    label: str,
    confidence: Any,
    explanation: str,
) -> str:
    """Guarda un analisis exitoso en public.analysis_history."""

    conninfo = _build_connection_string()
    confidence_value = _normalize_confidence(confidence)

    query = """
		INSERT INTO public.analysis_history
		(user_id, source_type, input_text, input_url, label, confidence, explanation)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
	"""

    try:
        with psycopg2.connect(conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        user_id,
                        source_type,
                        input_text,
                        input_url,
                        label,
                        confidence_value,
                        explanation,
                    ),
                )
                inserted_row = cur.fetchone()
            conn.commit()

            if not inserted_row:
                raise HistoryDatabaseError(
                    "No se pudo obtener el id del análisis guardado."
                )

            return str(inserted_row[0])
    except psycopg2.Error as exc:
        raise HistoryDatabaseError(
            "No se pudo guardar el analisis en la base de datos. "
            "Revisa DATABASE_URL y, si usas Supabase, prueba el host del pooler IPv4."
        ) from exc


def save_successful_analysis(
    *,
    user_id: str,
    request: AnalyzeRequest,
    label: str,
    confidence: Any,
    explanation: str,
) -> str | None:
    """
    Persistencia de analisis exitoso.
    Devuelve el id del analisis si se guardo correctamente y None en caso de error.
    El objetivo es no romper la respuesta de analisis por fallos temporales de BD.
    """

    source_type = request.source_type.value
    input_text = request.text if source_type in {"text", "file"} else None
    input_url = str(request.url) if source_type == "url" and request.url else None

    try:
        return save_analysis_history(
            user_id=user_id,
            source_type=source_type,
            input_text=input_text,
            input_url=input_url,
            label=label,
            confidence=confidence,
            explanation=explanation,
        )
    except (HistoryDatabaseError, psycopg2.Error) as exc:
        logger.exception("No se pudo guardar el historial de analisis: %s", exc)
        return None


def list_user_analysis_history(
    *,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    search_query: Optional[str] = None,
    source_type: Optional[str] = None,
    created_after: Optional[datetime] = None,
    score_sort_order: str = "desc",
) -> tuple[list[HistoryRecord], int]:
    """Lista historial paginado del usuario y devuelve tambien el total."""

    conninfo = _build_connection_string()

    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    safe_source_type = source_type if source_type in {"text", "file", "url"} else None
    safe_score_sort = "ASC" if score_sort_order.lower() == "asc" else "DESC"

    where_clauses = ["user_id = %s"]
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

    if safe_source_type:
        where_clauses.append("source_type = %s")
        where_params.append(safe_source_type)

    if created_after is not None:
        where_clauses.append("created_at >= %s")
        where_params.append(created_after)

    where_sql = " AND ".join(where_clauses)

    count_query = f"""
        SELECT COUNT(*)
        FROM public.analysis_history
        WHERE {where_sql}
    """

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
			created_at
		FROM public.analysis_history
		WHERE {where_sql}
		ORDER BY confidence {safe_score_sort}, created_at DESC
		LIMIT %s OFFSET %s
	""".format(
        where_sql=where_sql, safe_score_sort=safe_score_sort
    )

    try:
        with psycopg2.connect(conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(count_query, tuple(where_params))
                count_row = cur.fetchone()
                total_count = int(count_row[0]) if count_row else 0

                cur.execute(query, (*where_params, safe_limit, safe_offset))
                rows = cur.fetchall()
    except psycopg2.Error as exc:
        raise HistoryDatabaseError(
            "No se pudo consultar el historial en la base de datos. "
            "Revisa DATABASE_URL y, si usas Supabase, prueba el host del pooler IPv4."
        ) from exc

    records = [
        HistoryRecord(
            id=str(row[0]),
            user_id=row[1],
            source_type=row[2],
            input_text=row[3],
            input_url=row[4],
            label=row[5],
            confidence=float(row[6]),
            explanation=row[7],
            created_at=str(row[8]),
        )
        for row in rows
    ]

    return records, total_count


def get_user_analysis_by_id(*, user_id: str, analysis_id: str) -> HistoryRecord | None:
    """Obtiene un analisis por id para un usuario autenticado."""

    conninfo = _build_connection_string()

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
			created_at
		FROM public.analysis_history
		WHERE user_id = %s AND id = %s
		LIMIT 1
	"""

    try:
        with psycopg2.connect(conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (user_id, analysis_id))
                row = cur.fetchone()
    except psycopg2.Error as exc:
        raise HistoryDatabaseError(
            "No se pudo consultar el análisis en la base de datos. "
            "Revisa DATABASE_URL y, si usas Supabase, prueba el host del pooler IPv4."
        ) from exc

    if not row:
        return None

    return HistoryRecord(
        id=str(row[0]),
        user_id=row[1],
        source_type=row[2],
        input_text=row[3],
        input_url=row[4],
        label=row[5],
        confidence=float(row[6]),
        explanation=row[7],
        created_at=str(row[8]),
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


def get_user_dashboard_summary(
    *, user_id: str, trend_days: int = 14, alert_limit: int = 5
) -> DashboardSummary:
    """Obtiene métricas agregadas para el dashboard del usuario."""

    conninfo = _build_connection_string()
    safe_trend_days = max(7, min(trend_days, 90))
    safe_alert_limit = max(1, min(alert_limit, 20))

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
        WHERE user_id = %s
    """

    trend_query = """
        SELECT
            DATE(created_at) AS day,
            COUNT(*) AS total,
            AVG(confidence) AS average_confidence
        FROM public.analysis_history
        WHERE user_id = %s
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
        WHERE user_id = %s
        GROUP BY source_type
        ORDER BY total DESC
    """

    domain_query = """
        SELECT
            input_url,
            confidence
        FROM public.analysis_history
        WHERE user_id = %s
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
          AND confidence <= 0.35
        ORDER BY created_at DESC
        LIMIT %s
    """

    trend_start_date = datetime.utcnow().date() - timedelta(days=safe_trend_days - 1)

    try:
        with psycopg2.connect(conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(kpis_query, (user_id,))
                kpi_row = cur.fetchone()

                cur.execute(trend_query, (user_id, trend_start_date))
                trend_rows = cur.fetchall()

                cur.execute(source_query, (user_id,))
                source_rows = cur.fetchall()

                cur.execute(domain_query, (user_id,))
                domain_rows = cur.fetchall()

                cur.execute(alerts_query, (user_id, safe_alert_limit))
                alert_rows = cur.fetchall()
    except psycopg2.Error as exc:
        raise HistoryDatabaseError(
            "No se pudo consultar el resumen del dashboard en la base de datos. "
            "Revisa DATABASE_URL y, si usas Supabase, prueba el host del pooler IPv4."
        ) from exc

    total_analyses = int(kpi_row[0] or 0) if kpi_row else 0
    average_confidence = float(kpi_row[1] or 0.0) if kpi_row else 0.0
    reliable_total = int(kpi_row[2] or 0) if kpi_row else 0
    current_week_total = int(kpi_row[3] or 0) if kpi_row else 0
    previous_week_total = int(kpi_row[4] or 0) if kpi_row else 0

    reliable_rate = (
        round((reliable_total / total_analyses) * 100, 1) if total_analyses else 0.0
    )

    if previous_week_total == 0:
        week_over_week_delta = 0.0 if current_week_total == 0 else 100.0
    else:
        week_over_week_delta = round(
            ((current_week_total - previous_week_total) / previous_week_total) * 100,
            1,
        )

    trend_map: dict[date, tuple[int, float]] = {}
    for row in trend_rows:
        row_day: date = row[0]
        row_total = int(row[1] or 0)
        row_avg_confidence = float(row[2] or 0.0)
        trend_map[row_day] = (row_total, row_avg_confidence)

    trend_points: list[DashboardTrendPoint] = []
    for day_offset in range(safe_trend_days):
        point_day = trend_start_date + timedelta(days=day_offset)
        point_total, point_avg_confidence = trend_map.get(point_day, (0, 0.0))
        trend_points.append(
            DashboardTrendPoint(
                date=point_day.isoformat(),
                total=point_total,
                average_confidence=round(point_avg_confidence * 100, 1),
            )
        )

    source_breakdown = [
        DashboardSourceBreakdownItem(
            source_type=str(row[0]),
            total=int(row[1] or 0),
            average_confidence=_round_percentage(float(row[2] or 0.0)),
        )
        for row in source_rows
    ]

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
    )[:5]

    domain_breakdown = [
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

    alerts = [
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

    return DashboardSummary(
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
