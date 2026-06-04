"""Tests de la atenuación de confianza por cobertura de evidencia."""

import pytest

from app.core.credibility import adjust_confidence_with_evidence


def test_full_coverage_keeps_confidence():
    assert adjust_confidence_with_evidence(0.9, 1.0) == pytest.approx(0.9)


def test_zero_coverage_applies_max_penalty():
    # 0.9 * (1 - 0.25) = 0.675
    assert adjust_confidence_with_evidence(0.9, 0.0) == pytest.approx(0.675)


def test_partial_coverage_applies_partial_penalty():
    # 0.8 * (1 - 0.25 * 0.5) = 0.8 * 0.875 = 0.7
    assert adjust_confidence_with_evidence(0.8, 0.5) == pytest.approx(0.7)


def test_coverage_is_clamped_to_unit_interval():
    assert adjust_confidence_with_evidence(0.6, 5.0) == pytest.approx(0.6)
    assert adjust_confidence_with_evidence(0.6, -1.0) == pytest.approx(0.45)


def test_result_never_exceeds_one():
    assert adjust_confidence_with_evidence(1.0, 1.0) <= 1.0
