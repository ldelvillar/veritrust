"""Tests del módulo del veredicto: posturas y recuento de la búsqueda en, veredicto tipado fuera."""

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
    """Búsqueda en la que la literatura trató todas las afirmaciones."""
    return EvidenceSearch(total=claims, searched=claims, covered=claims, outage=False)


def _claim(
    supports: int = 0,
    contradicts: int = 0,
    *,
    index: int = 0,
    text: str = "S1",
    others: tuple = (),
) -> Claim:
    """Afirmación juzgada con tantas fuentes a favor y en contra como se pidan, como la deja el investigador."""
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
        # Ninguna fuente se pronuncia: incierta por ausencia de evidencia, nunca falsa.
        (0, 0, "uncertain", 0.5),
        # Suavizado de Laplace: una sola fuente no da certeza plena, tres dan más.
        (1, 0, "real", 2 / 3),
        (3, 0, "real", 0.8),
        (0, 1, "fake", 2 / 3),
        (0, 3, "fake", 0.8),
        # Dos a favor y una en contra: falsedad 0.4, sigue verdadera con menos confianza.
        (2, 1, "real", 0.6),
        # Evidencia equilibrada: falsedad 0.5, el punto neutro es incierto.
        (1, 1, "uncertain", 0.5),
        # Los bordes de la banda neutra (0.45 y 0.55) siguen siendo inciertos.
        (10, 8, "uncertain", 0.55),
        (8, 10, "uncertain", 0.45),
        # Justo fuera de la banda ya hay veredicto firme.
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

    # Casando por texto ambas compartirían las 5 fuentes; cada una con la suya, 4/5 y 1/4.
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

    # Falsedad media = (0.4 + 0.25 + 0.25) / 3 = 0.3: verdadera, por debajo de 0.75.
    assert verdict.kind == "real"
    assert verdict.falsehood == pytest.approx(0.3)
    assert verdict.confidence == pytest.approx(0.7)


def test_claims_the_literature_ignores_do_not_dilute_the_verdict() -> None:
    search = EvidenceSearch(total=2, searched=2, covered=2, outage=False)

    verdict = decide([_claim(contradicts=3), _claim(index=1, text="S2")], search)

    # Solo promedia S1 (falsedad 0.8); S2, sin postura, queda incierta por su cuenta.
    assert (verdict.kind, verdict.falsehood) == ("fake", pytest.approx(0.8))
    assert verdict.claims[1].kind == "uncertain"


@pytest.mark.parametrize(
    ("search", "coverage", "confidence"),
    [
        # Toda la literatura hallada: sin atenuación.
        (EvidenceSearch(total=2, searched=2, covered=2, outage=False), 1.0, 0.75),
        # Media cobertura: 0.75 × (1 − 0.25 × 0.5).
        (EvidenceSearch(total=2, searched=2, covered=1, outage=False), 0.5, 0.65625),
        # Nada que buscar: cobertura 0 y atenuación máxima.
        (EvidenceSearch(total=0, searched=0, covered=0, outage=False), 0.0, 0.5625),
        # La cota deja 2 de 10 sin buscar: cuentan como no cubiertas.
        (EvidenceSearch(total=10, searched=8, covered=8, outage=False), 0.8, 0.7125),
    ],
)
def test_confidence_is_attenuated_by_evidence_coverage(
    search, coverage, confidence
) -> None:
    verdict = decide([_claim(supports=2)], search)

    assert verdict.evidence_coverage == pytest.approx(coverage)
    assert verdict.confidence == pytest.approx(confidence)
    # La atenuación es del veredicto global; el de cada afirmación no cambia.
    assert verdict.claims[0].confidence == pytest.approx(0.75)
    # La falsedad es la que vio la banda, antes de atenuar.
    assert verdict.falsehood == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("search", "confidence"),
    [
        # Todas las buscadas topan con fuentes caídas: fallo nuestro, sin penalizar.
        (EvidenceSearch(total=3, searched=3, covered=0, outage=True), 0.5),
        # Por encima de la cota solo penalizan las 2 que quedaron sin buscar.
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
    # Leer la etiqueta guardada devuelve el mismo veredicto.
    assert kind_of(label) == verdict.kind


@pytest.mark.parametrize("label", ["", None, "Falsa", "true", "fake", "dudosa"])
def test_an_unknown_stored_label_reads_as_uncertain(label) -> None:
    assert kind_of(label) == "uncertain"


@pytest.mark.parametrize(
    ("kind", "confidence", "credibility"),
    [
        ("real", 0.9, 90),
        # Un veredicto falso invierte la confianza: muy falso es poco creíble.
        ("fake", 0.85, 15),
        # Un veredicto incierto no tiene credibilidad bien definida aunque haya confianza.
        ("uncertain", 0.6, None),
        ("real", None, None),
        # Fuera de rango se acota a [0, 100].
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
