"""Tests unitarios para los esquemas de la API."""

import pytest
from pydantic import ValidationError

from app.schemas.analysis import AnalysisRequest, SourceType
from app.schemas.history import SourceItem


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
            text="Texto",
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
            text="Texto",
            source_type="url",
        )

    assert "source_type no puede ser 'url'" in str(exc.value)


def test_analyze_request_rejects_invalid_source_type_value() -> None:
    with pytest.raises(ValidationError) as exc:
        AnalysisRequest(text="Texto", source_type="audio")

    assert "source_type" in str(exc.value)


def test_analyze_request_rejects_file_source_type() -> None:
    with pytest.raises(ValidationError) as exc:
        AnalysisRequest(text="Texto", source_type="file")

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
