"""Tests unitarios del despachador de extracción de texto por tipo de archivo."""

import pytest

import app.utils.extract_text_from_file as module
from app.schemas.analysis import MAX_INPUT_TEXT_LENGTH
from app.utils.extract_text_from_file import (
    FileExtractionError,
    extract_text_from_file,
)
from app.utils.extract_text_from_pdf import PDFExtractionError


def test_extracts_plain_text_from_txt() -> None:
    text = extract_text_from_file(
        b"Linea uno\nLinea dos\n", "nota.txt", MAX_INPUT_TEXT_LENGTH
    )

    assert text == "Linea uno\nLinea dos"


def test_extracts_plain_text_from_md() -> None:
    text = extract_text_from_file(
        b"# Titulo\n\nContenido", "lectura.md", MAX_INPUT_TEXT_LENGTH
    )

    assert "# Titulo" in text
    assert "Contenido" in text


def test_caps_plain_text_to_the_given_limit() -> None:
    text = extract_text_from_file(b"a" * 3500, "grande.txt", 3000)

    assert len(text) == 3000


def test_empty_plain_text_raises() -> None:
    with pytest.raises(FileExtractionError):
        extract_text_from_file(b"   \n\n  ", "vacio.txt", MAX_INPUT_TEXT_LENGTH)


def test_unsupported_suffix_raises() -> None:
    with pytest.raises(FileExtractionError):
        extract_text_from_file(b"contenido", "documento.docx", MAX_INPUT_TEXT_LENGTH)


def test_dispatches_pdf_to_pdf_extractor_with_the_limit(monkeypatch) -> None:
    monkeypatch.setattr(
        module, "extract_text_from_pdf", lambda data, max_chars: f"pdf a {max_chars}"
    )

    assert extract_text_from_file(b"%PDF-1.4", "informe.pdf", 3000) == "pdf a 3000"


def test_wraps_pdf_extraction_error(monkeypatch) -> None:
    def boom(data: bytes, max_chars: int) -> str:
        raise PDFExtractionError("sin texto seleccionable")

    monkeypatch.setattr(module, "extract_text_from_pdf", boom)

    with pytest.raises(FileExtractionError):
        extract_text_from_file(b"%PDF-1.4", "informe.pdf", MAX_INPUT_TEXT_LENGTH)
