"""Veredicto de un análisis, decidido solo a partir de la postura de la literatura recuperada."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Optional, get_args

VerdictKind = Literal["real", "fake", "uncertain"]

# Vocabulario único de veredicto, reutilizado en validación y persistencia.
VERDICT_KINDS: tuple[VerdictKind, ...] = get_args(VerdictKind)

ConfidenceLevel = Literal["high", "medium", "low"]

# Etiqueta en español con la que se guarda y se publica cada veredicto.
_LABELS: dict[VerdictKind, str] = {
    "real": "verdadera",
    "fake": "falsa",
    "uncertain": "incierta",
}
_KINDS_BY_LABEL: dict[str, VerdictKind] = {
    label: kind for kind, label in _LABELS.items()
}

# Punto neutro del score suavizado: por debajo la evidencia apoya, por encima refuta.
FAKE_THRESHOLD = 0.50
UNCERTAINTY_MARGIN = 0.05
# Pseudo-cuenta por postura: impide la certeza absoluta con evidencia escasa.
STANCE_SMOOTHING = 1.0
# Atenuación máxima de la confianza cuando no se halla evidencia que respalde el veredicto.
EVIDENCE_MAX_PENALTY = 0.25

# Cortes del tramo de confianza que ve el usuario, junto a las bandas del veredicto.
HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.6


@dataclass(frozen=True)
class EvidenceSearch:
    """Recuento de la búsqueda de literatura con el que se mide la cobertura de evidencia."""

    # Afirmaciones con una consulta utilizable: el denominador de la cobertura.
    total: int
    # Las que se llegaron a buscar; la cota deja fuera el resto.
    searched: int
    # Las que la literatura llegó a tratar.
    covered: int
    # Todas las buscadas toparon con fuentes inalcanzables.
    outage: bool


@dataclass(frozen=True)
class ClaimVerdict:
    """Veredicto de una afirmación concreta."""

    text: str
    kind: VerdictKind
    confidence: float

    @property
    def label(self) -> str:
        """Etiqueta en español del veredicto."""
        return _LABELS[self.kind]


@dataclass(frozen=True)
class Verdict:
    """Veredicto de un análisis con su confianza, su cobertura de evidencia y el de cada afirmación."""

    kind: VerdictKind
    # Confianza ya atenuada por la cobertura de evidencia.
    confidence: float
    # Probabilidad media de falsedad que vio la banda, antes de atenuar.
    falsehood: float
    # None cuando un corte de las fuentes impidió medirla.
    evidence_coverage: Optional[float]
    claims: tuple[ClaimVerdict, ...]

    @property
    def label(self) -> str:
        """Etiqueta en español del veredicto."""
        return _LABELS[self.kind]


def decide(
    claims: Sequence[str], sources: Sequence[dict], search: EvidenceSearch
) -> Verdict:
    """Decide el veredicto de cada afirmación y del análisis con la postura de las fuentes."""
    stances = _stance_counts(sources)
    claim_verdicts: list[ClaimVerdict] = []
    evidenced: list[float] = []
    for claim_index, text in enumerate(claims):
        counts = stances.get(claim_index, {"supports": 0, "contradicts": 0})
        falsehood = _falsehood(counts["supports"], counts["contradicts"])
        has_evidence = counts["supports"] + counts["contradicts"] > 0
        if has_evidence:
            evidenced.append(falsehood)
        kind, confidence = _band(falsehood, has_evidence)
        claim_verdicts.append(ClaimVerdict(text=text, kind=kind, confidence=confidence))

    # Solo promedia las afirmaciones sobre las que la literatura se pronuncia.
    falsehood = sum(evidenced) / len(evidenced) if evidenced else 0.5
    kind, confidence = _band(falsehood, bool(evidenced))
    penalized_coverage, evidence_coverage = _coverage(search)
    return Verdict(
        kind=kind,
        confidence=_attenuate(confidence, penalized_coverage),
        falsehood=falsehood,
        evidence_coverage=evidence_coverage,
        claims=tuple(claim_verdicts),
    )


def kind_of(label: Optional[str]) -> VerdictKind:
    """Devuelve el veredicto de una etiqueta guardada; una etiqueta desconocida cuenta como incierta."""
    return _KINDS_BY_LABEL.get(label or "", "uncertain")


def credibility_of(kind: VerdictKind, confidence: Optional[float]) -> Optional[int]:
    """Devuelve la credibilidad como entero [0, 100], o ``None``."""
    if confidence is None or kind == "uncertain":
        return None
    value = 1 - confidence if kind == "fake" else confidence
    return max(0, min(100, round(value * 100)))


def confidence_level_of(confidence: Optional[float]) -> Optional[ConfidenceLevel]:
    """Clasifica la confianza del veredicto como ``high``, ``medium`` o ``low``, o ``None``."""
    if confidence is None:
        return None
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        return "high"
    if confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


# La credibilidad [0, 1] de credibility_of() en SQL, para ordenar y agregar; incierto o sin confianza → NULL.
CREDIBILITY_SQL = (
    "CASE "
    "WHEN confidence IS NULL OR verdict = 'uncertain' THEN NULL "
    "WHEN verdict = 'fake' THEN 1 - confidence "
    "ELSE confidence "
    "END"
)


def _stance_counts(sources: Sequence[dict]) -> dict[int, dict[str, int]]:
    """Cuenta, por índice de afirmación, cuántas fuentes la respaldan o la contradicen."""
    counts: dict[int, dict[str, int]] = {}
    for source in sources:
        for statement in source.get("statements") or []:
            claim_index = statement.get("claim_index")
            stance = statement.get("stance")
            if not isinstance(claim_index, int) or stance not in (
                "supports",
                "contradicts",
            ):
                continue
            tally = counts.setdefault(claim_index, {"supports": 0, "contradicts": 0})
            tally[stance] += 1
    return counts


def _falsehood(supports: int, contradicts: int) -> float:
    """Probabilidad de falsedad de una afirmación según la postura de la literatura."""
    # Suavizado de Laplace: sin evidencia da 0.5 y unas pocas fuentes no bastan para la certeza.
    return (contradicts + STANCE_SMOOTHING) / (
        supports + contradicts + 2 * STANCE_SMOOTHING
    )


def _band(falsehood: float, has_evidence: bool) -> tuple[VerdictKind, float]:
    """Traduce una probabilidad de falsedad en veredicto y confianza."""
    # La ausencia de literatura no es prueba de falsedad: sin postura, es incierta.
    if not has_evidence:
        return "uncertain", 1.0 - falsehood
    if falsehood > FAKE_THRESHOLD + UNCERTAINTY_MARGIN:
        return "fake", falsehood
    if falsehood < FAKE_THRESHOLD - UNCERTAINTY_MARGIN:
        return "real", 1.0 - falsehood
    return "uncertain", 1.0 - falsehood


def _coverage(search: EvidenceSearch) -> tuple[float, Optional[float]]:
    """Devuelve la cobertura con la que se atenúa la confianza y la que ve el usuario."""
    if not search.total:
        return 0.0, 0.0
    # Un corte total no penaliza lo buscado (fallo nuestro), pero sí lo que la cota dejó fuera.
    if search.outage:
        return search.searched / search.total, None
    coverage = search.covered / search.total
    return coverage, coverage


def _attenuate(confidence: float, coverage: float) -> float:
    """Atenúa la confianza del veredicto según la cobertura de evidencia [0, 1]."""
    adjusted = confidence * (1 - EVIDENCE_MAX_PENALTY * (1 - coverage))
    return max(0.0, min(1.0, adjusted))
