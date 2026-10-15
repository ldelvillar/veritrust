"""
Este módulo evalúa solo el juez de evidencia: vuelve a juzgar las afirmaciones y fuentes
candidatas grabadas en un checkpoint del pipeline, para comparar modelos de juez sobre
la misma entrada sin ejecutar el resto del pipeline.

El proveedor y el modelo del juez se eligen como en el pipeline, por entorno; p. ej.
``LLM_PROVIDER=mistral`` o ``OLLAMA_JUDGE_MODEL=gemma4:12b``.
"""

import argparse
import json
import logging
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import TypedDict, cast

from app.agents.relevance import judge_stances
from app.core.claim import Claim, evidence_search, with_hits, with_stances
from app.core.config import get_settings
from app.core.verdict import decide, kind_of
from app.prompts.agents import load_prompts
from app.utils.llm import configured_models, ensure_llm_available
from evaluation.evaluate_pipeline import (
    CheckpointMismatchError,
    git_describe,
    load_checkpoint,
    prepare_checkpoint,
)

logger = logging.getLogger(__name__)

# Orden en que el investigador reúne los resultados de las fuentes de una afirmación.
_SOURCE_ORDER = ("europepmc", "pubmed", "openfda", "cima")

_LABELS = ("verdadera", "falsa")

_FIRM = ("supports", "contradicts")


@dataclass(frozen=True)
class JudgeCase:
    """Una muestra grabada: su etiqueta y su afirmación con las fuentes candidatas que vio el juez."""

    text: str
    expected: str
    claim: Claim


class JudgedSource(TypedDict):
    """Postura que dio el juez a una fuente candidata."""

    url: str
    stance: str


class JudgeRow(TypedDict):
    """Respuesta del juez para un caso y el veredicto que decide con ella."""

    text: str
    claim: str
    expected: str
    sources: list[JudgedSource]
    predicted: str


@dataclass(frozen=True)
class StanceLabel:
    """Postura correcta de una fuente para una afirmación, etiquetada a mano."""

    claim: str
    url: str
    label: str
    stance: str
    reason: str


def load_cases(path: Path) -> list[JudgeCase]:
    """Casos de un checkpoint del pipeline: las muestras de una afirmación traducida con alguna fuente candidata."""
    cases: list[JudgeCase] = []
    rows = list(load_checkpoint(path).values())
    for row in rows:
        translated = row.get("translated") or []
        # Con varias afirmaciones la fila no dice qué búsquedas son de cuál.
        if len(translated) != 1 or not translated[0] or "evidence" not in row:
            continue
        calls = sorted(
            (call for call in row["evidence"] if call["hits"] is not None),
            key=lambda call: _SOURCE_ORDER.index(call["source"]),
        )
        found = with_hits(
            Claim(index=0, text=row["extracted"][0], text_en=translated[0]),
            [hit for call in calls for hit in call["hits"] or []],
        )
        if found.evidence:
            cases.append(
                JudgeCase(text=row["text"], expected=row["expected"], claim=found)
            )
    logger.info("%d casos de %d muestras grabadas", len(cases), len(rows))
    return cases


def judge_cases(
    cases: list[JudgeCase],
    prompt_text: str,
    checkpoint_path: Path,
    minutes: float | None = None,
) -> list[JudgeRow]:
    """Juzga los casos sin fila en el checkpoint; uno sin respuesta no se guarda y se reintenta al reanudar."""
    done = cast(dict[str, JudgeRow], load_checkpoint(checkpoint_path))
    pending = [case for case in cases if case.text not in done]
    deadline = time() + minutes * 60 if minutes else None
    with checkpoint_path.open("a", encoding="utf-8") as handle:
        for i, case in enumerate(pending, start=1):
            # Un presupuesto de tiempo deja la corrida en un punto del que se reanuda.
            if deadline is not None and time() > deadline:
                logger.info(
                    "Presupuesto agotado con %d casos pendientes", len(pending) - i + 1
                )
                break
            stances = judge_stances(
                prompt_text, case.claim.text_en, case.claim.evidence
            )
            # Sin respuesta puede ser el modelo o la conexión: no se guarda como juicio.
            if stances is None:
                logger.warning(
                    "[%d/%d] el juez no respondió; se reintentará", i, len(pending)
                )
                continue
            judged = with_stances(case.claim, stances)
            verdict = decide([judged], evidence_search([judged]))
            row: JudgeRow = {
                "text": case.text,
                "claim": case.claim.text,
                "expected": case.expected,
                "sources": [
                    {"url": item.url, "stance": stance}
                    for item, stance in zip(case.claim.evidence, stances, strict=True)
                ],
                "predicted": verdict.label,
            }
            done[case.text] = row
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            logger.info(
                "[%d/%d] esperado=%s predicho=%s",
                i,
                len(pending),
                case.expected,
                verdict.label,
            )
    return [done[case.text] for case in cases if case.text in done]


