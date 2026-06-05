"""Derivación de veredicto y credibilidad a partir de etiqueta y confianza."""

from typing import Literal, Optional

Verdict = Literal["real", "fake", "uncertain"]


def classify_verdict(label: Optional[str]) -> Verdict:
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


# Atenuación máxima de la confianza cuando no se halla evidencia que respalde el veredicto
EVIDENCE_MAX_PENALTY = 0.25


def adjust_confidence_with_evidence(
    confidence: float, evidence_coverage: float
) -> float:
    """Atenúa la confianza del veredicto según la cobertura de evidencia [0, 1]."""
    coverage = max(0.0, min(1.0, evidence_coverage))
    adjusted = confidence * (1 - EVIDENCE_MAX_PENALTY * (1 - coverage))
    return max(0.0, min(1.0, adjusted))
