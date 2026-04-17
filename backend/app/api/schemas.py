"""Este módulo define los esquemas de datos para las solicitudes de la API."""

from enum import Enum
from typing import Annotated, List, Optional
from pydantic import BaseModel, HttpUrl, StringConstraints, model_validator


class SourceType(str, Enum):
    """Tipos de fuentes de entrada para el análisis."""

    TEXT = "text"
    FILE = "file"
    URL = "url"


class AnalysisRequest(BaseModel):
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
    def validate_payload_coherence(self) -> "AnalysisRequest":
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


class AnalysisResponse(BaseModel):
    """Modelo de datos para la respuesta del análisis."""

    status: str
    analysis_id: Optional[str] = None
    message: Optional[str] = None
    label: Optional[str] = None
    confidence: Optional[float] = None
    explanation: Optional[str] = None


class AnalysisHistoryItem(BaseModel):
    """Modelo de datos para un ítem del historial de análisis."""

    analysis_id: str
    user_id: str
    source_type: str
    input_text: Optional[str] = None
    input_url: Optional[str] = None
    label: str
    confidence: float
    explanation: str
    created_at: str


class HistoryResponse(BaseModel):
    """Modelo de datos para la respuesta del endpoint de historial de análisis."""

    status: str
    items: List[AnalysisHistoryItem]
    count: int
    page: int
    page_size: int


class DashboardKpis(BaseModel):
    """Modelo de datos para los KPIs del dashboard."""

    total_analyses: int
    reliable_rate: float
    average_confidence: float
    week_over_week_delta: float


class DashboardTrendPoint(BaseModel):
    """Modelo de datos para un punto de tendencia en el dashboard."""

    date: str
    total: int
    average_confidence: float


class DashboardSourceBreakdownItem(BaseModel):
    """Modelo de datos para un ítem de desglose por fuente en el dashboard."""

    source_type: str
    total: int
    average_confidence: float


class DashboardDomainBreakdownItem(BaseModel):
    """Modelo de datos para un ítem de desglose por dominio en el dashboard."""

    domain: str
    total: int
    average_confidence: float


class DashboardAlertItem(BaseModel):
    """Modelo de datos para un ítem de alerta en el dashboard."""

    id: str
    source_type: str
    input_text: Optional[str] = None
    input_url: Optional[str] = None
    label: str
    confidence: float
    created_at: str


class DashboardSummaryResponse(BaseModel):
    """Modelo de datos para el resumen del dashboard."""

    status: str
    kpis: DashboardKpis
    trend: list[DashboardTrendPoint]
    source_breakdown: list[DashboardSourceBreakdownItem]
    domain_breakdown: list[DashboardDomainBreakdownItem]
    alerts: list[DashboardAlertItem]