def compute_judge_metrics(rows: list[JudgeRow]) -> dict:
    """Aciertos sobre veredictos firmes y reparto de posturas según la etiqueta real."""
    firm = [row for row in rows if kind_of(row["predicted"]) != "uncertain"]
    correct = sum(row["predicted"] == row["expected"] for row in firm)
    return {
        "judged": len(rows),
        "firm": len(firm),
        "correct": correct,
        "accuracy": correct / len(firm) if firm else 0.0,
        "false_as_true": sum(
            row["expected"] == "falsa" and row["predicted"] == "verdadera"
            for row in firm
        ),
        "true_as_false": sum(
            row["expected"] == "verdadera" and row["predicted"] == "falsa"
            for row in firm
        ),
        "stances": {
            label: Counter(
                source["stance"]
                for row in rows
                if row["expected"] == label
                for source in row["sources"]
            )
            for label in _LABELS
        },
    }


def load_stance_labels(path: Path) -> list[StanceLabel]:
    """Lee las posturas etiquetadas a mano de un JSONL, una por par afirmación-fuente."""
    with path.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    return [
        StanceLabel(
            claim=record["claim"],
            url=record["url"],
            label=record["label"],
            stance=record["stance"],
            reason=record["reason"],
        )
        for record in records
    ]


def score_stances(rows: list[JudgeRow], labels: list[StanceLabel]) -> dict:
    """Compara las posturas del juez con las etiquetadas: firmes sin base, descartes de más y polaridad invertida."""
    judged = {
        (row["claim"], source["url"]): source["stance"]
        for row in rows
        for source in row["sources"]
    }
    scored = [
        (label, judged[(label.claim, label.url)])
        for label in labels
        if (label.claim, label.url) in judged
    ]
    loose = [
        (label, stance)
        for label, stance in scored
        if stance in _FIRM and label.stance not in _FIRM
    ]
    return {
        "labels": len(labels),
        "scored": len(scored),
        "judge_firm": sum(stance in _FIRM for _, stance in scored),
        "loose": len(loose),
        # Las que empujan hacia el veredicto equivocado de su afirmación.
        "loose_wrong_way": sum(
            (label.label, stance)
            in (("verdadera", "contradicts"), ("falsa", "supports"))
            for label, stance in loose
        ),
        "loose_reasons": Counter(label.reason for label, _ in loose),
        "gold_firm": sum(label.stance in _FIRM for label, _ in scored),
        "strict": sum(
            label.stance in _FIRM and stance not in _FIRM for label, stance in scored
        ),
        "polarity": sum(
            label.stance in _FIRM and stance in _FIRM and stance != label.stance
            for label, stance in scored
        ),
    }


def format_stance_report(scores: dict) -> str:
    """Compone el informe de posturas frente a las etiquetadas a mano."""

    def share(part: int, whole: int) -> str:
        return f"{part}/{whole} ({part / whole:.1%})" if whole else f"{part}/0"

    reasons = " · ".join(
        f"{reason} {n}" for reason, n in scores["loose_reasons"].most_common()
    )
    return "\n".join(
        [
            "",
            f"Posturas etiquetadas: {scores['scored']}/{scores['labels']} puntuadas",
            f"  Firmes sin base     : {share(scores['loose'], scores['judge_firm'])}"
            f" · {scores['loose_wrong_way']} hacia el veredicto equivocado",
            f"    por motivo        : {reasons or '-'}",
            f"  Descartes de más    : {share(scores['strict'], scores['gold_firm'])}",
            f"  Polaridad invertida : {scores['polarity']}",
        ]
    )


