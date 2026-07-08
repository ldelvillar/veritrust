"""Derivación de veredicto y credibilidad a partir de etiqueta y confianza."""

from typing import Literal, Optional, get_args

Verdict = Literal["real", "fake", "uncertain"]

# Vocabulario único de veredicto, reutilizado en validación y persistencia.
VERDICTS: tuple[Verdict, ...] = get_args(Verdict)


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
    """Devuelve la credibilidad como entero [0, 100], o ``None``."""
    if confidence is None or classify_verdict(label) == "uncertain":
        return None

    fraction = confidence if confidence <= 1 else confidence / 100
    credibility = 1 - fraction if classify_verdict(label) == "fake" else fraction
    return max(0, min(100, round(credibility * 100)))


# Misma credibilidad [0, 1] reproducida en SQL para ordenar y agregar; incierto/sin confianza → NULL.
CREDIBILITY_SQL_EXPR = (
    "CASE "
    "WHEN confidence IS NULL OR verdict = 'uncertain' THEN NULL "
    "WHEN verdict = 'fake' "
    "THEN 1 - (CASE WHEN confidence <= 1 THEN confidence ELSE confidence / 100.0 END) "
    "ELSE (CASE WHEN confidence <= 1 THEN confidence ELSE confidence / 100.0 END) "
    "END"
)


# Atenuación máxima de la confianza cuando no se halla evidencia que respalde el veredicto
EVIDENCE_MAX_PENALTY = 0.25


def adjust_confidence_with_evidence(
    confidence: float, evidence_coverage: float
) -> float:
    """Atenúa la confianza del veredicto según la cobertura de evidencia [0, 1]."""
    coverage = max(0.0, min(1.0, evidence_coverage))
    adjusted = confidence * (1 - EVIDENCE_MAX_PENALTY * (1 - coverage))
    return max(0.0, min(1.0, adjusted))


# Fracción de evidencia opuesta a partir de la cual un veredicto firme pasa a "incierta"
OPPOSITION_UNCERTAINTY_THRESHOLD = 0.5
# Atenuación máxima de la confianza por evidencia que contradice el veredicto
OPPOSITION_MAX_PENALTY = 0.25


def soften_verdict_with_opposition(
    label: str, confidence: float, opposition: float
) -> tuple[str, float]:
    """Ablanda (nunca invierte) un veredicto firme según la evidencia que lo contradice."""
    if label not in ("verdadera", "falsa") or opposition <= 0.0:
        return label, confidence
    opp = max(0.0, min(1.0, opposition))
    softened = max(0.0, min(1.0, confidence * (1 - OPPOSITION_MAX_PENALTY * opp)))
    if opp >= OPPOSITION_UNCERTAINTY_THRESHOLD:
        return "incierta", softened
    return label, softened
