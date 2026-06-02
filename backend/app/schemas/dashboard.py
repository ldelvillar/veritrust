"""Este módulo define los esquemas de datos relacionados con el dashboard del usuario."""

from typing import Optional

from pydantic import BaseModel, computed_field

from app.core.credibility import compute_credibility


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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def credibility(self) -> Optional[int]:
        """Credibilidad [0, 100] derivada del veredicto y la confianza."""
        return compute_credibility(self.label, self.confidence)


class DashboardSummaryResponse(BaseModel):
    """Modelo de datos para el resumen del dashboard."""

    status: str
    kpis: DashboardKpis
    trend: list[DashboardTrendPoint]
    source_breakdown: list[DashboardSourceBreakdownItem]
    domain_breakdown: list[DashboardDomainBreakdownItem]
    alerts: list[DashboardAlertItem]
