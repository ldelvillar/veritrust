"""Derivación de veredicto y credibilidad a partir de etiqueta y confianza.

``confidence`` es la seguridad del modelo en su veredicto; la credibilidad es lo
creíble que es el contenido: igual a la confianza para un veredicto verdadero e
invertida para uno falso. Es la única fuente de verdad de esta regla, compartida
por la respuesta de la API y la exportación CSV.
"""

from typing import Optional


def classify_verdict(label: Optional[str]) -> str:
    """Clasifica una etiqueta como ``real``, ``fake`` o ``uncertain``."""
    normalized = (label or "").lower()
    if "verdad" in normalized or "true" in normalized or "real" in normalized:
        return "real"
    if "fals" in normalized or "fake" in normalized:
        return "fake"
    return "uncertain"


def compute_credibility(
    label: Optional[str], confidence: Optional[float]
) -> Optional[int]:
    """Devuelve la credibilidad como entero [0, 100], o ``None`` sin confianza."""
    if confidence is None:
        return None

    fraction = confidence if confidence <= 1 else confidence / 100
    credibility = 1 - fraction if classify_verdict(label) == "fake" else fraction
    return max(0, min(100, round(credibility * 100)))
