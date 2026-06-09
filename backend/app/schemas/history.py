"""
Este módulo define los esquemas de datos relacionados con el historial de análisis del usuario.
"""

from typing import Any, List, Optional

from pydantic import BaseModel, computed_field, model_validator

from app.core.credibility import Verdict, classify_verdict, compute_credibility


class ClaimItem(BaseModel):
    """Veredicto de una afirmación concreta dentro de un análisis."""

    text: str
    label: str
    confidence: float

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verdict(self) -> Verdict:
        """Bucket del veredicto (`real`/`fake`/`uncertain`) derivado de la etiqueta."""
        return classify_verdict(self.label)


class SourceItem(BaseModel):
    """Fuente de literatura biomédica recuperada para fundamentar el análisis."""

    title: str
    url: str
    source: Optional[str] = None
    year: Optional[str] = None
    statements: Optional[List[str]] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_statement(cls, data: Any) -> Any:
        """Rellena ``statements`` desde el campo ``statement`` (singular) heredado."""
        if isinstance(data, dict) and not data.get("statements"):
            legacy = data.get("statement")
            if isinstance(legacy, str) and legacy.strip():
                return {**data, "statements": [legacy]}
        return data


class AnalysisHistoryItem(BaseModel):
    """Modelo de datos para un ítem del historial de análisis."""

    analysis_id: str
    user_id: str
    source_type: str
    input_text: Optional[str] = None
    input_url: Optional[str] = None
    label: Optional[str] = None
    confidence: Optional[float] = None
    explanation: Optional[str] = None
    status: str = "done"
    error_code: Optional[str] = None
    created_at: str
    pdf_filename: Optional[str] = None
    claims: Optional[List[ClaimItem]] = None
    sources: Optional[List[SourceItem]] = None
    share_token: Optional[str] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verdict(self) -> Verdict:
        """Bucket del veredicto (`real`/`fake`/`uncertain`) derivado de la etiqueta."""
        return classify_verdict(self.label)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def credibility(self) -> Optional[int]:
        """Credibilidad [0, 100] derivada del veredicto y la confianza."""
        return compute_credibility(self.label, self.confidence)


class PublicAnalysisReport(BaseModel):
    """Vista pública de solo lectura de un informe compartido; sin datos de identidad."""

    source_type: str
    input_text: Optional[str] = None
    input_url: Optional[str] = None
    label: Optional[str] = None
    confidence: Optional[float] = None
    explanation: Optional[str] = None
    status: str = "done"
    created_at: str
    pdf_filename: Optional[str] = None
    claims: Optional[List[ClaimItem]] = None
    sources: Optional[List[SourceItem]] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verdict(self) -> Verdict:
        """Bucket del veredicto (`real`/`fake`/`uncertain`) derivado de la etiqueta."""
        return classify_verdict(self.label)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def credibility(self) -> Optional[int]:
        """Credibilidad [0, 100] derivada del veredicto y la confianza."""
        return compute_credibility(self.label, self.confidence)


class HistoryResponse(BaseModel):
    """Modelo de datos para la respuesta del endpoint de historial de análisis."""

    status: str
    items: List[AnalysisHistoryItem]
    count: int
    page: int
    page_size: int
