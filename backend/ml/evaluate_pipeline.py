"""
Este módulo evalúa el pipeline multiagente completo contra un
conjunto etiquetado de HealthVer y reporta métricas de clasificación.
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from time import time
from typing import TypedDict, cast

import pandas as pd

from app.agents.errors import ainvoke_graph
from app.agents.main import create_graph, describe_pipeline
from app.core.credibility import EVIDENCE_MAX_PENALTY, classify_verdict
from app.prompts.agents import Prompts, load_prompts
from app.utils.llm import ensure_llm_available
from ml.load_data import load_dataset

logger = logging.getLogger(__name__)

# Mapeo de HealthVer a las binarias del sistema; NEI (2) queda fuera de la métrica.
LABEL_BY_CODE = {0: "verdadera", 1: "falsa"}


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
    fake_avg: float | None
    duration_seconds: float
    extracted: list[str]
    translated: list[str]
    sources_kept: int
    stances: dict[str, int]
    evidence_coverage: float
    judge_failures: int


def _stance_histogram(sources: list[dict]) -> dict[str, int]:
    """Cuenta las posturas asignadas a las fuentes que sobrevivieron al juez."""
    counts: dict[str, int] = {}
    for source in sources:
        for statement in source.get("statements") or []:
            stance = str(statement.get("stance"))
            counts[stance] = counts.get(stance, 0) + 1
    return counts


def load_samples(
    partition: str = "test", limit: int = 30, seed: int = 42
) -> list[Sample]:
    """Carga una muestra binaria y balanceada de HealthVer para la evaluación."""
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


def _reconstruct_fake_avg(
    label: str | None, confidence: float, coverage: float
) -> float | None:
    """Invierte la atenuación por cobertura para recuperar la fake_avg que vio la banda."""
    if not label:
        return None
    cov = max(0.0, min(1.0, coverage))
    raw = min(1.0, confidence / (1 - EVIDENCE_MAX_PENALTY * (1 - cov)))
    return round(raw if label == "falsa" else 1.0 - raw, 6)


def load_checkpoint(path: Path) -> dict[str, EvalRow]:
    """Lee las filas ya evaluadas de un checkpoint JSONL; vacío si no existe."""
    done: dict[str, EvalRow] = {}
    if not path.exists():
        return done
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                # Línea corrupta (p. ej. crash a media escritura): se ignora.
                continue
            if isinstance(row, dict) and "text" in row:
                done[row["text"]] = cast(EvalRow, row)
    return done


# Lo que decide las filas: reanudar con otro valor mezclaría configuraciones bajo una cabecera.
_RUN_IDENTITY_KEYS = ("provider", "models", "prompts")


class CheckpointMismatchError(ValueError):
    """El checkpoint se generó con otra configuración o no la registra."""


def _git_describe() -> str | None:
    """Commit del código evaluado, con -dirty si hay cambios sin commitear; None sin git."""
    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def describe_run(prompts: Prompts, *, partition: str, seed: int) -> dict:
    """Resume la configuración del pipeline que produce las filas de un checkpoint."""
    return {
        **describe_pipeline(prompts),
        "partition": partition,
        "seed": seed,
        "git": _git_describe(),
    }


def read_checkpoint_run(path: Path) -> dict | None:
    """Devuelve la configuración registrada en la cabecera del checkpoint, si la hay."""
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict) and isinstance(record.get("run"), dict):
                return record["run"]
    return None


def prepare_checkpoint(path: Path, run: dict) -> dict:
    """Escribe la cabecera de un checkpoint nuevo o verifica que se reanuda con la misma configuración."""
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        path.write_text(
            json.dumps({"run": run}, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return run
    recorded = read_checkpoint_run(path)
    if recorded is None or any(recorded.get(k) != run[k] for k in _RUN_IDENTITY_KEYS):
        raise CheckpointMismatchError(
            f"El checkpoint {path} se generó con otra configuración o no la registra; "
            "usa --fresh u otro --checkpoint para no mezclar resultados."
        )
    return recorded


async def evaluate_pipeline(
    samples: list[Sample], graph: object, checkpoint_path: Path | None = None
) -> list[EvalRow]:
    """Ejecuta el grafo sobre cada muestra, con checkpoint y reanudación opcionales."""
    done: dict[str, EvalRow] = (
        load_checkpoint(checkpoint_path) if checkpoint_path else {}
    )
    pending = [s for s in samples if s["text"] not in done]
    total = len(pending)
    if done:
        logger.info("Reanudando: %d ya evaluadas, %d pendientes", len(done), total)

    # Solo se persisten muestras completadas; una que falla se reintenta al reanudar.
    handle = checkpoint_path.open("a", encoding="utf-8") if checkpoint_path else None
    try:
        for i, sample in enumerate(pending, start=1):
            started = time()
            try:
                result = await ainvoke_graph(
                    graph, _build_initial_state(sample["text"])
                )
            except Exception:
                logger.exception(
                    "[%d/%d] fallo al analizar; se reintentará al reanudar", i, total
                )
                continue
            duration = time() - started

            # Sin etiqueta: el texto no contenía afirmaciones médicas verificables.
            predicted = result.get("label") or None
            confidence = float(result.get("confidence") or 0.0)
            row: EvalRow = {
                "text": sample["text"],
                "expected": sample["expected"],
                "predicted": predicted,
                "confidence": confidence,
                # fake_avg cruda para poder barrer la banda global sin re-ejecutar.
                "fake_avg": _reconstruct_fake_avg(
                    predicted,
                    confidence,
                    float(result.get("evidence_coverage") or 0.0),
                ),
                # Coste por muestra: fija el n asumible en evaluaciones posteriores.
                "duration_seconds": round(duration, 3),
                # Permite detectar inversiones de polaridad extractor/traductor.
                "extracted": [str(x) for x in result.get("extracted_statements") or []],
                "translated": [
                    str(x) for x in result.get("translated_statements") or []
                ],
                # Diagnóstico: separa "no se recuperó nada" de "el juez no se moja".
                "sources_kept": len(result.get("sources") or []),
                "stances": _stance_histogram(result.get("sources") or []),
                "evidence_coverage": float(result.get("evidence_coverage") or 0.0),
                # Juez caido: la fila no mide el pipeline, mide una incidencia.
                "judge_failures": int(result.get("judge_failures") or 0),
            }
            done[sample["text"]] = row
            if handle is not None:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
            logger.info(
                "[%d/%d] esperado=%s predicho=%s (%.1f s)",
                i,
                total,
                sample["expected"],
                predicted or "sin_afirmaciones",
                duration,
            )
    finally:
        if handle is not None:
            handle.close()

    # Filas de las muestras de esta ejecución, en orden; las fallidas quedan fuera.
    return [done[s["text"]] for s in samples if s["text"] in done]


def _is_abstention(predicted: str | None) -> bool:
    """Sin afirmaciones (None) o veredicto no firme ('incierta') no puntúan."""
    return predicted is None or classify_verdict(predicted) == "uncertain"


def compute_metrics(rows: list[EvalRow]) -> dict[str, float]:
    """Calcula la matriz de confusión y métricas tomando 'falsa' como positivo."""
    # Con el juez caido no hay posturas: la fila no mide nada y se excluye.
    invalid = [r for r in rows if r.get("judge_failures")]
    valid = [r for r in rows if not r.get("judge_failures")]

    # Abstenerse ('incierta') es seguro, no un error: se excluye de las métricas.
    scored = [r for r in valid if not _is_abstention(r["predicted"])]
    skipped = sum(1 for r in valid if r["predicted"] is None)
    uncertain = len(valid) - len(scored) - skipped

    tp = fp = tn = fn = 0
    for row in scored:
        expected_fake = row["expected"] == "falsa"
        predicted_fake = classify_verdict(row["predicted"]) == "fake"
        if expected_fake:
            tp += predicted_fake
            fn += not predicted_fake
        else:
            tn += not predicted_fake
            fp += predicted_fake

    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total else 0.0
    # Cobertura: veredictos firmes sobre las muestras que sí tenían afirmaciones.
    coverage = total / (total + uncertain) if (total + uncertain) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "accuracy": accuracy,
        "coverage": coverage,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "evaluated": total,
        "uncertain": uncertain,
        "skipped": skipped,
        "judge_failed": len(invalid),
    }


def _format_run(run: dict) -> list[str]:
    """Líneas del informe que atribuyen las métricas a la configuración que las produjo."""
    models = ", ".join(f"{role}={name}" for role, name in run["models"].items())
    prompts = ", ".join(f"{name}={version}" for name, version in run["prompts"].items())
    return [
        f"Proveedor : {run['provider']} · git {run.get('git') or 'desconocido'}",
        f"Partición : {run['partition']} (seed {run['seed']})",
        f"Modelos   : {models}",
        f"Prompts   : {prompts}",
    ]


def format_report(
    metrics: dict[str, float], rows: list[EvalRow], run: dict | None = None
) -> str:
    """Compone un informe legible con métricas y ejemplos mal clasificados."""
    lines = [
        "",
        "===== Evaluación del pipeline multiagente =====",
        *(_format_run(run) if run else []),
        f"Muestras evaluadas : {int(metrics['evaluated'])}",
        f"Veredicto incierto : {int(metrics['uncertain'])} (abstención, excluida de las métricas)",
        f"Sin afirmaciones   : {int(metrics['skipped'])} (excluidas de las métricas)",
        f"Juez caído         : {int(metrics['judge_failed'])} "
        "(evidencia sin juzgar, excluidas de las métricas)",
        f"TP={int(metrics['tp'])} TN={int(metrics['tn'])} "
        f"FP={int(metrics['fp'])} FN={int(metrics['fn'])}",
        f"Accuracy  : {metrics['accuracy']:.2%}",
        f"Cobertura : {metrics['coverage']:.2%} (veredictos firmes / muestras con afirmaciones)",
        f"Precision : {metrics['precision']:.2%}",
        f"Recall    : {metrics['recall']:.2%}",
        f"F1-score  : {metrics['f1_score']:.2%}",
    ]

    # Solo cuentan como error los veredictos firmes que discrepan de lo esperado.
    errors = [
        r
        for r in rows
        if not r.get("judge_failures")
        if not _is_abstention(r["predicted"])
        and (classify_verdict(r["predicted"]) == "fake") != (r["expected"] == "falsa")
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
        choices=["train", "test", "validation", "gold"],
        help="Partición de HealthVer a muestrear.",
    )
    parser.add_argument(
        "--limit", type=int, default=30, help="Número de muestras a evaluar."
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Semilla para un muestreo reproducible."
    )
    parser.add_argument(
        "--checkpoint",
        default=None,
        help="Ruta del checkpoint JSONL (por defecto results/eval_pipeline_<partición>.jsonl).",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignora cualquier checkpoint previo y evalúa desde cero.",
    )
    parser.add_argument(
        "--with-explanation",
        action="store_true",
        help="Genera el informe del experto; por defecto se omite porque no decide la etiqueta.",
    )
    args = parser.parse_args()

    # El informe es ~1/3 de los tokens por muestra y no influye en la métrica.
    if not args.with_explanation:
        os.environ["HEALTH_EXPERT_EXPLANATION_ENABLED"] = "false"

    # results/ está git-ignored; el checkpoint permite reanudar una evaluación larga.
    default_dir = Path(__file__).resolve().parents[1] / "results"
    checkpoint_path = (
        Path(args.checkpoint)
        if args.checkpoint
        else default_dir / f"eval_pipeline_{args.partition}.jsonl"
    )
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    if args.fresh:
        checkpoint_path.unlink(missing_ok=True)

    ensure_llm_available()

    prompts = load_prompts()
    try:
        run = prepare_checkpoint(
            checkpoint_path,
            describe_run(prompts, partition=args.partition, seed=args.seed),
        )
    except CheckpointMismatchError as exc:
        raise SystemExit(str(exc)) from exc

    graph = create_graph(prompts)
    samples = load_samples(args.partition, args.limit, args.seed)
    logger.info(
        "Evaluando %d muestras de la partición '%s'", len(samples), args.partition
    )

    start = time()
    rows = asyncio.run(evaluate_pipeline(samples, graph, checkpoint_path))
    metrics = compute_metrics(rows)

    print(format_report(metrics, rows, run))
    failed = len(samples) - len(rows)
    if failed:
        logger.warning(
            "%d muestras fallaron y no se evaluaron; vuelve a ejecutar para reintentarlas.",
            failed,
        )
    logger.info("Checkpoint: %s", checkpoint_path)
    logger.info("Tiempo total: %.1f s", time() - start)
    return metrics


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    main()
