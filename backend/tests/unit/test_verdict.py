"""Tests of the verdict module, with Stances and search counts in and a typed Verdict out."""

import pytest

from app.core.claim import Claim, Evidence, EvidenceSearch
from app.core.verdict import (
    ClaimVerdict,
    confidence_level_of,
    credibility_of,
    decide,
    kind_of,
)


def _full(claims: int) -> EvidenceSearch:
    """Search in which the literature covered every claim."""
    return EvidenceSearch(total=claims, searched=claims, covered=claims, outage=False)


def _claim(
    supports: int = 0,
    contradicts: int = 0,
    *,
    index: int = 0,
    text: str = "S1",
    others: tuple = (),
) -> Claim:
    """Judged claim with as many supporting and contradicting Sources as asked, as the investigator leaves it."""
    stances = ["supports"] * supports + ["contradicts"] * contradicts + list(others)
    return Claim(
        index=index,
        text=text,
        query='"q"',
        outcome="judged",
        evidence=tuple(
            Evidence(
                title=f"Fuente {i}",
                url=f"https://doi.org/10.1/{index}-{i}",
                stance=stance,
            )
            for i, stance in enumerate(stances)
        ),
    )


@pytest.mark.parametrize(
    ("supports", "contradicts", "kind", "confidence"),
    [
        # No Source rules, so it is uncertain for lack of Evidence, never false.
        (0, 0, "uncertain", 0.5),
        # Laplace smoothing, so one Source does not give full certainty and three give more.
        (1, 0, "real", 2 / 3),
        (3, 0, "real", 0.8),
        (0, 1, "fake", 2 / 3),
        (0, 3, "fake", 0.8),
        # Two supporting and one contradicting give falsehood 0.4, still true with less Confidence.
        (2, 1, "real", 0.6),
        # Balanced Evidence gives falsehood 0.5, and the neutral point is uncertain.
        (1, 1, "uncertain", 0.5),
        # The edges of the neutral band (0.45 and 0.55) are still uncertain.
        (10, 8, "uncertain", 0.55),
        (8, 10, "uncertain", 0.45),
        # Just outside the band there is a firm Verdict.
        (11, 8, "real", 12 / 21),
        (8, 11, "fake", 12 / 21),
    ],
)
def test_one_claim_is_banded_by_its_smoothed_falsehood(
    supports, contradicts, kind, confidence
) -> None:
    verdict = decide([_claim(supports, contradicts)], _full(1))

    assert verdict.kind == kind
    assert verdict.confidence == pytest.approx(confidence)
    assert verdict.claims == (
        ClaimVerdict(text="S1", kind=kind, confidence=pytest.approx(confidence)),
    )


def test_inconclusive_or_unjudged_evidence_does_not_count() -> None:
    verdict = decide([_claim(others=("inconclusive", None))], _full(1))

    assert (verdict.kind, verdict.confidence) == ("uncertain", 0.5)


def test_each_claim_is_decided_from_its_own_evidence() -> None:
    claims = [
        _claim(contradicts=3, index=0, text="Misma frase"),
        _claim(supports=2, index=1, text="Misma frase"),
    ]

    verdict = decide(claims, _full(2))

    # Matching by text both would share the 5 Sources, while each with its own gives 4/5 and 1/4.
    assert [(c.kind, c.confidence) for c in verdict.claims] == [
        ("fake", pytest.approx(0.8)),
        ("real", pytest.approx(0.75)),
    ]


def test_minority_contradiction_only_lowers_the_confidence() -> None:
    claims = [
        _claim(supports=2, contradicts=1, index=0),
        _claim(supports=2, index=1),
        _claim(supports=2, index=2),
    ]

    verdict = decide(claims, _full(3))

    # Mean falsehood = (0.4 + 0.25 + 0.25) / 3 = 0.3, true and below 0.75.
    assert verdict.kind == "real"
    assert verdict.falsehood == pytest.approx(0.3)
    assert verdict.confidence == pytest.approx(0.7)


def test_claims_the_literature_ignores_do_not_dilute_the_verdict() -> None:
    search = EvidenceSearch(total=2, searched=2, covered=2, outage=False)

    verdict = decide([_claim(contradicts=3), _claim(index=1, text="S2")], search)

    # Only S1 (falsehood 0.8) is averaged, and S2, without a Stance, is uncertain on its own.
    assert (verdict.kind, verdict.falsehood) == ("fake", pytest.approx(0.8))
    assert verdict.claims[1].kind == "uncertain"


def test_a_true_claim_never_offsets_a_false_one() -> None:
    # A hoax wrapped in a truth, bleach refuted by one Source and paracetamol backed by four.
    claims = [_claim(contradicts=1, index=0), _claim(supports=4, index=1)]

    verdict = decide(claims, _full(2))

    # The mean (0.67 + 0.17) / 2 = 0.42 would call it true, but it is partly false.
    assert verdict.kind == "mixed"
    assert verdict.falsehood == pytest.approx(5 / 12)
    assert [c.kind for c in verdict.claims] == ["fake", "real"]


def test_partly_false_confidence_is_the_strongest_false_claim() -> None:
    claims = [
        _claim(contradicts=1, index=0),
        _claim(contradicts=3, index=1),
        _claim(supports=3, index=2),
    ]

    verdict = decide(claims, _full(3))

    assert (verdict.kind, verdict.confidence) == ("mixed", pytest.approx(0.8))


