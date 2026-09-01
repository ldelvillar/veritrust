"""
Este módulo define los esquemas de datos relacionados con el historial de análisis del usuario.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, computed_field

from app.core.credibility import Verdict, classify_verdict, compute_credibility
from app.schemas.feedback import AnalysisFeedback

Stance = Literal["supports", "contradicts", "inconclusive"]


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


class StatementStance(BaseModel):
    """Afirmación enlazada a una fuente y la postura de la fuente sobre ella."""

    claim_index: int
    text: str
    stance: Optional[Stance] = None


class SourceItem(BaseModel):
    """Fuente de literatura biomédica recuperada para fundamentar el análisis."""

    title: str
    url: str
    source: Optional[str] = None
    year: Optional[str] = None
    statements: Optional[List[StatementStance]] = None


class AnalysisHistoryItem(BaseModel):
    """Modelo de datos para un ítem del historial de análisis."""

    analysis_id: str
    user_id: str
    source_type: str
    input_text: Optional[str] = None
    input_url: Optional[str] = None
    label: Optional[str] = None
    confidence: Optional[float] = None
    evidence_coverage: Optional[float] = None
    explanation: Optional[str] = None
    status: str = "done"
    error_code: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    file_filename: Optional[str] = None
    claims: Optional[List[ClaimItem]] = None
    sources: Optional[List[SourceItem]] = None
    share_token: Optional[str] = None
    stage: Optional[str] = None
    feedback: Optional[AnalysisFeedback] = None

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
    evidence_coverage: Optional[float] = None
    explanation: Optional[str] = None
    status: str = "done"
    created_at: str
    completed_at: Optional[str] = None
    file_filename: Optional[str] = None
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


class PendingAnalysesSummary(BaseModel):
    """Análisis en curso del usuario, para el indicador global del menú."""

    count: int
    newest_analysis_id: Optional[str] = None


class HistoryVerdictCounts(BaseModel):
    """Conteos globales por veredicto del historial filtrado, para las tarjetas."""

    total: int
    real: int
    fake: int
    uncertain: int


class HistorySourceTypeCounts(BaseModel):
    """Conteos globales por tipo de fuente del historial filtrado, para los chips."""

    total: int
    text: int
    url: int
    file: int


class HistoryResponse(BaseModel):
    """Modelo de datos para la respuesta del endpoint de historial de análisis."""

    status: str
    items: List[AnalysisHistoryItem]
    count: int
    page: int
    page_size: int
    verdict_counts: HistoryVerdictCounts
    source_type_counts: HistorySourceTypeCounts


class DeleteAllResponse(BaseModel):
    """Respuesta al eliminar todo el historial de análisis del usuario."""

    status: str
    deleted_count: int
