"""Tests unitarios para la derivación de veredicto y credibilidad."""

import re

from app.core.credibility import (
    VERDICT_FAKE_SQL,
    VERDICT_REAL_SQL,
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


def _bucket_via_sql_mirror(label: str | None) -> str:
    """Clasifica como lo haría el espejo SQL: LIKE '%token%' equivale a contención."""
    text = (label or "").lower()
    real_tokens = re.findall(r"%%(\w+)%%", VERDICT_REAL_SQL)
    fake_tokens = re.findall(r"%%(\w+)%%", VERDICT_FAKE_SQL)
    if any(token in text for token in real_tokens):
        return "real"
    if any(token in text for token in fake_tokens):
        return "fake"
    return "uncertain"


def test_sql_verdict_mirror_matches_classify_verdict() -> None:
    # Incluye los casos que el espejo antiguo (prefijo, sin 'real') clasificaba mal.
    labels = [
        "verdadera",
        "Contenido verdadero",
        "real",
        "true",
        "falsa",
        "información falsa",
        "fake",
        "incierta",
        "",
        None,
    ]
    for label in labels:
        assert _bucket_via_sql_mirror(label) == classify_verdict(label), label


def test_compute_credibility_keeps_confidence_for_real_verdict() -> None:
    assert compute_credibility("verdadera", 0.9) == 90


def test_compute_credibility_inverts_confidence_for_fake_verdict() -> None:
    assert compute_credibility("falsa", 0.85) == 15


def test_compute_credibility_returns_none_without_confidence() -> None:
    assert compute_credibility("verdadera", None) is None


def test_compute_credibility_returns_none_for_uncertain_verdict() -> None:
    # Un veredicto incierto no tiene credibilidad bien definida aunque haya confianza.
    assert compute_credibility("incierta", 0.6) is None


def test_compute_credibility_normalizes_and_clamps() -> None:
    assert compute_credibility("verdadera", 90) == 90  # ya en porcentaje
    assert compute_credibility("falsa", -0.2) == 100  # invertido y acotado
    assert compute_credibility("verdadera", -0.5) == 0
