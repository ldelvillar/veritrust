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


def test_more_misclassified_samples_than_the_tolerance_fails_on_accuracy() -> None:
    samples = _samples(40)

    # Four more wrong is one past the 3-sample tolerance, on whichever class they fall.
    result = gate.evaluate_gate(samples, _arm(samples), _arm(samples, wrong=4))

    assert not result.passed
    assert (
        "| accuracy | 100.0% | 90.0% | -10.0 pp (+4 fallos) | +3 fallos | ❌ |"
        in result.report
    )


def test_misclassifying_exactly_the_tolerance_passes() -> None:
    samples = _samples(40)

    # Three more wrong is exactly accuracy's tolerance.
    result = gate.evaluate_gate(samples, _arm(samples), _arm(samples, wrong=3))

    assert result.passed


def test_more_false_negatives_than_the_tolerance_fails_on_recall() -> None:
    samples = _samples(40)
    head = _arm(samples)
    # Three false samples called true, within accuracy's tolerance but past recall's 2.
    for sample in [s for s in samples if s["expected"] == "falsa"][:3]:
        head.rows[sample["text"]]["predicted"] = "verdadera"

    result = gate.evaluate_gate(samples, _arm(samples), head)

    assert not result.passed
    assert "| recall | 100.0% | 85.0% | -15.0 pp (+3 fallos) | +2 fallos | ❌ |" in (
        result.report
    )


def test_the_worst_no_change_run_passes() -> None:
    samples = _samples(100)

    # The worst no-change pair measured: 2 more false negatives, 1 more false positive and 4 more abstentions.
    head = _arm(samples, uncertain=4)
    rest = samples[4:]
    for sample in [s for s in rest if s["expected"] == "falsa"][:2]:
        head.rows[sample["text"]]["predicted"] = "verdadera"
    first_true = next(s for s in rest if s["expected"] == "verdadera")
    head.rows[first_true["text"]]["predicted"] = "falsa"

    result = gate.evaluate_gate(samples, _arm(samples), head)

    assert result.passed


def test_abstaining_more_fails_on_coverage() -> None:
    samples = _samples(20)

    # Abstaining keeps accuracy at 100% but drops coverage from 100% to 85%.
    result = gate.evaluate_gate(samples, _arm(samples), _arm(samples, uncertain=3))

    assert not result.passed
    assert "| coverage | 100.0% | 85.0% | -15.0 pp | -4 pp | ❌ |" in result.report


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


@pytest.mark.parametrize("side", ["base", "head"])
def test_arms_labelled_unlike_the_samples_fail_as_incomparable(side: str) -> None:
    samples = _samples(20)

    # One arm's rows carry a label the gate's sampling no longer gives, as when labelling code changes.
    arms = {"base": _arm(samples), "head": _arm(samples)}
    arms[side].rows[samples[0]["text"]]["expected"] = "falsa"

    result = gate.evaluate_gate(samples, arms["base"], arms["head"])

    assert not result.passed
    assert "1 muestras tienen otra etiqueta" in result.report
    assert "| Métrica |" not in result.report


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
