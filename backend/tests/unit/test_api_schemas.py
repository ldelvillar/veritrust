"""Tests unitarios para los esquemas de la API."""

from typing import get_args

import pytest
from pydantic import ValidationError

from app.agents.main import PIPELINE_STAGES
from app.schemas.analysis import AnalysisRequest, AnalysisStage, SourceType
from app.schemas.history import HistoryListItem, HistoryQuery, SourceItem


def test_analyze_request_accepts_text_with_default_source_type() -> None:
    request = AnalysisRequest(text="Texto clínico")

    assert request.text == "Texto clínico"
    assert request.url is None
    assert request.source_type == SourceType.TEXT


def test_analyze_request_accepts_url_with_url_source_type() -> None:
    request = AnalysisRequest(
        url="https://ejemplo.com/noticia",
        source_type="url",
    )

    assert request.text is None
    assert str(request.url) == "https://ejemplo.com/noticia"
    assert request.source_type == SourceType.URL


def test_analyze_request_rejects_payload_without_text_or_url() -> None:
    with pytest.raises(ValidationError) as exc:
        AnalysisRequest(source_type="text")

    assert "Debes enviar exactamente uno" in str(exc.value)


def test_analyze_request_rejects_payload_with_text_and_url() -> None:
    with pytest.raises(ValidationError) as exc:
        AnalysisRequest(
            text="Texto clínico",
            url="https://ejemplo.com/noticia",
            source_type="url",
        )

    assert "Debes enviar exactamente uno" in str(exc.value)


def test_analyze_request_rejects_url_with_non_url_source_type() -> None:
    with pytest.raises(ValidationError) as exc:
        AnalysisRequest(
            url="https://ejemplo.com/noticia",
            source_type="text",
        )

    assert "source_type debe ser 'url'" in str(exc.value)


def test_analyze_request_rejects_text_with_url_source_type() -> None:
    with pytest.raises(ValidationError) as exc:
        AnalysisRequest(
            text="Texto clínico",
            source_type="url",
        )

    assert "source_type no puede ser 'url'" in str(exc.value)


def test_analyze_request_rejects_invalid_source_type_value() -> None:
    with pytest.raises(ValidationError) as exc:
        AnalysisRequest(text="Texto clínico", source_type="audio")

    assert "source_type" in str(exc.value)


def test_analyze_request_rejects_file_source_type() -> None:
    with pytest.raises(ValidationError) as exc:
        AnalysisRequest(text="Texto clínico", source_type="file")

    assert "endpoint de subida" in str(exc.value)


def test_source_item_keeps_statement_stance_when_present() -> None:
    source = SourceItem.model_validate(
        {
            "title": "Estudio",
            "url": "https://x/1",
            "statements": [{"claim_index": 0, "text": "a", "stance": "contradicts"}],
        }
    )

    assert source.statements is not None
    assert source.statements[0].claim_index == 0
    assert source.statements[0].text == "a"
    assert source.statements[0].stance == "contradicts"


def test_source_item_rejects_a_statement_without_its_claim_index() -> None:
    """El índice enlaza fuente y afirmación: sin él la fuente no es interpretable."""
    with pytest.raises(ValidationError):
        SourceItem.model_validate(
            {
                "title": "Estudio",
                "url": "https://x/1",
                "statements": [{"text": "a", "stance": "contradicts"}],
            }
        )


def test_analysis_stage_vocabulary_matches_the_worker_stages() -> None:
    """El contrato de etapas es la preparación más los nodos del grafo, ni más ni menos."""
    assert set(get_args(AnalysisStage)) == {"preparing", *PIPELINE_STAGES}


def _history_row(**overrides: object) -> dict[str, object]:
    return {
        "analysis_id": "a1",
        "source_type": "url",
        "created_at": "2026-09-22T10:00:00+00:00",
        "status": "failed",
        "error_code": "URL_EXTRACTION",
        **overrides,
    }


def test_history_item_keeps_closed_set_values_as_plain_strings() -> None:
    item = HistoryListItem.model_validate(_history_row(stage="investigator"))

    assert type(item.source_type) is str and item.source_type == "url"
    assert type(item.error_code) is str and item.error_code == "URL_EXTRACTION"
    assert item.stage == "investigator"


@pytest.mark.parametrize(
    "field, value",
    [
        ("status", "running"),
        ("stage", "verifier"),
        ("source_type", "pdf"),
        ("origin", "cli"),
        ("error_code", "PDF_EXTRACTION"),
    ],
)
def test_history_item_rejects_values_outside_the_contract(
    field: str, value: str
) -> None:
    with pytest.raises(ValidationError):
        HistoryListItem.model_validate(_history_row(**{field: value}))


def test_history_query_trims_the_search_and_treats_blank_as_absent() -> None:
    assert HistoryQuery(search="  gripe aviar ").search == "gripe aviar"
    assert HistoryQuery(search="   ").search is None


def test_history_query_content_types_follow_the_source_type_enum() -> None:
    annotation = HistoryQuery.model_fields["source_type"].annotation

    assert get_args(annotation) == ("all", *(member.value for member in SourceType))
