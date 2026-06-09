"""Tests unitarios para helpers internos de la capa de persistencia (db/)."""

from datetime import date, datetime, timezone

import pytest

from app.core.config import Settings
from app.db import dashboard as dashboard_module
from app.db import history as history_module
from app.db import pool as pool_module
from app.db.pool import DatabaseError
from app.schemas.dashboard import (
    DashboardAlertItem,
    DashboardDomainBreakdownItem,
    DashboardSourceBreakdownItem,
    DashboardTrendPoint,
)
from app.schemas.history import AnalysisHistoryItem


def _use_database_url(monkeypatch, database_url: str) -> None:
    """Hace que _build_connection_string lea una configuración controlada."""
    settings = Settings(_env_file=None, database_url=database_url)  # type: ignore[call-arg]
    monkeypatch.setattr(pool_module, "get_settings", lambda: settings)


def test_build_connection_string_returns_database_url(monkeypatch) -> None:
    _use_database_url(monkeypatch, "postgresql://user:pass@localhost:5432/db")

    conninfo = pool_module._build_connection_string()

    assert conninfo == "postgresql://user:pass@localhost:5432/db"


def test_build_connection_string_raises_when_database_url_is_missing(
    monkeypatch,
) -> None:
    _use_database_url(monkeypatch, "")

    with pytest.raises(DatabaseError) as exc:
        pool_module._build_connection_string()

    assert "DATABASE_URL" in str(exc.value)


def test_build_database_error_appends_configuration_hint() -> None:
    message = pool_module._build_database_error("Error base.")

    assert message.startswith("Error base.")
    assert "DATABASE_URL" in message


def test_normalize_confidence_accepts_valid_numeric_values() -> None:
    assert history_module._normalize_confidence(0) == 0.0
    assert history_module._normalize_confidence("1") == 1.0
    assert history_module._normalize_confidence(0.75) == 0.75


def test_normalize_confidence_rejects_non_numeric_values() -> None:
    with pytest.raises(DatabaseError) as exc:
        history_module._normalize_confidence("no-num")

    assert "no es numerico" in str(exc.value)


def test_normalize_confidence_rejects_out_of_range_values() -> None:
    with pytest.raises(DatabaseError):
        history_module._normalize_confidence(1.2)

    with pytest.raises(DatabaseError):
        history_module._normalize_confidence(-0.01)


def test_map_history_record_converts_sql_row_to_dataclass() -> None:
    row = (
        123,
        "user-1",
        "text",
        "contenido",
        None,
        "falsa",
        0.81,
        "explicacion",
        datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
        "done",
        None,
        [{"text": "Afirmación", "label": "falsa", "confidence": 0.81}],
        [{"title": "Estudio", "url": "https://doi.org/10.1/x", "source": "BMJ"}],
        None,
    )

    record = history_module._map_history_record(row)

    assert isinstance(record, AnalysisHistoryItem)
    assert record.analysis_id == "123"
    assert record.user_id == "user-1"
    assert record.confidence == 0.81
    assert record.status == "done"
    assert record.error_code is None
    assert record.created_at.startswith("2026-04-10")
    assert record.claims is not None
    assert record.claims[0].label == "falsa"
    assert record.sources is not None
    assert record.sources[0].source == "BMJ"


def test_map_history_record_handles_pending_row_with_null_results() -> None:
    row = (
        123,
        "user-1",
        "text",
        "contenido",
        None,
        None,
        None,
        None,
        datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
        "pending",
        None,
        None,
        None,
        None,
    )

    record = history_module._map_history_record(row)

    assert record.status == "pending"
    assert record.label is None
    assert record.confidence is None
    assert record.explanation is None
    assert record.claims is None
    assert record.sources is None


