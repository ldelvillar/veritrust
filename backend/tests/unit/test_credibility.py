"""Tests unitarios para la derivación de veredicto y credibilidad."""

from app.core.credibility import classify_verdict, compute_credibility


def test_classify_verdict_buckets_labels() -> None:
    assert classify_verdict("verdadera") == "real"
    assert classify_verdict("Noticia falsa") == "fake"
    assert classify_verdict("true") == "real"
    assert classify_verdict("fake") == "fake"
    assert classify_verdict("") == "uncertain"
    assert classify_verdict(None) == "uncertain"


def test_compute_credibility_keeps_confidence_for_real_verdict() -> None:
    assert compute_credibility("verdadera", 0.9) == 90


def test_compute_credibility_inverts_confidence_for_fake_verdict() -> None:
    assert compute_credibility("falsa", 0.85) == 15


def test_compute_credibility_returns_none_without_confidence() -> None:
    assert compute_credibility("verdadera", None) is None


def test_compute_credibility_normalizes_and_clamps() -> None:
    assert compute_credibility("verdadera", 90) == 90  # ya en porcentaje
    assert compute_credibility("falsa", -0.2) == 100  # invertido y acotado
    assert compute_credibility("verdadera", -0.5) == 0
