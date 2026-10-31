"""Data schemas for analyses."""

from enum import Enum
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, HttpUrl, StringConstraints, model_validator

MAX_INPUT_TEXT_LENGTH = 10_000
# Useful floor, since below it no verifiable medical claim fits and the pipeline runs for nothing.
MIN_INPUT_TEXT_LENGTH = 10


class SourceType(str, Enum):
    """Tipos de fuentes de entrada para el análisis."""

    TEXT = "text"
    FILE = "file"
    URL = "url"


# Analysis lifecycle, matching the status CHECK in db/migrations.
AnalysisStatus = Literal["pending", "done", "failed"]

# Stage the worker reports, input preparation first and then each graph node.
AnalysisStage = Literal[
    "preparing", "extractor", "translator", "investigator", "health_expert"
]

# Origin of the Analysis, matching the origin CHECK in db/migrations.
AnalysisOrigin = Literal["web", "mcp"]


class AnalysisRequest(BaseModel):
    """Modelo de datos para la solicitud de análisis."""

    text: Optional[
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True,
                min_length=MIN_INPUT_TEXT_LENGTH,
                max_length=MAX_INPUT_TEXT_LENGTH,
            ),
        ]
    ] = None
    url: Optional[HttpUrl] = None
    source_type: SourceType = SourceType.TEXT

    @model_validator(mode="after")
    def validate_payload_coherence(self) -> "AnalysisRequest":
        """Validate that the payload is consistent."""
        has_text = self.text is not None
        has_url = self.url is not None

        if self.source_type == SourceType.FILE:
            raise ValueError(
                "Los archivos se envían al endpoint de subida, no como JSON."
            )

        if has_text == has_url:
            raise ValueError("Debes enviar exactamente uno: 'text' o 'url'.")

        if has_url and self.source_type != SourceType.URL:
            raise ValueError("Si envías 'url', source_type debe ser 'url'.")

        if has_text and self.source_type == SourceType.URL:
            raise ValueError("Si envías 'text', source_type no puede ser 'url'.")

        return self


class AnalysisResponse(BaseModel):
    """Modelo de datos para la respuesta del análisis."""

    status: str
    analysis_id: Optional[str] = None
    message: Optional[str] = None
    label: Optional[str] = None
    confidence: Optional[float] = None
    explanation: Optional[str] = None


class ShareResponse(BaseModel):
    """Respuesta al crear o consultar el enlace público de un análisis."""

    status: str
    share_token: str


class AnalysisStatusResponse(BaseModel):
    """Estado ligero de un análisis para el sondeo mientras sigue en curso."""

    status: AnalysisStatus
    stage: Optional[AnalysisStage] = None