def test_sanitize_history_query_params_clamps_and_normalizes_values() -> None:
    safe_limit, safe_offset, safe_source_type, safe_date_sort = (
        history_module._sanitize_history_query_params(
            limit=500,
            offset=-10,
            source_type="audio",
            date_sort_order="zzz",
        )
    )

    assert safe_limit == 100
    assert safe_offset == 0
    assert safe_source_type is None
    assert safe_date_sort == "DESC"


def test_sanitize_history_query_params_preserves_valid_values() -> None:
    safe_limit, safe_offset, safe_source_type, safe_date_sort = (
        history_module._sanitize_history_query_params(
            limit=25,
            offset=5,
            source_type="url",
            date_sort_order="asc",
        )
    )

    assert safe_limit == 25
    assert safe_offset == 5
    assert safe_source_type == "url"
    assert safe_date_sort == "ASC"


def test_build_history_where_clause_with_only_user_id() -> None:
    where_sql, params = history_module._build_history_where_clause(
        user_id="user-1",
        search_query=None,
        source_type=None,
        created_after=None,
    )

    assert where_sql == "user_id = %s AND status = 'done'"
    assert params == ["user-1"]


def test_build_history_where_clause_with_search_filters_and_date() -> None:
    created_after = datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)
    where_sql, params = history_module._build_history_where_clause(
        user_id="user-2",
        search_query="  covid  ",
        source_type="text",
        created_after=created_after,
    )

    assert "COALESCE(input_text, '') ILIKE %s" in where_sql
    assert "source_type = %s" in where_sql
    assert "created_at >= %s" in where_sql
    assert params == [
        "user-2",
        "%covid%",
        "%covid%",
        "%covid%",
        "%covid%",
        "text",
        created_after,
    ]


def test_build_history_where_clause_filters_by_fake_verdict() -> None:
    where_sql, params = history_module._build_history_where_clause(
        user_id="user-1",
        search_query=None,
        source_type=None,
        created_after=None,
        verdict="fake",
    )

    assert "LIKE '%%fals%%'" in where_sql
    assert "LIKE '%%fake%%'" in where_sql
    # La cláusula de veredicto es constante: no añade parámetros.
    assert params == ["user-1"]


def test_build_history_where_clause_uncertain_excludes_real_and_fake() -> None:
    where_sql, params = history_module._build_history_where_clause(
        user_id="user-1",
        search_query=None,
        source_type=None,
        created_after=None,
        verdict="uncertain",
    )

    assert where_sql.endswith(
        f"AND (NOT {history_module._VERDICT_REAL_SQL} "
        f"AND NOT {history_module._VERDICT_FAKE_SQL})"
    )
    assert params == ["user-1"]


def test_build_history_where_clause_ignores_unknown_verdict() -> None:
    where_sql, params = history_module._build_history_where_clause(
        user_id="user-1",
        search_query=None,
        source_type=None,
        created_after=None,
        verdict="bogus",
    )

    assert where_sql == "user_id = %s AND status = 'done'"
    assert params == ["user-1"]


def test_build_history_queries_includes_ordering_and_where() -> None:
    count_query, list_query = history_module._build_history_queries(
        "user_id = %s",
        "ASC",
    )

    assert "SELECT COUNT(*)" in count_query
    assert "WHERE user_id = %s" in count_query
    assert "ORDER BY created_at ASC" in list_query
    assert "LIMIT %s OFFSET %s" in list_query


def test_sanitize_dashboard_params_clamps_values() -> None:
    safe_trend_days, safe_alert_limit = dashboard_module._sanitize_dashboard_params(
        trend_days=1,
        alert_limit=999,
    )

    assert safe_trend_days == 7
    assert safe_alert_limit == 20


def test_extract_kpis_values_handles_none_and_row_values() -> None:
    assert dashboard_module._extract_kpis_values(None) == (0, 0.0, 0, 0, 0, 0)
    assert dashboard_module._extract_kpis_values((10, 0.83, 7, 4, 2, 3)) == (
        10,
        0.83,
        7,
        4,
        2,
        3,
    )


