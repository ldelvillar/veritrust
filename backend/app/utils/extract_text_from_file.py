"""Despacha la extracción de texto de un archivo subido según su tipo (pdf/txt/md)."""

from pathlib import Path

from app.utils.extract_text_from_pdf import PDFExtractionError, extract_text_from_pdf

# Extensiones de texto plano que se decodifican directamente, sin parsear.
_PLAIN_TEXT_SUFFIXES = {".txt", ".md"}
_PDF_SUFFIX = ".pdf"

# Tipos de archivo aceptados en la subida.
ALLOWED_FILE_SUFFIXES = _PLAIN_TEXT_SUFFIXES | {_PDF_SUFFIX}


class FileExtractionError(Exception):
    """Excepción lanzada cuando no se puede extraer texto del archivo subido."""


def _extract_plain_text(data: bytes, max_chars: int) -> str:
    """Decodifica un archivo de texto plano (UTF-8) y lo acota a ``max_chars``."""
    text = data.decode("utf-8", errors="replace")
    text = "\n".join(line for line in text.splitlines() if line.strip())
    if not text.strip():
        raise FileExtractionError("El archivo de texto está vacío.")
    return text[:max_chars]


def extract_text_from_file(data: bytes, filename: str, max_chars: int) -> str:
    """Extrae el texto de un archivo subido según su extensión, acotado a ``max_chars``."""
    suffix = Path(filename).suffix.lower()

    if suffix == _PDF_SUFFIX:
        try:
            return extract_text_from_pdf(data, max_chars)
        except PDFExtractionError as exc:
            raise FileExtractionError(str(exc)) from exc

    if suffix in _PLAIN_TEXT_SUFFIXES:
        return _extract_plain_text(data, max_chars)

    raise FileExtractionError(f"Tipo de archivo no soportado: {suffix or filename}")