def format_judge_report(metrics: dict, run: dict, cases: int) -> str:
    """Compone el informe del juez: la configuración, los veredictos y el reparto de posturas."""
    lines = [
        "",
        "===== Evaluación del juez =====",
        f"Proveedor : {run['provider']} · git {run.get('git') or 'desconocido'}",
        f"Juez      : {run['models']['judge']} · prompt {run['prompts']['judge']}",
        f"Casos     : {', '.join(Path(p).name for p in run['replay_evidence'])}",
        f"Juzgados  : {metrics['judged']}/{cases}",
        f"Firmes    : {metrics['firm']} · aciertos {metrics['correct']} "
        f"({metrics['accuracy']:.1%})",
        f"falsa→verdadera {metrics['false_as_true']} · "
        f"verdadera→falsa {metrics['true_as_false']}",
        "",
        "Posturas por etiqueta real (s:c = supports por contradicts):",
    ]
    for label, counts in metrics["stances"].items():
        supports, contradicts = counts["supports"], counts["contradicts"]
        ratio = f"{supports / contradicts:.2f}" if contradicts else "∞"
        lines.append(
            f"  {label:<10} supports {supports:>4} · contradicts {contradicts:>4} · "
            f"inconclusive {counts['inconclusive']:>4} · unrelated {counts['unrelated']:>4}"
            f" · s:c {ratio}"
        )
    return "\n".join(lines)


def main() -> dict:
    """Punto de entrada de script: juzga los casos grabados e imprime el informe."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        required=True,
        nargs="+",
        metavar="CKPT",
        help="Checkpoints del pipeline con la evidencia bruta grabada que se vuelve a juzgar.",
    )
    parser.add_argument(
        "--checkpoint", required=True, help="Ruta del checkpoint JSONL de esta corrida."
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignora cualquier checkpoint previo y juzga desde cero.",
    )
    parser.add_argument(
        "--minutes",
        type=float,
        default=None,
        help="Deja de empezar casos pasado este tiempo; la corrida se reanuda después.",
    )
    parser.add_argument(
        "--stance-labels",
        default=None,
        metavar="JSONL",
        help="Posturas etiquetadas a mano con las que puntuar cada fuente juzgada.",
    )
    args = parser.parse_args()

    cases_paths = [Path(path).resolve() for path in args.cases]
    checkpoint_path = Path(args.checkpoint)
    if checkpoint_path.resolve() in cases_paths:
        raise SystemExit("--cases debe apuntar a otros checkpoints que --checkpoint.")
    cases = [case for path in cases_paths for case in load_cases(path)]
    if not cases:
        raise SystemExit(
            "Los checkpoints de --cases no existen o no tienen casos de una afirmación."
        )
    labels = (
        load_stance_labels(Path(args.stance_labels)) if args.stance_labels else None
    )

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    if args.fresh:
        checkpoint_path.unlink(missing_ok=True)

    ensure_llm_available()

    prompts = load_prompts()
    # Lo que decide las posturas: reanudar con otro juez mezclaría resultados.
    run = {
        "provider": get_settings().llm_provider_name(),
        "models": {"judge": configured_models()["judge"]},
        "prompts": {"judge": prompts.judge.version},
        "replay_evidence": [str(path) for path in cases_paths],
        "git": git_describe(),
    }
    try:
        run = prepare_checkpoint(checkpoint_path, run)
    except CheckpointMismatchError as exc:
        raise SystemExit(str(exc)) from exc

    rows = judge_cases(cases, prompts.judge.text, checkpoint_path, args.minutes)
    metrics = compute_judge_metrics(rows)
    print(format_judge_report(metrics, run, len(cases)))
    if labels is not None:
        metrics["stance_labels"] = score_stances(rows, labels)
        print(format_stance_report(metrics["stance_labels"]))
    return metrics


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    main()
