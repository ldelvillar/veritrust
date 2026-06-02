"""
Este módulo evalúa el pipeline multiagente completo contra un
conjunto etiquetado de PubHealth y reporta métricas de clasificación.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from time import time
from typing import TypedDict

# Asegurar que al ejecutar este archivo como script, se use el código local del repositorio.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from app.agents.errors import ainvoke_graph
from app.agents.health_expert import ensure_bert_detector_ready
from app.agents.main import create_graph
from app.prompts.agents import load_prompts
from app.utils.ollama import ensure_ollama_available
from ml.utils.load_data import load_dataset

logger = logging.getLogger(__name__)

# Mapeo de las etiquetas numéricas de PubHealth a las binarias del sistema.
LABEL_BY_CODE = {0: "verdadera", 1: "falsa", 3: "falsa"}


class Sample(TypedDict):
    """Una muestra etiquetada lista para evaluar."""

    text: str
    expected: str


class EvalRow(TypedDict):
    """Resultado del pipeline para una muestra, frente a su etiqueta esperada."""

    text: str
    expected: str
    predicted: str | None
    confidence: float


def load_samples(
    partition: str = "validation", limit: int = 30, seed: int = 42
) -> list[Sample]:
    """Carga una muestra binaria y balanceada de PubHealth para la evaluación."""
    df = load_dataset(partition)
    df = df[df["label"].isin(LABEL_BY_CODE)].copy()
    df["expected"] = df["label"].map(LABEL_BY_CODE)

    # Muestrear a partes iguales de cada clase para no sesgar las métricas.
    per_class = max(1, limit // 2)
    frames = [
        subset.sample(n=min(per_class, len(subset)), random_state=seed)
        for _, subset in df.groupby("expected")
    ]
    sampled = pd.concat(frames).sample(frac=1, random_state=seed).head(limit)

    samples: list[Sample] = []
    for _, row in sampled.iterrows():
        text = str(row["claim"]).replace("\xa0", " ").strip()
        if text:
            samples.append({"text": text, "expected": str(row["expected"])})
    return samples


def _build_initial_state(text: str) -> dict[str, object]:
    """Construye el estado inicial del grafo para un texto de entrada."""
    return {
        "input_text": text,
        "extracted_statements": [],
        "translated_statements": [],
        "label": "",
        "confidence": 0.0,
        "medical_explanation": "",
    }


async def evaluate_pipeline(samples: list[Sample], graph: object) -> list[EvalRow]:
    """Ejecuta el grafo completo sobre cada muestra y devuelve sus predicciones."""
    rows: list[EvalRow] = []
    total = len(samples)
    for i, sample in enumerate(samples, start=1):
        result = await ainvoke_graph(graph, _build_initial_state(sample["text"]))
        label = result.get("label") or None
        explanation = result.get("medical_explanation") or None

        # Sin explicación: el texto no contenía afirmaciones médicas verificables.
        predicted = label if (label and explanation) else None
        rows.append(
            {
                "text": sample["text"],
                "expected": sample["expected"],
                "predicted": predicted,
                "confidence": float(result.get("confidence") or 0.0),
            }
        )
        logger.info(
            "[%d/%d] esperado=%s predicho=%s",
            i,
            total,
            sample["expected"],
            predicted or "sin_afirmaciones",
        )
    return rows


def compute_metrics(rows: list[EvalRow]) -> dict[str, float]:
    """Calcula la matriz de confusión y métricas tomando 'falsa' como positivo."""
    scored = [r for r in rows if r["predicted"] is not None]
    skipped = len(rows) - len(scored)

    tp = fp = tn = fn = 0
    for row in scored:
        expected, predicted = row["expected"], row["predicted"]
        if expected == "falsa":
            tp += predicted == "falsa"
            fn += predicted != "falsa"
        else:
            tn += predicted == "verdadera"
            fp += predicted != "verdadera"

    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

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
        "skipped": skipped,
    }


def format_report(metrics: dict[str, float], rows: list[EvalRow]) -> str:
    """Compone un informe legible con métricas y ejemplos mal clasificados."""
    lines = [
        "",
        "===== Evaluación del pipeline multiagente =====",
        f"Muestras evaluadas : {int(metrics['evaluated'])}",
        f"Sin afirmaciones   : {int(metrics['skipped'])} (excluidas de las métricas)",
        f"TP={int(metrics['tp'])} TN={int(metrics['tn'])} "
        f"FP={int(metrics['fp'])} FN={int(metrics['fn'])}",
        f"Accuracy  : {metrics['accuracy']:.2%}",
        f"Precision : {metrics['precision']:.2%}",
        f"Recall    : {metrics['recall']:.2%}",
        f"F1-score  : {metrics['f1_score']:.2%}",
    ]

    errors = [
        r
        for r in rows
        if r["predicted"] is not None and r["predicted"] != r["expected"]
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
        default="validation",
        choices=["train", "test", "validation"],
        help="Partición de PubHealth a muestrear.",
    )
    parser.add_argument(
        "--limit", type=int, default=30, help="Número de muestras a evaluar."
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Semilla para un muestreo reproducible."
    )
    args = parser.parse_args()

    ensure_ollama_available()
    ensure_bert_detector_ready()

    graph = create_graph(load_prompts())
    samples = load_samples(args.partition, args.limit, args.seed)
    logger.info(
        "Evaluando %d muestras de la partición '%s'", len(samples), args.partition
    )

    start = time()
    rows = asyncio.run(evaluate_pipeline(samples, graph))
    metrics = compute_metrics(rows)

    print(format_report(metrics, rows))
    logger.info("Tiempo total: %.1f s", time() - start)
    return metrics


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    main()
