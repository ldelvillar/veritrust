"""Tests de los ajustes por evidencia: atenuación por cobertura y mezcla por postura."""

import pytest

from app.core.credibility import (
    adjust_confidence_with_evidence,
    blend_fake_prob_with_stance,
)


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


def test_no_pronounced_sources_leave_fake_prob_untouched():
    assert blend_fake_prob_with_stance(0.3, 0, 0) == pytest.approx(0.3)


def test_single_contradicting_source_nudges_fake_prob_up():
    # peso 1/6: (5/6) * 0.1 + (1/6) * 1 = 0.25
    assert blend_fake_prob_with_stance(0.1, 0, 1) == pytest.approx(0.25)


def test_single_supporting_source_nudges_fake_prob_down():
    # peso 1/6: (5/6) * 0.4 = 1/3
    assert blend_fake_prob_with_stance(0.4, 1, 0) == pytest.approx(1 / 3)


def test_three_contradicting_sources_can_flip_a_confident_claim():
    # peso máximo 0.5: 0.5 * 0.1 + 0.5 * 1 = 0.55, cruza el umbral de falsedad.
    assert blend_fake_prob_with_stance(0.1, 0, 3) == pytest.approx(0.55)


def test_weight_saturates_beyond_three_sources():
    assert blend_fake_prob_with_stance(0.1, 0, 5) == pytest.approx(
        blend_fake_prob_with_stance(0.1, 0, 3)
    )


def test_split_evidence_pulls_toward_half():
    # postura 0.5 con peso 1/3: (2/3) * 0.1 + (1/3) * 0.5 = 0.2333...
    assert blend_fake_prob_with_stance(0.1, 1, 1) == pytest.approx(0.7 / 3)
