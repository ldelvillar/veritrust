"""
Este módulo define los esquemas de datos relacionados con el historial de análisis del usuario.
"""

from typing import List, Optional
from pydantic import BaseModel


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
