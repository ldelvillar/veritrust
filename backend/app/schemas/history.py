"""
Este módulo define los esquemas de datos relacionados con el historial de análisis del usuario.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, computed_field

from app.core.verdict import (
    ConfidenceLevel,
    VerdictKind,
    confidence_level_of,
    credibility_of,
    kind_of,
)
from app.schemas.analysis import (
    AnalysisOrigin,
    AnalysisStage,
    AnalysisStatus,
    SourceType,
)
from app.schemas.errors import ErrorCode
from app.schemas.feedback import AnalysisFeedback

Stance = Literal["supports", "contradicts", "inconclusive"]


class ClaimItem(BaseModel):
    """Veredicto de una afirmación concreta dentro de un análisis."""

    text: str
    label: str
    confidence: float

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verdict(self) -> VerdictKind:
        """Bucket del veredicto (`real`/`fake`/`uncertain`) derivado de la etiqueta."""
        return kind_of(self.label)


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


class HistoryListItem(BaseModel):
    """Fila del listado de historial: lo que pinta la tabla, sin el cuerpo del informe."""

    # Los enums validan el contrato pero se guardan como str, igual que antes de tiparlos.
    model_config = ConfigDict(use_enum_values=True)

    analysis_id: str
    source_type: SourceType
    origin: AnalysisOrigin = "web"
    input_text: Optional[str] = None
    input_url: Optional[str] = None
    label: Optional[str] = None
    confidence: Optional[float] = None
    evidence_coverage: Optional[float] = None
    status: AnalysisStatus = "done"
    error_code: Optional[ErrorCode] = None
    created_at: str
    file_filename: Optional[str] = None
    share_token: Optional[str] = None
    stage: Optional[AnalysisStage] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verdict(self) -> VerdictKind:
        """Bucket del veredicto (`real`/`fake`/`uncertain`) derivado de la etiqueta."""
        return kind_of(self.label)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def credibility(self) -> Optional[int]:
        """Credibilidad [0, 100] derivada del veredicto y la confianza."""
        return credibility_of(self.verdict, self.confidence)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def confidence_level(self) -> Optional[ConfidenceLevel]:
        """Tramo de la confianza del veredicto (`high`/`medium`/`low`) para su etiqueta."""
        return confidence_level_of(self.confidence)


class HistoryExportItem(HistoryListItem):
    """Fila del CSV: como el listado pero con ``input_text`` íntegro y el instante de fin."""

    completed_at: Optional[str] = None


class AnalysisHistoryItem(HistoryListItem):
    """Modelo de datos para un ítem del historial de análisis, con el informe completo."""

    user_id: str
    explanation: Optional[str] = None
    completed_at: Optional[str] = None
    claims: Optional[List[ClaimItem]] = None
    sources: Optional[List[SourceItem]] = None
    feedback: Optional[AnalysisFeedback] = None


class PublicAnalysisReport(BaseModel):
    """Vista pública de solo lectura de un informe compartido; sin datos de identidad."""

    # Los enums validan el contrato pero se guardan como str, igual que antes de tiparlos.
    model_config = ConfigDict(use_enum_values=True)

    source_type: SourceType
    input_text: Optional[str] = None
    input_url: Optional[str] = None
    label: Optional[str] = None
    confidence: Optional[float] = None
    evidence_coverage: Optional[float] = None
    explanation: Optional[str] = None
    status: AnalysisStatus = "done"
    created_at: str
    completed_at: Optional[str] = None
    file_filename: Optional[str] = None
    claims: Optional[List[ClaimItem]] = None
    sources: Optional[List[SourceItem]] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verdict(self) -> VerdictKind:
        """Bucket del veredicto (`real`/`fake`/`uncertain`) derivado de la etiqueta."""
        return kind_of(self.label)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def credibility(self) -> Optional[int]:
        """Credibilidad [0, 100] derivada del veredicto y la confianza."""
        return credibility_of(self.verdict, self.confidence)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def confidence_level(self) -> Optional[ConfidenceLevel]:
        """Tramo de la confianza del veredicto (`high`/`medium`/`low`) para su etiqueta."""
        return confidence_level_of(self.confidence)


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
    items: List[HistoryListItem]
    count: int
    page: int
    page_size: int
    verdict_counts: HistoryVerdictCounts
    source_type_counts: HistorySourceTypeCounts


class DeleteAllResponse(BaseModel):
    """Respuesta al eliminar todo el historial de análisis del usuario."""

    status: str
    deleted_count: int
