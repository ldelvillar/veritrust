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
from app.schemas.history import AnalysisHistoryItem, HistoryListItem


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


def test_coerce_optional_fraction_passes_none_and_validates_range() -> None:
    assert history_module._coerce_optional_fraction(None) is None
    assert history_module._coerce_optional_fraction(0.0) == 0.0
    assert history_module._coerce_optional_fraction(1.0) == 1.0
    with pytest.raises(DatabaseError):
        history_module._coerce_optional_fraction(1.5)
    with pytest.raises(DatabaseError):
        history_module._coerce_optional_fraction("no-num")


def test_map_history_record_converts_sql_row_to_dataclass() -> None:
    row = {
        "id": 123,
        "user_id": "user-1",
        "source_type": "text",
        "input_text": "contenido",
        "input_url": None,
        "label": "falsa",
        "confidence": 0.81,
        "evidence_coverage": 0.5,
        "explanation": "explicacion",
        "created_at": datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
        "completed_at": datetime(2026, 4, 10, 12, 3, tzinfo=timezone.utc),
        "status": "done",
        "error_code": None,
        "claims": [{"text": "Afirmación", "label": "falsa", "confidence": 0.81}],
        "sources": [
            {"title": "Estudio", "url": "https://doi.org/10.1/x", "source": "BMJ"}
        ],
        "file_filename": None,
        "share_token": "tok_xyz",
    }

    record = history_module._map_history_record(row)

    assert isinstance(record, AnalysisHistoryItem)
    assert record.analysis_id == "123"
    assert record.user_id == "user-1"
    assert record.confidence == 0.81
    assert record.evidence_coverage == 0.5
    assert record.status == "done"
    assert record.error_code is None
    assert record.created_at.startswith("2026-04-10")
    assert record.completed_at is not None
    assert record.completed_at.startswith("2026-04-10 12:03")
    assert record.claims is not None
    assert record.claims[0].label == "falsa"
    assert record.sources is not None
    assert record.sources[0].source == "BMJ"
    assert record.share_token == "tok_xyz"


def test_map_history_record_handles_pending_row_with_null_results() -> None:
    row = {
        "id": 123,
        "user_id": "user-1",
        "source_type": "text",
        "input_text": "contenido",
        "input_url": None,
        "label": None,
        "confidence": None,
        "evidence_coverage": None,
        "explanation": None,
        "created_at": datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
        "completed_at": None,
        "status": "pending",
        "error_code": None,
        "claims": None,
        "sources": None,
        "file_filename": None,
        "share_token": None,
    }

    record = history_module._map_history_record(row)

    assert record.status == "pending"
    assert record.label is None
    assert record.confidence is None
    assert record.evidence_coverage is None
    assert record.explanation is None
    assert record.claims is None
    assert record.sources is None
    # Una fila pendiente aún no ha terminado: sin instante de finalización.
    assert record.completed_at is None
    # El listado no selecciona stage: sin esa clave, el mapeo lo deja en None.
    assert record.stage is None


def test_map_history_record_reads_stage_when_present() -> None:
    row = {
        "id": 123,
        "user_id": "user-1",
        "source_type": "url",
        "input_text": None,
        "input_url": "https://ejemplo.com/x",
        "label": None,
        "confidence": None,
        "evidence_coverage": None,
        "explanation": None,
        "created_at": datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
        "completed_at": None,
        "status": "pending",
        "error_code": None,
        "claims": None,
        "sources": None,
        "file_filename": None,
        "share_token": None,
        "stage": "investigator",
    }

    record = history_module._map_history_record(row)

    assert record.status == "pending"
    assert record.evidence_coverage is None
    assert record.stage == "investigator"


