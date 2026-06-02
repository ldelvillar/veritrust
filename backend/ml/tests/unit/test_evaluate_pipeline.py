"""Tests unitarios para la evaluación del pipeline multiagente."""

import asyncio

import pandas as pd
import pytest

from ml.evaluation import evaluate_pipeline as ep


def _row(expected: str, predicted: str | None, confidence: float = 0.9) -> ep.EvalRow:
    return {
        "text": "afirmacion de prueba",
        "expected": expected,
        "predicted": predicted,
        "confidence": confidence,
    }


def test_compute_metrics_perfect_classification() -> None:
    rows = [_row("falsa", "falsa"), _row("verdadera", "verdadera")]
    metrics = ep.compute_metrics(rows)

    assert metrics["tp"] == 1
    assert metrics["tn"] == 1
    assert metrics["fp"] == 0
    assert metrics["fn"] == 0
    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["evaluated"] == 2
    assert metrics["skipped"] == 0


def test_compute_metrics_counts_confusion_and_skips() -> None:
    rows = [
        _row("falsa", "falsa"),  # tp
        _row("falsa", "verdadera"),  # fn
        _row("verdadera", "falsa"),  # fp
        _row("verdadera", "verdadera"),  # tn
        _row("falsa", None),  # sin afirmaciones -> excluida
    ]
    metrics = ep.compute_metrics(rows)

    assert (metrics["tp"], metrics["fn"], metrics["fp"], metrics["tn"]) == (1, 1, 1, 1)
    assert metrics["evaluated"] == 4
    assert metrics["skipped"] == 1
    assert metrics["accuracy"] == 0.5


def test_compute_metrics_empty_rows_are_zero() -> None:
    metrics = ep.compute_metrics([])

    assert metrics["accuracy"] == 0.0
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1_score"] == 0.0
    assert metrics["evaluated"] == 0


def test_load_samples_balances_classes_and_maps_labels(monkeypatch) -> None:
    df = pd.DataFrame(
        {
            "claim": [f"c{i}" for i in range(8)],
            # 0->verdadera, 1->falsa, 3->falsa, 2->descartada
            "label": [0, 0, 0, 1, 1, 3, 2, 2],
        }
    )
    monkeypatch.setattr(ep, "load_dataset", lambda partition: df.copy())

    samples = ep.load_samples(partition="validation", limit=4, seed=1)

    assert len(samples) == 4
    labels = {s["expected"] for s in samples}
    assert labels <= {"verdadera", "falsa"}
    # La clase 'unproven' (2) nunca debe aparecer.
    assert all(s["text"] not in {"c6", "c7"} for s in samples)


def test_load_samples_skips_blank_claims(monkeypatch) -> None:
    df = pd.DataFrame({"claim": ["\xa0  ", "real claim"], "label": [0, 1]})
    monkeypatch.setattr(ep, "load_dataset", lambda partition: df.copy())

    samples = ep.load_samples(limit=2, seed=1)

    assert all(s["text"].strip() for s in samples)


def test_evaluate_pipeline_marks_missing_explanation_as_skipped() -> None:
    samples: list[ep.Sample] = [
        {"text": "tiene afirmaciones", "expected": "falsa"},
        {"text": "sin afirmaciones medicas", "expected": "verdadera"},
    ]

    class FakeGraph:
        async def ainvoke(self, state: dict) -> dict:
            if "sin" in state["input_text"]:
                return {"label": "", "confidence": 0.0, "medical_explanation": ""}
            return {
                "label": "falsa",
                "confidence": 0.8,
                "medical_explanation": "informe",
            }

    rows = asyncio.run(ep.evaluate_pipeline(samples, FakeGraph()))

    assert rows[0]["predicted"] == "falsa"
    assert rows[1]["predicted"] is None
    assert rows[1]["confidence"] == 0.0


def test_format_report_lists_misclassifications() -> None:
    rows = [_row("falsa", "verdadera", 0.7), _row("verdadera", "verdadera")]
    metrics = ep.compute_metrics(rows)

    report = ep.format_report(metrics, rows)

    assert "Evaluación del pipeline multiagente" in report
    assert "Errores de clasificación (1)" in report


def test_build_initial_state_has_pipeline_keys() -> None:
    state = ep._build_initial_state("hola")

    assert state["input_text"] == "hola"
    assert state["extracted_statements"] == []
    assert state["label"] == ""


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
