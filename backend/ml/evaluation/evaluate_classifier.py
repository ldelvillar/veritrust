"""
Este módulo evalúa el clasificador BERT en aislamiento contra el conjunto
etiquetado de HealthVer, sin pasar por el resto del pipeline multiagente.
"""

import argparse
import logging
from time import time
from typing import TypedDict

import pandas as pd

from app.tools.model_tool import FakeNewsDetectorTool
from ml.utils.load_data import load_dataset

logger = logging.getLogger(__name__)

# Mapeo de las etiquetas numéricas de HealthVer a las clases del clasificador.
LABEL_BY_CODE = {0: "verdadera", 1: "falsa", 2: "incierta"}

BATCH_SIZE = 32


class Sample(TypedDict):
    """Una muestra etiquetada lista para evaluar."""

    text: str
    expected: str


class EvalRow(TypedDict):
    """Resultado del clasificador para una muestra, frente a su etiqueta esperada."""

    text: str
    expected: str
    predicted: str
    confidence: float


def load_samples(
    partition: str = "test", per_class: int = 300, seed: int = 42
) -> list[Sample]:
    """Carga una muestra balanceada por clase de HealthVer para la evaluación."""
    df = load_dataset(partition)
    df = df[df["label"].isin(LABEL_BY_CODE)].copy()
    df["expected"] = df["label"].map(LABEL_BY_CODE)

    frames = [
        subset.sample(n=min(per_class, len(subset)), random_state=seed)
        for _, subset in df.groupby("expected")
    ]
    sampled = pd.concat(frames)

    samples: list[Sample] = []
    for _, row in sampled.iterrows():
        text = str(row["claim"]).replace("\xa0", " ").strip()
        if text:
            samples.append({"text": text, "expected": str(row["expected"])})
    return samples


def evaluate_classifier(
    samples: list[Sample], tool: FakeNewsDetectorTool
) -> list[EvalRow]:
    """Clasifica cada muestra con el detector BERT por lotes."""
    rows: list[EvalRow] = []
    for start in range(0, len(samples), BATCH_SIZE):
        batch = samples[start : start + BATCH_SIZE]
        results = tool.predict_batch([s["text"] for s in batch])
        for sample, result in zip(batch, results):
            rows.append(
                {
                    "text": sample["text"],
                    "expected": sample["expected"],
                    "predicted": str(result["label"]),
                    "confidence": float(result["confidence"]),
                }
            )
        logger.info("Clasificadas %d/%d muestras", len(rows), len(samples))
    return rows


def compute_metrics(rows: list[EvalRow]) -> dict[str, float]:
    """Calcula métricas binarias tomando 'falsa' como positivo; 'incierta' abstiene."""
    binary = [r for r in rows if r["expected"] in ("verdadera", "falsa")]
    scored = [r for r in binary if r["predicted"] in ("verdadera", "falsa")]
    uncertain = len(binary) - len(scored)

    tp = fp = tn = fn = 0
    for row in scored:
        expected_fake = row["expected"] == "falsa"
        predicted_fake = row["predicted"] == "falsa"
        if expected_fake:
            tp += predicted_fake
            fn += not predicted_fake
        else:
            tn += not predicted_fake
            fp += predicted_fake

    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    # Las muestras 'NEI' se reportan aparte: lo deseable es que abstengan.
    nei = [r for r in rows if r["expected"] == "incierta"]
    nei_uncertain = sum(1 for r in nei if r["predicted"] == "incierta")

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "evaluated": total,
        "uncertain": uncertain,
        "true_to_false_rate": fp / (tn + fp) if (tn + fp) else 0.0,
        "false_to_true_rate": fn / (tp + fn) if (tp + fn) else 0.0,
        "nei_total": len(nei),
        "nei_uncertain": nei_uncertain,
    }


def format_report(metrics: dict[str, float], rows: list[EvalRow]) -> str:
    """Compone un informe legible con métricas y ejemplos mal clasificados."""
    lines = [
        "",
        "===== Evaluación del clasificador BERT =====",
        f"Veredictos firmes  : {int(metrics['evaluated'])}",
        f"Abstenciones       : {int(metrics['uncertain'])} ('incierta' sobre claims verdadera/falsa)",
        f"TP={int(metrics['tp'])} TN={int(metrics['tn'])} "
        f"FP={int(metrics['fp'])} FN={int(metrics['fn'])}",
        f"Accuracy  : {metrics['accuracy']:.2%}",
        f"Precision : {metrics['precision']:.2%}",
        f"Recall    : {metrics['recall']:.2%}",
        f"F1-score  : {metrics['f1_score']:.2%}",
        f"Error verdadera->falsa : {metrics['true_to_false_rate']:.2%}",
        f"Error falsa->verdadera : {metrics['false_to_true_rate']:.2%}",
    ]

    if metrics["nei_total"]:
        lines.append(
            f"NEI -> incierta        : {int(metrics['nei_uncertain'])}"
            f"/{int(metrics['nei_total'])} "
            f"({metrics['nei_uncertain'] / metrics['nei_total']:.0%})"
        )

    errors = [
        r
        for r in rows
        if r["expected"] in ("verdadera", "falsa")
        and r["predicted"] in ("verdadera", "falsa")
        and r["predicted"] != r["expected"]
    ]
    if errors:
        lines.append("")
        lines.append(f"Errores de clasificación ({len(errors)}):")
        for row in errors:
            lines.append(
                f"  esperado={row['expected']:<10} predicho={row['predicted']:<10} "
                f"conf={row['confidence']:.2f}  «{row['text'][:90]}»"
            )

    return "\n".join(lines)


def main() -> dict[str, float]:
    """Punto de entrada de script: ejecuta la evaluación e imprime el informe."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--partition",
        default="test",
        choices=["train", "test", "validation"],
        help="Partición de HealthVer a muestrear.",
    )
    parser.add_argument(
        "--per-class", type=int, default=300, help="Muestras por clase a evaluar."
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Semilla para un muestreo reproducible."
    )
    args = parser.parse_args()

    tool = FakeNewsDetectorTool()
    logger.info("Modelo: %s", tool.model_path)
    samples = load_samples(args.partition, args.per_class, args.seed)
    logger.info(
        "Evaluando %d muestras de la partición '%s'", len(samples), args.partition
    )

    start = time()
    rows = evaluate_classifier(samples, tool)
    metrics = compute_metrics(rows)

    print(format_report(metrics, rows))
    logger.info("Tiempo total: %.1f s", time() - start)
    return metrics


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    main()
