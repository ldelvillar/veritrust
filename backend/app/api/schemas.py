"""Este módulo define los esquemas de datos para las solicitudes de la API."""

from enum import Enum
from typing import Annotated, Optional
from pydantic import BaseModel, HttpUrl, StringConstraints, model_validator


class SourceType(str, Enum):
    """Tipos de fuentes de entrada para el análisis."""

    TEXT = "text"
    FILE = "file"
    URL = "url"


class AnalyzeRequest(BaseModel):
    """Modelo de datos para la solicitud de análisis."""

    text: Optional[
        Annotated[
            str,
            StringConstraints(strip_whitespace=True, min_length=1, max_length=10000),
        ]
    ] = None
    url: Optional[HttpUrl] = None
    source_type: SourceType = SourceType.TEXT

    @model_validator(mode="after")
    def validate_payload_coherence(self) -> "AnalyzeRequest":
        """Valida que el payload sea coherente."""
        has_text = self.text is not None
        has_url = self.url is not None

        if has_text == has_url:
            raise ValueError("Debes enviar exactamente uno: 'text' o 'url'.")

        if has_url and self.source_type != SourceType.URL:
            raise ValueError("Si envías 'url', source_type debe ser 'url'.")

        if has_text and self.source_type == SourceType.URL:
            raise ValueError("Si envías 'text', source_type no puede ser 'url'.")

        return self
