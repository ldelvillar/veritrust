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
    text = extract_text_from_file(b"Linea uno\nLinea dos\n", "nota.txt")

    assert text == "Linea uno\nLinea dos"


def test_extracts_plain_text_from_md() -> None:
    text = extract_text_from_file(b"# Titulo\n\nContenido", "lectura.md")

    assert "# Titulo" in text
    assert "Contenido" in text


def test_caps_plain_text_to_max_length() -> None:
    text = extract_text_from_file(b"a" * (MAX_INPUT_TEXT_LENGTH + 500), "grande.txt")

    assert len(text) == MAX_INPUT_TEXT_LENGTH


def test_empty_plain_text_raises() -> None:
    with pytest.raises(FileExtractionError):
        extract_text_from_file(b"   \n\n  ", "vacio.txt")


def test_unsupported_suffix_raises() -> None:
    with pytest.raises(FileExtractionError):
        extract_text_from_file(b"contenido", "documento.docx")


def test_dispatches_pdf_to_pdf_extractor(monkeypatch) -> None:
    monkeypatch.setattr(module, "extract_text_from_pdf", lambda data: "texto del pdf")

    assert extract_text_from_file(b"%PDF-1.4", "informe.pdf") == "texto del pdf"


def test_wraps_pdf_extraction_error(monkeypatch) -> None:
    def boom(data: bytes) -> str:
        raise PDFExtractionError("sin texto seleccionable")

    monkeypatch.setattr(module, "extract_text_from_pdf", boom)

    with pytest.raises(FileExtractionError):
        extract_text_from_file(b"%PDF-1.4", "informe.pdf")