def test_map_history_record_reads_only_columns_the_queries_select() -> None:
    """Si el mapeo lee una columna que las consultas no traen, esto revienta."""
    row = {column: None for column in history_module._HISTORY_COLUMNS}
    row["id"] = 123
    row["user_id"] = "user-1"
    row["source_type"] = "text"
    row["created_at"] = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
    row["status"] = "pending"

    record = history_module._map_history_record(row)

    assert record.analysis_id == "123"
    # stage es la unica columna extra: solo la consulta por id la selecciona.
    assert record.stage is None


def test_map_history_list_record_keeps_the_fields_the_table_paints() -> None:
    row = {
        "id": 123,
        "source_type": "text",
        "input_text": "contenido",
        "input_url": None,
        "label": "falsa",
        "confidence": 0.81,
        "evidence_coverage": 0.5,
        "created_at": datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
        "status": "pending",
        "stage": "investigator",
        "error_code": None,
        "file_filename": None,
        "share_token": "tok_xyz",
    }

    record = history_module._map_history_list_record(row)

    assert isinstance(record, HistoryListItem)
    assert record.analysis_id == "123"
    assert record.created_at.startswith("2026-04-10")
    assert record.evidence_coverage == 0.5
    # El listado sí reporta la etapa: la fila 'en curso' muestra por dónde va el pipeline.
    assert record.stage == "investigator"
    assert record.share_token == "tok_xyz"
    # Credibilidad y veredicto se derivan de label/confidence, no viajan como columnas.
    assert record.verdict == "fake"
    assert record.credibility == 19


def test_map_history_list_record_reads_only_columns_the_list_query_selects() -> None:
    """Si el mapeo del listado lee una columna que la consulta no trae, esto revienta."""
    row: dict[str, object] = {
        column: None for column in history_module._HISTORY_LIST_COLUMNS
    }
    # La consulta aliasa LEFT(input_text, N) como input_text; el resto son columnas.
    row["input_text"] = None
    row["id"] = 123
    row["source_type"] = "text"
    row["created_at"] = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
    row["status"] = "pending"

    record = history_module._map_history_list_record(row)

    assert record.analysis_id == "123"


def test_history_list_query_omits_the_report_body() -> None:
    """El listado no debe traer el informe: es carga que la tabla nunca pinta."""
    projection = history_module._HISTORY_LIST_SELECT

    for column in ("explanation", "claims", "sources", "user_id", "file_data"):
        assert column not in projection
    # El texto pegado llega recortado; buscar sigue mirando la columna completa.
    assert f"LEFT(input_text, {history_module.HISTORY_LIST_TEXT_CHARS})" in projection

    _, list_query = history_module._build_history_queries(
        "user_id = %s", "created_at DESC"
    )
    assert projection in list_query


def test_history_export_query_omits_the_report_but_keeps_the_full_text() -> None:
    """El CSV tampoco necesita el informe, pero sí el texto íntegro y la fecha de fin."""
    projection = history_module._HISTORY_EXPORT_SELECT

    for column in ("explanation", "claims", "sources", "user_id", "file_data"):
        assert column not in projection
    # Sin LEFT(): a diferencia del listado, la exportación no recorta el texto.
    assert "LEFT(" not in projection
    assert "input_text" in projection
    # completed_at alimenta la columna «Duración (s)» del CSV.
    assert "completed_at" in projection


def test_sanitize_history_query_params_clamps_and_normalizes_values() -> None:
    safe_limit, safe_offset, safe_source_type, safe_order_by = (
        history_module._sanitize_history_query_params(
            limit=500,
            offset=-10,
            source_type="audio",
            sort="zzz",
        )
    )

    assert safe_limit == 100
    assert safe_offset == 0
    assert safe_source_type is None
    # Un sort desconocido cae al orden por defecto (más recientes primero).
    assert safe_order_by == "created_at DESC"


def test_sanitize_history_query_params_preserves_valid_values() -> None:
    safe_limit, safe_offset, safe_source_type, safe_order_by = (
        history_module._sanitize_history_query_params(
            limit=25,
            offset=5,
            source_type="url",
            sort="oldest",
        )
    )

    assert safe_limit == 25
    assert safe_offset == 5
    assert safe_source_type == "url"
    assert safe_order_by == "created_at ASC"


