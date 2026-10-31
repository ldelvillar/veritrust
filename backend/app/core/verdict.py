"""Verdict of an Analysis, decided only from the Stance of the retrieved literature."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Optional, get_args

from app.core.claim import Claim, EvidenceSearch

VerdictKind = Literal["real", "fake", "mixed", "uncertain"]

# Single Verdict vocabulary, reused in validation and persistence.
VERDICT_KINDS: tuple[VerdictKind, ...] = get_args(VerdictKind)

ConfidenceLevel = Literal["high", "medium", "low"]

# Spanish label each Verdict is stored and published with.
_LABELS: dict[VerdictKind, str] = {
    "real": "verdadera",
    "fake": "falsa",
    "mixed": "parcialmente falsa",
    "uncertain": "incierta",
}
_KINDS_BY_LABEL: dict[str, VerdictKind] = {
    label: kind for kind, label in _LABELS.items()
}

# Neutral point of the smoothed score, where below it the Evidence supports and above it refutes.
FAKE_THRESHOLD = 0.50
UNCERTAINTY_MARGIN = 0.05
# Pseudo-count per Stance, which prevents absolute certainty from scarce Evidence.
STANCE_SMOOTHING = 1.0
# Maximum attenuation of the Confidence when no Evidence backs the Verdict.
EVIDENCE_MAX_PENALTY = 0.25

# Cut-offs of the Confidence band the user sees, next to the Verdict bands.
HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.6


@dataclass(frozen=True)
class ClaimVerdict:
    """Verdict of one claim."""

    text: str
    kind: VerdictKind
    confidence: float

    @property
    def label(self) -> str:
        """Spanish label of the Verdict."""
        return _LABELS[self.kind]


@dataclass(frozen=True)
class Verdict:
    """Verdict of an Analysis with its Confidence, its Evidence coverage and each claim's Verdict."""

    kind: VerdictKind
    # Confidence already attenuated by Evidence coverage.
    confidence: float
    # Mean falsehood probability of the claims with Evidence, before attenuation.
    falsehood: float
    # None when a source outage prevented measuring it.
    evidence_coverage: Optional[float]
    claims: tuple[ClaimVerdict, ...]

    @property
    def label(self) -> str:
        """Spanish label of the Verdict."""
        return _LABELS[self.kind]


def decide(claims: Sequence[Claim], search: EvidenceSearch) -> Verdict:
    """Decide the Verdict of each claim and of the Analysis from the Stance of its Evidence."""
    claim_verdicts: list[ClaimVerdict] = []
    evidenced: list[float] = []
    for claim in claims:
        supports = sum(item.stance == "supports" for item in claim.evidence)
        contradicts = sum(item.stance == "contradicts" for item in claim.evidence)
        falsehood = _falsehood(supports, contradicts)
        has_evidence = supports + contradicts > 0
        if has_evidence:
            evidenced.append(falsehood)
        kind, confidence = _band(falsehood, has_evidence)
        claim_verdicts.append(
            ClaimVerdict(text=claim.text, kind=kind, confidence=confidence)
        )

    # Only averages the claims the literature rules on.
    falsehood = sum(evidenced) / len(evidenced) if evidenced else 0.5
    kind, confidence = _overall(claim_verdicts, falsehood, bool(evidenced))
    penalized_coverage, evidence_coverage = _coverage(search)
    return Verdict(
        kind=kind,
        confidence=_attenuate(confidence, penalized_coverage),
        falsehood=falsehood,
        evidence_coverage=evidence_coverage,
        claims=tuple(claim_verdicts),
    )


def kind_of(label: Optional[str]) -> VerdictKind:
    """Return the Verdict of a stored label, where an unknown label counts as uncertain."""
    return _KINDS_BY_LABEL.get(label or "", "uncertain")


def credibility_of(kind: VerdictKind, confidence: Optional[float]) -> Optional[int]:
    """Return the Credibility as an integer in [0, 100], or ``None``."""
    if confidence is None or kind in ("uncertain", "mixed"):
        return None
    value = 1 - confidence if kind == "fake" else confidence
    return max(0, min(100, round(value * 100)))


def confidence_level_of(confidence: Optional[float]) -> Optional[ConfidenceLevel]:
    """Classify the Verdict's Confidence as ``high``, ``medium`` or ``low``, or ``None``."""
    if confidence is None:
        return None
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        return "high"
    if confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


# SQL twin of credibility_of() for sorting and aggregating.
CREDIBILITY_SQL = (
    "CASE "
    "WHEN confidence IS NULL OR verdict IN ('uncertain', 'mixed') THEN NULL "
    "WHEN verdict = 'fake' THEN 1 - confidence "
    "ELSE confidence "
    "END"
)


def _falsehood(supports: int, contradicts: int) -> float:
    """Falsehood probability of a claim from the Stance of the literature."""
    # Laplace smoothing, so no Evidence gives 0.5 and a few Sources are not enough for certainty.
    return (contradicts + STANCE_SMOOTHING) / (
        supports + contradicts + 2 * STANCE_SMOOTHING
    )


def _band(falsehood: float, has_evidence: bool) -> tuple[VerdictKind, float]:
    """Turn a falsehood probability into a Verdict and Confidence."""
    # Missing literature is no proof of falsehood, so without a Stance it is uncertain.
    if not has_evidence:
        return "uncertain", 1.0 - falsehood
    if falsehood > FAKE_THRESHOLD + UNCERTAINTY_MARGIN:
        return "fake", falsehood
    if falsehood < FAKE_THRESHOLD - UNCERTAINTY_MARGIN:
        return "real", 1.0 - falsehood
    return "uncertain", 1.0 - falsehood


def _overall(
    claims: Sequence[ClaimVerdict], falsehood: float, has_evidence: bool
) -> tuple[VerdictKind, float]:
    """Decide the overall Verdict from each claim's, where a true one never offsets a false one or backs an uncertain one."""
    fake = [claim.confidence for claim in claims if claim.kind == "fake"]
    real = [claim.confidence for claim in claims if claim.kind == "real"]
    uncertain = [claim.confidence for claim in claims if claim.kind == "uncertain"]
    if fake and real:
        # The warning follows the strongest false claim.
        return "mixed", max(fake)
    if fake:
        return "fake", sum(fake) / len(fake)
    if real and uncertain:
        # A text is only true if everything it claims could be verified (ADR-0003).
        return "uncertain", sum(uncertain) / len(uncertain)
    if real:
        return "real", sum(real) / len(real)
    return _band(falsehood, has_evidence)


def _coverage(search: EvidenceSearch) -> tuple[float, Optional[float]]:
    """Return the coverage that attenuates the Confidence and the one the user sees."""
    if not search.total:
        return 0.0, 0.0
    # A total outage does not penalise what was searched (our failure), but does penalise what the cap left out.
    if search.outage:
        return search.searched / search.total, None
    coverage = search.covered / search.total
    return coverage, coverage


def _attenuate(confidence: float, coverage: float) -> float:
    """Attenuate the Verdict's Confidence by Evidence coverage in [0, 1]."""
    adjusted = confidence * (1 - EVIDENCE_MAX_PENALTY * (1 - coverage))
    return max(0.0, min(1.0, adjusted))
