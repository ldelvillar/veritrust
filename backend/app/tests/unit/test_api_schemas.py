"""Tests unitarios para los esquemas de la API."""

import pytest
from pydantic import ValidationError

from app.api.schemas import AnalyzeRequest, SourceType


def test_analyze_request_accepts_text_with_default_source_type() -> None:
    request = AnalyzeRequest(text="Texto clínico")

    assert request.text == "Texto clínico"
    assert request.url is None
    assert request.source_type == SourceType.TEXT


def test_analyze_request_accepts_text_with_file_source_type() -> None:
    request = AnalyzeRequest(text="Texto extraído", source_type="file")

    assert request.text == "Texto extraído"
    assert request.url is None
    assert request.source_type == SourceType.FILE


def test_analyze_request_accepts_url_with_url_source_type() -> None:
    request = AnalyzeRequest(
        url="https://ejemplo.com/noticia",
        source_type="url",
    )

    assert request.text is None
    assert str(request.url) == "https://ejemplo.com/noticia"
    assert request.source_type == SourceType.URL


def test_analyze_request_rejects_payload_without_text_or_url() -> None:
    with pytest.raises(ValidationError) as exc:
        AnalyzeRequest(source_type="text")

    assert "Debes enviar exactamente uno" in str(exc.value)


def test_analyze_request_rejects_payload_with_text_and_url() -> None:
    with pytest.raises(ValidationError) as exc:
        AnalyzeRequest(
            text="Texto",
            url="https://ejemplo.com/noticia",
            source_type="url",
        )

    assert "Debes enviar exactamente uno" in str(exc.value)


def test_analyze_request_rejects_url_with_non_url_source_type() -> None:
    with pytest.raises(ValidationError) as exc:
        AnalyzeRequest(
            url="https://ejemplo.com/noticia",
            source_type="text",
        )

    assert "source_type debe ser 'url'" in str(exc.value)


def test_analyze_request_rejects_text_with_url_source_type() -> None:
    with pytest.raises(ValidationError) as exc:
        AnalyzeRequest(
            text="Texto",
            source_type="url",
        )

    assert "source_type no puede ser 'url'" in str(exc.value)


def test_analyze_request_rejects_invalid_source_type_value() -> None:
    with pytest.raises(ValidationError) as exc:
        AnalyzeRequest(text="Texto", source_type="audio")

    assert "source_type" in str(exc.value)
