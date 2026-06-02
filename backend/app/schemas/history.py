"""
Este módulo define los esquemas de datos relacionados con el historial de análisis del usuario.
"""

from typing import List, Optional

from pydantic import BaseModel, computed_field

from app.core.credibility import compute_credibility


class AnalysisHistoryItem(BaseModel):
    """Modelo de datos para un ítem del historial de análisis.

    Las columnas de resultado son ``None`` mientras ``status == "pending"`` y se
    rellenan cuando el worker termina; en ``status == "failed"`` ``error_code``
    lleva el código de error estable del contrato.
    """

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