def test_calculate_reliable_rate_handles_zero_and_rounding() -> None:
    assert (
        dashboard_module._calculate_reliable_rate(
            reliable_total=0,
            total_analyses=0,
        )
        == 0.0
    )
    assert (
        dashboard_module._calculate_reliable_rate(
            reliable_total=1,
            total_analyses=3,
        )
        == 33.3
    )


def test_calculate_week_over_week_delta_covers_edge_cases() -> None:
    assert (
        dashboard_module._calculate_week_over_week_delta(
            current_week_total=0,
            previous_week_total=0,
        )
        == 0.0
    )
    assert (
        dashboard_module._calculate_week_over_week_delta(
            current_week_total=5,
            previous_week_total=0,
        )
        == 100.0
    )
    assert (
        dashboard_module._calculate_week_over_week_delta(
            current_week_total=3,
            previous_week_total=2,
        )
        == 50.0
    )


def test_round_percentage_clamps_and_rounds_values() -> None:
    assert dashboard_module._round_percentage(None) == 0.0
    assert dashboard_module._round_percentage(0.1234) == 12.3
    assert dashboard_module._round_percentage(1.8) == 100.0
    assert dashboard_module._round_percentage(-0.2) == 0.0


def test_extract_domain_returns_normalized_host() -> None:
    assert dashboard_module._extract_domain("https://Example.COM/path") == "example.com"
    assert dashboard_module._extract_domain("notaurl") is None
    assert dashboard_module._extract_domain(None) is None


def test_build_trend_points_creates_contiguous_daily_series() -> None:
    trend_rows = [
        (date(2026, 4, 1), 2, 0.5),
        (date(2026, 4, 3), 1, 0.75),
    ]

    points = dashboard_module._build_trend_points(
        trend_rows=trend_rows,
        trend_start_date=date(2026, 4, 1),
        trend_days=3,
    )

    assert len(points) == 3
    assert isinstance(points[0], DashboardTrendPoint)
    assert points[0].date == "2026-04-01"
    assert points[0].total == 2
    assert points[0].average_confidence == 50.0
    assert points[1].date == "2026-04-02"
    assert points[1].total == 0
    assert points[1].average_confidence == 0.0
    assert points[2].average_confidence == 75.0


def test_build_source_breakdown_maps_rows_to_dataclasses() -> None:
    rows = [("url", 3, 0.91), ("text", 1, None)]

    result = dashboard_module._build_source_breakdown(rows)

    assert len(result) == 2
    assert isinstance(result[0], DashboardSourceBreakdownItem)
    assert result[0].source_type == "url"
    assert result[0].total == 3
    assert result[0].average_confidence == 91.0
    assert result[1].average_confidence == 0.0


def test_build_domain_breakdown_aggregates_domains_and_applies_limit() -> None:
    domain_rows = [
        ("https://a.com/one", 0.9),
        ("https://A.com/two", 0.7),
        ("https://b.com", 0.5),
        ("notaurl", 0.3),
        (None, 0.2),
    ]

    result = dashboard_module._build_domain_breakdown(domain_rows=domain_rows, limit=1)

    assert len(result) == 1
    assert isinstance(result[0], DashboardDomainBreakdownItem)
    assert result[0].domain == "a.com"
    assert result[0].total == 2
    assert result[0].average_confidence == 80.0


def test_build_alerts_maps_rows_to_alert_items() -> None:
    alert_rows = [
        (
            99,
            "url",
            None,
            "https://example.com",
            "falsa",
            0.21,
            datetime(2026, 4, 10, 15, 0, tzinfo=timezone.utc),
        )
    ]

    alerts = dashboard_module._build_alerts(alert_rows)

    assert len(alerts) == 1
    assert isinstance(alerts[0], DashboardAlertItem)
    assert alerts[0].id == "99"
    assert alerts[0].source_type == "url"
    assert alerts[0].confidence == 0.21
    assert alerts[0].created_at.startswith("2026-04-10")
