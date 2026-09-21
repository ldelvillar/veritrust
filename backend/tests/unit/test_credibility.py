"""Tests unitarios para la derivación de veredicto y credibilidad."""

from app.core.credibility import (
    VERDICTS,
    classify_confidence,
    classify_verdict,
    compute_credibility,
)


def test_classify_verdict_buckets_labels() -> None:
    assert classify_verdict("verdadera") == "real"
    assert classify_verdict("Noticia falsa") == "fake"
    assert classify_verdict("true") == "real"
    assert classify_verdict("fake") == "fake"
    assert classify_verdict("") == "uncertain"
    assert classify_verdict(None) == "uncertain"


def test_classify_verdict_output_is_always_a_known_verdict() -> None:
    # El vocabulario persistido y validado debe cubrir toda salida de classify_verdict.
    for label in ("verdadera", "falsa", "incierta", "", None):
        assert classify_verdict(label) in VERDICTS


def test_compute_credibility_keeps_confidence_for_real_verdict() -> None:
    assert compute_credibility("verdadera", 0.9) == 90


def test_compute_credibility_inverts_confidence_for_fake_verdict() -> None:
    assert compute_credibility("falsa", 0.85) == 15


def test_compute_credibility_returns_none_without_confidence() -> None:
    assert compute_credibility("verdadera", None) is None


def test_compute_credibility_returns_none_for_uncertain_verdict() -> None:
    # Un veredicto incierto no tiene credibilidad bien definida aunque haya confianza.
    assert compute_credibility("incierta", 0.6) is None


def test_compute_credibility_clamps_out_of_range_confidence() -> None:
    assert compute_credibility("falsa", -0.2) == 100  # invertido y acotado
    assert compute_credibility("verdadera", -0.5) == 0


def test_classify_confidence_buckets_at_inclusive_lower_bounds() -> None:
    assert classify_confidence(0.85) == "high"
    assert classify_confidence(0.849) == "medium"
    assert classify_confidence(0.6) == "medium"
    assert classify_confidence(0.599) == "low"
    assert classify_confidence(0.0) == "low"


def test_classify_confidence_returns_none_without_confidence() -> None:
    assert classify_confidence(None) is None
