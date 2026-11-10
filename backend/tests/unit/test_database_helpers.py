"""Unit tests for the internal helpers of the persistence layer (db/)."""

from datetime import date, datetime, timezone

import pytest

from app.core.config import Settings
from app.db import dashboard as dashboard_module
from app.db import history_query as history_query_module
from app.db import pool as pool_module
from app.db.pool import DatabaseError
from app.schemas.dashboard import (
    DashboardAlertItem,
    DashboardDomainBreakdownItem,
    DashboardSourceBreakdownItem,
    DashboardTrendPoint,
)


def _use_database_url(monkeypatch, database_url: str) -> None:
    """Make _build_connection_string read a controlled configuration."""
    settings = Settings(_env_file=None, database_url=database_url)
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


def test_history_list_query_omits_the_report_body() -> None:
    """The list must not bring the report, a payload the table never draws."""
    projection = history_query_module._HISTORY_LIST_SELECT

    for column in ("explanation", "claims", "sources", "user_id", "file_data"):
        assert column not in projection
    # Pasted text arrives trimmed while search still looks at the full column.
    assert (
        f"LEFT(input_text, {history_query_module.HISTORY_LIST_TEXT_CHARS})"
        in projection
    )


def test_history_export_query_omits_the_report_but_keeps_the_full_text() -> None:
    """The CSV does not need the report either, but does need the full text and the end date."""
    projection = history_query_module._HISTORY_EXPORT_SELECT

    for column in ("explanation", "claims", "sources", "user_id", "file_data"):
        assert column not in projection
    # No LEFT(), since unlike the list the Export does not trim the text.
    assert "LEFT(" not in projection
    assert "input_text" in projection
    # completed_at feeds the CSV's «Duración (s)» column.
    assert "completed_at" in projection


def test_extract_kpis_values_handles_none_and_row_values() -> None:
    assert dashboard_module._extract_kpis_values(None) == (0, None, 0, 0, 0, 0, 0.0, 0)
    assert dashboard_module._extract_kpis_values((10, 0.83, 7, 4, 2, 3, 0.62, 1)) == (
        10,
        0.83,
        7,
        4,
        2,
        3,
        0.62,
        1,
    )


def test_extract_kpis_values_has_no_credibility_when_every_analysis_is_uncertain() -> (
    None
):
    assert (
        dashboard_module._extract_kpis_values((4, None, 0, 1, 0, 0, 0.5, 0))[1] is None
    )


def test_credibility_percentage_keeps_a_missing_credibility_missing() -> None:
    assert dashboard_module._credibility_percentage(None) is None
    assert dashboard_module._credibility_percentage(0.1234) == 12.3
    assert dashboard_module._credibility_percentage(0.0) == 0.0


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
    assert points[0].average_credibility == 50.0
    assert points[1].date == "2026-04-02"
    assert points[1].total == 0
    assert points[1].average_credibility is None
    assert points[2].average_credibility == 75.0


def test_build_trend_points_has_no_credibility_on_an_all_uncertain_day() -> None:
    points = dashboard_module._build_trend_points(
        trend_rows=[(date(2026, 4, 1), 3, None)],
        trend_start_date=date(2026, 4, 1),
        trend_days=1,
    )

    assert points[0].total == 3
    assert points[0].average_credibility is None


def test_build_source_breakdown_maps_rows_to_dataclasses() -> None:
    rows = [("url", 3, 0.91), ("text", 1, None)]

    result = dashboard_module._build_source_breakdown(rows)

    assert len(result) == 2
    assert isinstance(result[0], DashboardSourceBreakdownItem)
    assert result[0].source_type == "url"
    assert result[0].total == 3
    assert result[0].average_credibility == 91.0
    assert result[1].average_credibility is None


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
    assert result[0].average_credibility == 80.0


def test_build_domain_breakdown_excludes_uncertain_from_credibility() -> None:
    # The uncertain row (NULL Credibility) counts towards frequency but not the mean.
    domain_rows = [
        ("https://a.com/one", 0.8),
        ("https://a.com/two", None),
    ]

    result = dashboard_module._build_domain_breakdown(domain_rows=domain_rows, limit=5)

    assert len(result) == 1
    assert result[0].total == 2
    assert result[0].average_credibility == 80.0


def test_build_domain_breakdown_has_no_credibility_when_every_analysis_is_uncertain() -> (
    None
):
    domain_rows = [
        ("https://a.com/one", None),
        ("https://a.com/two", None),
    ]

    result = dashboard_module._build_domain_breakdown(domain_rows=domain_rows, limit=5)

    assert result[0].total == 2
    assert result[0].average_credibility is None


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
    assert (alerts[0].verdict, alerts[0].credibility) == ("fake", 79)


def test_a_partly_false_alert_has_its_verdict_and_no_credibility() -> None:
    created = datetime(2026, 4, 10, 15, 0, tzinfo=timezone.utc)
    row = (7, "text", "Texto", None, "parcialmente falsa", 0.8, created)

    (alert,) = dashboard_module._build_alerts([row])

    assert (alert.verdict, alert.credibility) == ("mixed", None)
