"""Tests unitarios para la evaluación aislada del clasificador BERT."""

import pandas as pd
import pytest

from ml.evaluation import evaluate_classifier as ec


def _row(expected: str, predicted: str, confidence: float = 0.9) -> ec.EvalRow:
    return {
        "text": "afirmacion de prueba",
        "expected": expected,
        "predicted": predicted,
        "confidence": confidence,
    }


def test_compute_metrics_perfect_classification() -> None:
    rows = [_row("falsa", "falsa"), _row("verdadera", "verdadera")]
    metrics = ec.compute_metrics(rows)

    assert (metrics["tp"], metrics["tn"], metrics["fp"], metrics["fn"]) == (1, 1, 0, 0)
    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["evaluated"] == 2
    assert metrics["uncertain"] == 0


def test_compute_metrics_counts_directional_errors() -> None:
    rows = [
        _row("falsa", "falsa"),  # tp
        _row("falsa", "verdadera"),  # fn
        _row("verdadera", "falsa"),  # fp
        _row("verdadera", "verdadera"),  # tn
    ]
    metrics = ec.compute_metrics(rows)

    assert (metrics["tp"], metrics["fn"], metrics["fp"], metrics["tn"]) == (1, 1, 1, 1)
    assert metrics["true_to_false_rate"] == 0.5
    assert metrics["false_to_true_rate"] == 0.5
    assert metrics["accuracy"] == 0.5


def test_compute_metrics_treats_incierta_as_abstention() -> None:
    rows = [
        _row("falsa", "falsa"),  # tp
        _row("verdadera", "incierta"),  # abstención -> no puntúa
        _row("falsa", "incierta"),  # abstención -> no puntúa
    ]
    metrics = ec.compute_metrics(rows)

    assert (metrics["tp"], metrics["fn"], metrics["fp"], metrics["tn"]) == (1, 0, 0, 0)
    assert metrics["evaluated"] == 1
    assert metrics["uncertain"] == 2
    assert metrics["accuracy"] == 1.0


def test_compute_metrics_reports_nei_separately() -> None:
    rows = [
        _row("incierta", "incierta"),  # NEI correctamente abstenida
        _row("incierta", "falsa"),  # NEI con veredicto firme
        _row("verdadera", "verdadera"),
    ]
    metrics = ec.compute_metrics(rows)

    # Las muestras NEI no entran en la matriz binaria.
    assert metrics["evaluated"] == 1
    assert metrics["nei_total"] == 2
    assert metrics["nei_uncertain"] == 1


def test_compute_metrics_empty_rows_are_zero() -> None:
    metrics = ec.compute_metrics([])

    assert metrics["accuracy"] == 0.0
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1_score"] == 0.0
    assert metrics["evaluated"] == 0


def test_format_report_lists_errors_and_nei() -> None:
    rows = [
        _row("verdadera", "falsa", 0.8),
        _row("falsa", "falsa"),
        _row("incierta", "incierta"),
    ]
    metrics = ec.compute_metrics(rows)

    report = ec.format_report(metrics, rows)

    assert "Evaluación del clasificador BERT" in report
    assert "Errores de clasificación (1)" in report
    assert "NEI -> incierta        : 1/1" in report


def test_format_report_omits_error_section_when_clean() -> None:
    rows = [_row("falsa", "falsa"), _row("verdadera", "incierta")]
    metrics = ec.compute_metrics(rows)

    report = ec.format_report(metrics, rows)

    assert "Errores de clasificación" not in report
    assert "Abstenciones       : 1" in report


def test_load_samples_balances_classes_and_maps_labels(monkeypatch) -> None:
    df = pd.DataFrame(
        {
            "claim": [f"c{i}" for i in range(8)],
            # 0->verdadera, 1->falsa, 2->incierta
            "label": [0, 0, 1, 1, 2, 2, 0, 1],
        }
    )
    monkeypatch.setattr(ec, "load_dataset", lambda partition: df.copy())

    samples = ec.load_samples(partition="validation", per_class=1, seed=1)

    assert len(samples) == 3
    assert {s["expected"] for s in samples} == {"verdadera", "falsa", "incierta"}
    # La clase 'unproven' (2) nunca debe aparecer.
    assert all(s["text"] not in {"c6", "c7"} for s in samples)


def test_load_samples_skips_blank_claims(monkeypatch) -> None:
    df = pd.DataFrame({"claim": ["\xa0  ", "real claim"], "label": [0, 1]})
    monkeypatch.setattr(ec, "load_dataset", lambda partition: df.copy())

    samples = ec.load_samples(per_class=2, seed=1)

    assert all(s["text"].strip() for s in samples)


def test_evaluate_classifier_batches_and_builds_rows() -> None:
    samples: list[ec.Sample] = [
        {"text": f"claim {i}", "expected": "falsa"} for i in range(ec.BATCH_SIZE + 1)
    ]

    class FakeTool:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def predict_batch(self, texts: list[str]) -> list[dict]:
            self.calls.append(len(texts))
            return [{"label": "falsa", "confidence": 0.75} for _ in texts]

    tool = FakeTool()
    rows = ec.evaluate_classifier(samples, tool)  # type: ignore[arg-type]

    # Se respeta el tamaño de lote y se preserva la cardinalidad de entrada.
    assert tool.calls == [ec.BATCH_SIZE, 1]
    assert len(rows) == len(samples)
    assert rows[0] == {
        "text": "claim 0",
        "expected": "falsa",
        "predicted": "falsa",
        "confidence": 0.75,
    }


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
