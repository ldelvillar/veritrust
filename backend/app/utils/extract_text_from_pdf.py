"""Extract the text of a PDF."""

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.schemas.analysis import MAX_INPUT_TEXT_LENGTH


class PDFExtractionError(Exception):
    """Raised when extracting the text of the PDF fails."""


def extract_text_from_pdf(data: bytes) -> str:
    """Extract the text of a PDF given as bytes, capped to ``MAX_INPUT_TEXT_LENGTH``."""
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise PDFExtractionError(
                "El PDF está protegido con contraseña y no se puede leer."
            )

        pages_text = [page.extract_text() or "" for page in reader.pages]
    except PDFExtractionError:
        raise
    except (PdfReadError, ValueError, OSError) as e:
        raise PDFExtractionError(f"No se pudo leer el PDF: {e}") from e

    text = "\n".join(line.strip() for line in "\n".join(pages_text).splitlines())
    text = "\n".join(line for line in text.splitlines() if line)

    if not text:
        raise PDFExtractionError(
            "No se pudo extraer texto del PDF proporcionado. "
            "Puede ser un documento escaneado sin texto seleccionable."
        )

    return text[:MAX_INPUT_TEXT_LENGTH]
