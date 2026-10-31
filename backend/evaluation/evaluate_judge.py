"""Rejudge the claims and candidate Sources recorded in a pipeline checkpoint, without running the rest of the pipeline, to compare judge models chosen by env as in the pipeline (e.g. ``LLM_PROVIDER=mistral`` or ``OLLAMA_JUDGE_MODEL=gemma4:12b``)."""

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

# Order in which the investigator gathers a claim's source results.
_SOURCE_ORDER = ("europepmc", "pubmed", "openfda", "cima")

_LABELS = ("verdadera", "falsa")

_FIRM = ("supports", "contradicts")


@dataclass(frozen=True)
class JudgeCase:
    """A recorded sample, its label and its claim with the candidate Sources the judge saw."""

    text: str
    expected: str
    claim: Claim


class JudgedSource(TypedDict):
    """Stance the judge gave a candidate Source."""

    url: str
    stance: str


class JudgeRow(TypedDict):
    """The judge's answer for a case and the Verdict it decides with it."""

    text: str
    claim: str
    expected: str
    sources: list[JudgedSource]
    predicted: str


@dataclass(frozen=True)
class StanceLabel:
    """Correct Stance of a Source for a claim, labelled by hand."""

    claim: str
    url: str
    label: str
    stance: str
    reason: str


def load_cases(path: Path) -> list[JudgeCase]:
    """Cases of a pipeline checkpoint, the samples of one translated claim with some candidate Source."""
    cases: list[JudgeCase] = []
    rows = list(load_checkpoint(path).values())
    for row in rows:
        translated = row.get("translated") or []
        # With several claims the row does not say which searches belong to which.
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
    """Judge the cases without a checkpoint row, where an unanswered one is not saved and is retried on resume."""
    done = cast(dict[str, JudgeRow], load_checkpoint(checkpoint_path))
    pending = [case for case in cases if case.text not in done]
    deadline = time() + minutes * 60 if minutes else None
    with checkpoint_path.open("a", encoding="utf-8") as handle:
        for i, case in enumerate(pending, start=1):
            # A time budget leaves the run at a point it resumes from.
            if deadline is not None and time() > deadline:
                logger.info(
                    "Presupuesto agotado con %d casos pendientes", len(pending) - i + 1
                )
                break
            stances = judge_stances(
                prompt_text, case.claim.text_en, case.claim.evidence
            )
            # No answer may be the model or the connection, so it is not saved as a judgment.
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
    """Hits on firm Verdicts and the spread of Stances by the real label."""
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
    """Read the hand-labelled Stances from a JSONL, one per claim and Source pair."""
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
    """Compare the judge's Stances with the labelled ones: unfounded firm ones, extra discards and inverted polarity."""
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
        # The ones that push their claim towards the wrong Verdict.
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
    """Compose the report of Stances against the hand-labelled ones."""

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
    """Compose the judge report: the configuration, the Verdicts and the spread of Stances."""
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
    """Script entry point that judges the recorded cases and prints the report."""
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
    # Run identity, since resuming with another judge would mix results.
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