def test_an_uncertain_claim_does_not_soften_a_false_one() -> None:
    # False (12/21) next to an uncertain one (0.45), where the mean 0.51 would fall in the neutral band.
    claims = [_claim(8, 11), _claim(10, 8, index=1, text="S2")]

    verdict = decide(claims, _full(2))

    assert (verdict.kind, verdict.confidence) == ("fake", pytest.approx(12 / 21))


@pytest.mark.parametrize(
    ("neutral", "confidence"),
    [
        # Bleach with no Source ruling next to backed paracetamol.
        ((0, 0), 0.5),
        # An uncertain one with balanced Evidence (falsehood 0.55) brings its Confidence.
        ((8, 10), 0.45),
    ],
)
def test_a_true_claim_never_vouches_for_an_uncertain_one(neutral, confidence) -> None:
    claims = [_claim(supports=4), _claim(*neutral, index=1, text="S2")]

    verdict = decide(claims, _full(2))

    assert (verdict.kind, verdict.confidence) == (
        "uncertain",
        pytest.approx(confidence),
    )
    assert [c.kind for c in verdict.claims] == ["real", "uncertain"]


def test_only_uncertain_claims_keep_the_analysis_uncertain() -> None:
    claims = [_claim(supports=1, contradicts=1), _claim(10, 8, index=1, text="S2")]

    verdict = decide(claims, _full(2))

    # Falsehoods 0.5 and 0.45 have a mean of 0.475, still in the neutral band.
    assert (verdict.kind, verdict.confidence) == ("uncertain", pytest.approx(0.525))


@pytest.mark.parametrize(
    ("search", "coverage", "confidence"),
    [
        # All the literature found, so no attenuation.
        (EvidenceSearch(total=2, searched=2, covered=2, outage=False), 1.0, 0.75),
        # Half coverage gives 0.75 × (1 − 0.25 × 0.5).
        (EvidenceSearch(total=2, searched=2, covered=1, outage=False), 0.5, 0.65625),
        # Nothing to search, so coverage 0 and maximum attenuation.
        (EvidenceSearch(total=0, searched=0, covered=0, outage=False), 0.0, 0.5625),
        # The cap leaves 2 of 10 unsearched, which count as uncovered.
        (EvidenceSearch(total=10, searched=8, covered=8, outage=False), 0.8, 0.7125),
    ],
)
def test_confidence_is_attenuated_by_evidence_coverage(
    search, coverage, confidence
) -> None:
    verdict = decide([_claim(supports=2)], search)

    assert verdict.evidence_coverage == pytest.approx(coverage)
    assert verdict.confidence == pytest.approx(confidence)
    # The attenuation is of the overall Verdict, and each claim's does not change.
    assert verdict.claims[0].confidence == pytest.approx(0.75)
    # The falsehood is the one the band saw, before attenuation.
    assert verdict.falsehood == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("search", "confidence"),
    [
        # Every searched claim hits down sources, our failure, so no penalty.
        (EvidenceSearch(total=3, searched=3, covered=0, outage=True), 0.5),
        # Above the cap only the 2 left unsearched penalise.
        (EvidenceSearch(total=10, searched=8, covered=0, outage=True), 0.475),
    ],
)
def test_an_evidence_outage_leaves_coverage_unknown(search, confidence) -> None:
    verdict = decide([_claim()], search)

    assert verdict.evidence_coverage is None
    assert verdict.kind == "uncertain"
    assert verdict.confidence == pytest.approx(confidence)


@pytest.mark.parametrize(
    ("contradicts", "supports", "label"),
    [(3, 0, "falsa"), (0, 3, "verdadera"), (1, 1, "incierta")],
)
def test_the_spanish_label_follows_the_verdict(contradicts, supports, label) -> None:
    verdict = decide([_claim(supports, contradicts)], _full(1))

    assert verdict.label == verdict.claims[0].label == label
    # Reading the stored label returns the same Verdict.
    assert kind_of(label) == verdict.kind


def test_the_partly_false_label_reads_back_as_mixed() -> None:
    verdict = decide([_claim(contradicts=3), _claim(supports=3, index=1)], _full(2))

    assert verdict.label == "parcialmente falsa"
    assert kind_of(verdict.label) == "mixed"


@pytest.mark.parametrize("label", ["", None, "Falsa", "true", "fake", "dudosa"])
def test_an_unknown_stored_label_reads_as_uncertain(label) -> None:
    assert kind_of(label) == "uncertain"


@pytest.mark.parametrize(
    ("kind", "confidence", "credibility"),
    [
        ("real", 0.9, 90),
        # A false Verdict inverts the Confidence, so very false is barely credible.
        ("fake", 0.85, 15),
        # An uncertain Verdict has no well-defined Credibility even with Confidence.
        ("uncertain", 0.6, None),
        # Partly false content has none either, since one number does not describe the mix.
        ("mixed", 0.8, None),
        ("real", None, None),
        # Out of range is clamped to [0, 100].
        ("fake", -0.2, 100),
        ("real", -0.5, 0),
    ],
)
def test_credibility_follows_from_verdict_and_confidence(
    kind, confidence, credibility
) -> None:
    assert credibility_of(kind, confidence) == credibility


@pytest.mark.parametrize(
    ("confidence", "level"),
    [
        (0.85, "high"),
        (0.849, "medium"),
        (0.6, "medium"),
        (0.599, "low"),
        (0.0, "low"),
        (None, None),
    ],
)
def test_confidence_level_bands_at_inclusive_lower_bounds(confidence, level) -> None:
    assert confidence_level_of(confidence) == level