def test_sanitize_history_query_params_credibility_sort_uses_computed_expression() -> (
    None
):
    _, _, _, order_high = history_module._sanitize_history_query_params(
        limit=10, offset=0, source_type=None, sort="credibility_high"
    )
    _, _, _, order_low = history_module._sanitize_history_query_params(
        limit=10, offset=0, source_type=None, sort="credibility_low"
    )

    # La credibilidad se computa en SQL desde verdict/confidence; incierto va al final.
    assert "verdict = 'fake'" in order_high
    assert order_high.endswith("DESC NULLS LAST, created_at DESC")
    assert order_low.endswith("ASC NULLS LAST, created_at DESC")


def test_build_history_where_clause_with_only_user_id() -> None:
    where_sql, params = history_module._build_history_where_clause(
        user_id="user-1",
        search_query=None,
        source_type=None,
        created_after=None,
    )

    # Sin filtro de estado se listan todas las filas (en curso, completadas o fallidas).
    assert where_sql == "user_id = %s"
    assert params == ["user-1"]


def test_build_history_where_clause_filters_by_status() -> None:
    where_sql, params = history_module._build_history_where_clause(
        user_id="user-1",
        search_query=None,
        source_type=None,
        created_after=None,
        status="failed",
    )

    assert where_sql == "user_id = %s AND status = %s"
    assert params == ["user-1", "failed"]


def test_build_history_where_clause_ignores_unknown_status() -> None:
    where_sql, params = history_module._build_history_where_clause(
        user_id="user-1",
        search_query=None,
        source_type=None,
        created_after=None,
        status="bogus",
    )

    assert where_sql == "user_id = %s"
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
    assert "COALESCE(file_filename, '') ILIKE %s" in where_sql
    assert "source_type = %s" in where_sql
    assert "created_at >= %s" in where_sql
    assert params == [
        "user-2",
        "%covid%",
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

    # Igualdad parametrizada sobre la columna verdict.
    assert where_sql == "user_id = %s AND verdict = %s"
    assert params == ["user-1", "fake"]


def test_build_history_where_clause_filters_by_uncertain_verdict() -> None:
    where_sql, params = history_module._build_history_where_clause(
        user_id="user-1",
        search_query=None,
        source_type=None,
        created_after=None,
        verdict="uncertain",
    )

    # Las filas pending/failed tienen verdict NULL, así que la igualdad las excluye.
    assert where_sql == "user_id = %s AND verdict = %s"
    assert params == ["user-1", "uncertain"]


def test_build_history_where_clause_ignores_unknown_verdict() -> None:
    where_sql, params = history_module._build_history_where_clause(
        user_id="user-1",
        search_query=None,
        source_type=None,
        created_after=None,
        verdict="bogus",
    )

    assert where_sql == "user_id = %s"
    assert params == ["user-1"]


def test_build_history_queries_includes_ordering_and_where() -> None:
    count_query, list_query = history_module._build_history_queries(
        "user_id = %s",
        "created_at ASC",
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
    assert dashboard_module._extract_kpis_values(None) == (0, 0.0, 0, 0, 0, 0, 0.0)
    assert dashboard_module._extract_kpis_values((10, 0.83, 7, 4, 2, 3, 0.62)) == (
        10,
        0.83,
        7,
        4,
        2,
        3,
        0.62,
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


def test_build_domain_breakdown_excludes_uncertain_from_credibility() -> None:
    # La fila incierta (credibilidad NULL) cuenta como frecuencia pero no en la media.
    domain_rows = [
        ("https://a.com/one", 0.8),
        ("https://a.com/two", None),
    ]

    result = dashboard_module._build_domain_breakdown(domain_rows=domain_rows, limit=5)

    assert len(result) == 1
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
