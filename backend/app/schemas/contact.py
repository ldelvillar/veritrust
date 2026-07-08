"""Esquemas del formulario de contacto/demo enviado a POST /contact."""

from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, StringConstraints, field_validator

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
_MAX_METADATA_ENTRIES = 10
_MAX_METADATA_VALUE_LENGTH = 500


class ContactType(str, Enum):
    """Formulario del que procede el mensaje."""

    CONTACT = "contact"
    DEMO = "demo"


class ContactRequest(BaseModel):
    """Mensaje de un formulario público de contacto o solicitud de demo."""

    type: ContactType = ContactType.CONTACT
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
    ]
    email: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, max_length=254, pattern=_EMAIL_PATTERN
        ),
    ]
    subject: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    message: Optional[
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
        ]
    ] = None
    metadata: Optional[dict[str, str]] = None

    @field_validator("metadata")
    @classmethod
    def validate_metadata(
        cls, value: Optional[dict[str, str]]
    ) -> Optional[dict[str, str]]:
        """Acota el número de entradas y la longitud de cada valor para evitar abuso."""
        if value is None:
            return None
        if len(value) > _MAX_METADATA_ENTRIES:
            raise ValueError("Demasiados campos adicionales.")
        cleaned = {k: v.strip() for k, v in value.items() if v.strip()}
        if any(len(v) > _MAX_METADATA_VALUE_LENGTH for v in cleaned.values()):
            raise ValueError("Un campo adicional supera la longitud máxima.")
        return cleaned or None


class ContactResponse(BaseModel):
    """Respuesta a un mensaje de contacto entregado correctamente."""

    status: str
