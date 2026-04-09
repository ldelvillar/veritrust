"""Este módulo define los esquemas de datos para las solicitudes de la API."""

from typing import Annotated, Optional
from pydantic import BaseModel, HttpUrl, StringConstraints, model_validator


class AnalyzeRequest(BaseModel):
    """Modelo de datos para la solicitud de análisis."""

    text: Optional[
        Annotated[
            str,
            StringConstraints(strip_whitespace=True, min_length=1, max_length=10000),
        ]
    ] = None
    url: Optional[HttpUrl] = None

    @model_validator(mode="after")
    def check_text_or_url(self) -> "AnalyzeRequest":
        """Valida que se proporcione solo uno de los campos: 'text' o 'url'."""
        if (self.text and self.url) or (not self.text and not self.url):
            raise ValueError(
                "Se debe proporcionar solo uno de los campos:"
                "'text' o 'url', pero no ambos ni ninguno."
            )
        return self
