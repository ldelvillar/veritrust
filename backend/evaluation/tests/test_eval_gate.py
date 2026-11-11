"""Unit tests for the CI gate that compares a PR's pipeline evaluation with main's."""

import json
import sys

import pytest

from evaluation import eval_gate as gate
from evaluation import evaluate_pipeline as ep


def _samples(n: int) -> list[ep.Sample]:
    """Alternate false and true samples, so each class has n/2."""
    return [
        {"text": f"afirmacion {i}", "expected": "falsa" if i % 2 else "verdadera"}
        for i in range(n)
    ]


def _arm(
    samples: list[ep.Sample],
    wrong: int = 0,
    drop: int = 0,
    uncertain: int = 0,
    no_claims: int = 0,
) -> gate.Arm:
    """Arm that misjudges the first `wrong` samples, abstains on the next `uncertain`, finds no claims in the next `no_claims` and lacks the last `drop`."""
    rows: dict[str, ep.EvalRow] = {}
    for i, sample in enumerate(samples[: len(samples) - drop]):
        flipped = "verdadera" if sample["expected"] == "falsa" else "falsa"
        if i < wrong:
            predicted: str | None = flipped
        elif i < wrong + uncertain:
            predicted = "incierta"
        elif i < wrong + uncertain + no_claims:
            predicted = None
        else:
            predicted = sample["expected"]
        rows[sample["text"]] = {
            "text": sample["text"],
            "expected": sample["expected"],
            "predicted": predicted,
            "confidence": 0.9,
            "fake_avg": None,
            "duration_seconds": 0.0,
        }
    return gate.Arm(run=None, rows=rows)


def test_identical_arms_pass() -> None:
    samples = _samples(20)

    result = gate.evaluate_gate(samples, _arm(samples), _arm(samples))

    assert result.passed
    assert result.report.startswith(gate.MARKER)


def test_an_accuracy_drop_beyond_its_tolerance_fails() -> None:
    samples = _samples(20)

    # Two of twenty wrong is a 10-point drop, past the 5-point tolerance.
    result = gate.evaluate_gate(samples, _arm(samples), _arm(samples, wrong=2))

    assert not result.passed
    assert "| accuracy | 100.0% | 90.0% | -10.0 pp | -5 pp | ❌ |" in result.report


def test_a_drop_of_exactly_the_tolerance_passes() -> None:
    samples = _samples(20)

    result = gate.evaluate_gate(samples, _arm(samples), _arm(samples, wrong=1))

    assert result.passed


def test_abstaining_more_fails_on_coverage() -> None:
    samples = _samples(20)

    # Abstaining keeps accuracy at 100% but drops coverage from 100% to 85%.
    result = gate.evaluate_gate(samples, _arm(samples), _arm(samples, uncertain=3))

    assert not result.passed
    assert "| coverage | 100.0% | 85.0% | -15.0 pp | -10 pp | ❌ |" in result.report


def test_finding_no_claims_in_more_samples_fails() -> None:
    samples = _samples(20)

    # Samples with no claims leave accuracy and coverage untouched, so only this gate sees them.
    result = gate.evaluate_gate(samples, _arm(samples), _arm(samples, no_claims=2))

    assert not result.passed
    assert "| claims_found | 100.0% | 90.0% | -10.0 pp | -5 pp | ❌ |" in result.report


def test_samples_one_arm_lacks_are_left_out_of_both() -> None:
    samples = _samples(20)

    # Main got the last sample wrong, but the PR never evaluated it, so it does not count.
    base = _arm(samples)
    last = samples[-1]["text"]
    base.rows[last]["predicted"] = "incierta"

    result = gate.evaluate_gate(samples, base, _arm(samples, drop=1))

    assert result.passed
    assert "19 de 20 muestras" in result.report


def test_an_arm_that_lost_too_many_samples_fails() -> None:
    samples = _samples(20)

    result = gate.evaluate_gate(
        samples, _arm(samples), _arm(samples, drop=gate.MAX_MISSING + 1)
    )

    assert not result.passed
    assert f"PR perdió {gate.MAX_MISSING + 1} muestras" in result.report


def test_main_writes_the_report_and_exits_non_zero_on_a_regression(
    monkeypatch, tmp_path
) -> None:
    samples = _samples(20)
    paths = {}
    for name, arm in {"base": _arm(samples), "head": _arm(samples, wrong=4)}.items():
        header = {"run": {"git": f"{name}123", "prompts": {"judge": "v7"}}}
        paths[name] = tmp_path / f"{name}.jsonl"
        paths[name].write_text(
            "\n".join(json.dumps(r) for r in [header, *arm.rows.values()]),
            encoding="utf-8",
        )
    report = tmp_path / "report.md"
    monkeypatch.setattr(gate, "load_samples", lambda *_: samples)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "eval_gate",
            f"--base={paths['base']}",
            f"--head={paths['head']}",
            f"--report={report}",
            "--commit=abc1234",
        ],
    )

    with pytest.raises(SystemExit) as exit_info:
        gate.main()

    assert exit_info.value.code == 1
    written = report.read_text(encoding="utf-8")
    assert "### Puerta de evaluación para `abc1234`: ❌ falla" in written
    assert "git `head123` · prompts judge=v7" in written
