"""Dispatch text extraction of an uploaded file by its type (pdf/txt/md)."""

from pathlib import Path

from app.schemas.analysis import MAX_INPUT_TEXT_LENGTH
from app.utils.extract_text_from_pdf import PDFExtractionError, extract_text_from_pdf

# Plain text extensions decoded directly, without parsing.
_PLAIN_TEXT_SUFFIXES = {".txt", ".md"}
_PDF_SUFFIX = ".pdf"

ALLOWED_FILE_SUFFIXES = _PLAIN_TEXT_SUFFIXES | {_PDF_SUFFIX}


class FileExtractionError(Exception):
    """Raised when no text can be extracted from the uploaded file."""


def _extract_plain_text(data: bytes) -> str:
    """Decode a plain text (UTF-8) file and cap it to the budget."""
    text = data.decode("utf-8", errors="replace")
    text = "\n".join(line for line in text.splitlines() if line.strip())
    if not text.strip():
        raise FileExtractionError("El archivo de texto está vacío.")
    return text[:MAX_INPUT_TEXT_LENGTH]


def extract_text_from_file(data: bytes, filename: str) -> str:
    """Extract the text of an uploaded file by its extension."""
    suffix = Path(filename).suffix.lower()

    if suffix == _PDF_SUFFIX:
        try:
            return extract_text_from_pdf(data)
        except PDFExtractionError as exc:
            raise FileExtractionError(str(exc)) from exc

    if suffix in _PLAIN_TEXT_SUFFIXES:
        return _extract_plain_text(data)

    raise FileExtractionError(f"Tipo de archivo no soportado: {suffix or filename}")
