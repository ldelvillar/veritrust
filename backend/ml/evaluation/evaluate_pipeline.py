"""
Este módulo evalúa el pipeline multiagente completo contra un
conjunto etiquetado de HealthVer y reporta métricas de clasificación.
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from time import time
from typing import TypedDict, cast

import pandas as pd
import yaml
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from app.agents.errors import ainvoke_graph
from app.agents.health_expert import ensure_bert_detector_ready
from app.agents.main import create_graph
from app.core.config import get_settings
from app.core.credibility import EVIDENCE_MAX_PENALTY, classify_verdict
from app.prompts.agents import load_prompts
from app.utils.ollama import ensure_ollama_available
from ml.utils.load_data import load_dataset

logger = logging.getLogger(__name__)

# Mapeo de HealthVer a las binarias del sistema; NEI (2) queda fuera de la métrica.
LABEL_BY_CODE = {0: "verdadera", 1: "falsa"}

# Prompt del filtro de dominio; propio de la evaluación, fuera del contrato de la app.
PROMPTS_PATH = Path(__file__).parent / "prompts.yaml"

# Candidatos a muestrear por cada muestra pedida cuando se filtra por dominio.
MEDICAL_POOL_FACTOR = 4


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


class MedicalJudgment(BaseModel):
    """Si el texto contiene al menos una afirmación médica verificable."""

    is_medical: bool = Field(
        description="true si el texto contiene una afirmación médica o de salud verificable"
    )


def _build_medical_filter_chain():
    """Construye la cadena sí/no que juzga si una muestra es del dominio médico."""
    with PROMPTS_PATH.open(encoding="utf-8") as handle:
        prompt_text = str(yaml.safe_load(handle)["medical_filter"]["text"])
    settings = get_settings()
    llm = ChatOllama(
        model=settings.ollama_judge_model,
        temperature=0,
        base_url=settings.ollama_base_url,
        num_ctx=settings.ollama_judge_num_ctx,
        num_predict=settings.ollama_judge_num_predict,
        client_kwargs={"timeout": settings.ollama_request_timeout_seconds},
    ).with_structured_output(MedicalJudgment)
    prompt = ChatPromptTemplate.from_messages(
        [("system", prompt_text), ("user", "Texto:\n{claim}")]
    )
    return prompt | llm


def filter_medical_samples(samples: list[Sample], chain, limit: int) -> list[Sample]:
    """Conserva, en orden y por clase, hasta ``limit`` muestras del dominio médico."""
    per_class = max(1, limit // 2)
    kept: list[Sample] = []
    by_class: dict[str, int] = {}
    judged = 0
    for sample in samples:
        if by_class.get(sample["expected"], 0) >= per_class:
            continue
        judged += 1
        try:
            is_medical = bool(chain.invoke({"claim": sample["text"]}).is_medical)
        except Exception:
            # Falla en abierto: ante un error del juez la muestra se conserva.
            logger.warning("Fallo juzgando el dominio; se conserva la muestra")
            is_medical = True
        if is_medical:
            kept.append(sample)
            by_class[sample["expected"]] = by_class.get(sample["expected"], 0) + 1
            if len(kept) >= per_class * 2:
                break
    logger.info("Filtro médico: %d juzgadas, %d conservadas", judged, len(kept))
    return kept


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

            label = result.get("label") or None
            explanation = result.get("medical_explanation") or None
            # Sin explicación: el texto no contenía afirmaciones médicas verificables.
            predicted = label if (label and explanation) else None
            confidence = float(result.get("confidence") or 0.0)
            row: EvalRow = {
                "text": sample["text"],
                "expected": sample["expected"],
                "predicted": predicted,
                "confidence": confidence,
                # fake_avg cruda para poder barrer la banda global sin re-ejecutar.
                "fake_avg": _reconstruct_fake_avg(
                    label, confidence, float(result.get("evidence_coverage") or 0.0)
                ),
                # Coste por muestra: fija el n asumible en evaluaciones posteriores.
                "duration_seconds": round(duration, 3),
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
    # Abstenerse ('incierta') es seguro, no un error: se excluye de las métricas.
    scored = [r for r in rows if not _is_abstention(r["predicted"])]
    skipped = sum(1 for r in rows if r["predicted"] is None)
    uncertain = len(rows) - len(scored) - skipped

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
    }


def format_report(metrics: dict[str, float], rows: list[EvalRow]) -> str:
    """Compone un informe legible con métricas y ejemplos mal clasificados."""
    lines = [
        "",
        "===== Evaluación del pipeline multiagente =====",
        f"Muestras evaluadas : {int(metrics['evaluated'])}",
        f"Veredicto incierto : {int(metrics['uncertain'])} (abstención, excluida de las métricas)",
        f"Sin afirmaciones   : {int(metrics['skipped'])} (excluidas de las métricas)",
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
        choices=["train", "test", "validation"],
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
        "--medical-only",
        action="store_true",
        help="Filtra el muestreo a textos con afirmación médica verificable (juez LLM).",
    )
    args = parser.parse_args()

    # results/ está git-ignored; el checkpoint permite reanudar una evaluación larga.
    default_dir = Path(__file__).resolve().parents[2] / "results"
    checkpoint_path = (
        Path(args.checkpoint)
        if args.checkpoint
        else default_dir / f"eval_pipeline_{args.partition}.jsonl"
    )
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    if args.fresh:
        checkpoint_path.unlink(missing_ok=True)

    ensure_ollama_available()
    ensure_bert_detector_ready()

    graph = create_graph(load_prompts())
    pool = args.limit * MEDICAL_POOL_FACTOR if args.medical_only else args.limit
    samples = load_samples(args.partition, pool, args.seed)
    if args.medical_only:
        samples = filter_medical_samples(
            samples, _build_medical_filter_chain(), args.limit
        )
    logger.info(
        "Evaluando %d muestras de la partición '%s'", len(samples), args.partition
    )

    start = time()
    rows = asyncio.run(evaluate_pipeline(samples, graph, checkpoint_path))
    metrics = compute_metrics(rows)

    print(format_report(metrics, rows))
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
