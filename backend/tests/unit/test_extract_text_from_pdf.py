import io

import pytest
from pypdf import PdfReader, PdfWriter

from app.schemas.analysis import MAX_INPUT_TEXT_LENGTH
from app.utils.extract_text_from_pdf import PDFExtractionError, extract_text_from_pdf


def _make_pdf(text: str) -> bytes:
    """Construye un PDF mínimo de una página con ``text`` en un operador Tj."""
    escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    content = f"BT /F1 24 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        b"<< /Length "
        + str(len(content)).encode()
        + b" >>\nstream\n"
        + content
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_pos = len(pdf)
    size = len(objects) + 1
    pdf += f"xref\n0 {size}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += b"trailer\n"
    pdf += f"<< /Size {size} /Root 1 0 R >>\n".encode()
    pdf += b"startxref\n"
    pdf += f"{xref_pos}\n".encode()
    pdf += b"%%EOF"
    return bytes(pdf)


def test_extracts_text_from_valid_pdf():
    result = extract_text_from_pdf(_make_pdf("Hello World"))

    assert "Hello World" in result


def test_truncates_to_max_input_length():
    long_text = "A" * (MAX_INPUT_TEXT_LENGTH + 2000)

    result = extract_text_from_pdf(_make_pdf(long_text))

    assert len(result) <= MAX_INPUT_TEXT_LENGTH
    assert result.startswith("AAAA")


def test_raises_on_pdf_without_extractable_text():
    with pytest.raises(PDFExtractionError, match="No se pudo extraer texto"):
        extract_text_from_pdf(_make_pdf(""))


def test_raises_on_corrupt_input():
    with pytest.raises(PDFExtractionError, match="No se pudo leer el PDF"):
        extract_text_from_pdf(b"this is not a pdf")


def test_raises_on_password_protected_pdf():
    reader = PdfReader(io.BytesIO(_make_pdf("Secret")))
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    writer.encrypt("a-user-password")
    buffer = io.BytesIO()
    writer.write(buffer)

    with pytest.raises(PDFExtractionError, match="protegido con contraseña"):
        extract_text_from_pdf(buffer.getvalue())
