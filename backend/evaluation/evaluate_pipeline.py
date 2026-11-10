"""Evaluate the full multi-agent pipeline against a labelled HealthVer set and report classification metrics."""

import argparse
import asyncio
import json
import logging
import os
import re
import subprocess
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from itertools import count
from pathlib import Path
from time import time
from typing import Any, TypedDict, cast

import pandas as pd
from langfuse import Evaluation

from app.agents import investigator as investigator_module
from app.agents.errors import ainvoke_graph
from app.agents.main import create_graph, describe_pipeline
from app.core.claim import Claim
from app.core.config import get_settings
from app.core.tracing import langfuse
from app.core.verdict import Verdict, kind_of
from app.prompts.agents import Prompts, load_prompts
from app.utils.evidence import EvidenceRetrievalError
from app.utils.llm import ensure_llm_available
from evaluation.load_data import load_dataset, load_jsonl

logger = logging.getLogger(__name__)

# Map HealthVer to the system's binary labels, leaving NEI (2) out of the metric.
LABEL_BY_CODE = {0: "verdadera", 1: "falsa"}

# Langfuse dataset of each repo partition, which evaluation.upload_datasets creates.
LANGFUSE_DATASETS = {
    "gold": "gold-es",
    "negations": "negations-es",
    "test": "healthver-test",
}


class Sample(TypedDict):
    """A labelled sample ready to evaluate."""

    text: str
    expected: str


class EvidenceCall(TypedDict):
    """A search in an evidence source with its raw results, or hits None if the source failed."""

    source: str
    query: str
    max_results: int
    hits: list[dict] | None


class RecordedEvidence(TypedDict):
    """A Source found for a claim and the Stance the judge gave it."""

    url: str
    stance: str | None


class RecordedClaim(TypedDict):
    """Outcome of a claim's search and all its Evidence, before the report's trim."""

    outcome: str
    evidence: list[RecordedEvidence]


class EvalRow(TypedDict):
    """Pipeline result for a sample, against its expected label."""

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
    claim_evidence: list[RecordedClaim]
    evidence: list[EvidenceCall]
    evidence_live: int
    explanation: str


# The investigator's searches per source, which the tape replaces while a sample is evaluated.
_SEARCHES = {
    "europepmc": "search_europepmc",
    "pubmed": "search_pubmed",
    "openfda": "search_openfda",
    "cima": "search_cima",
}


class EvidenceTape:
    """Record a sample's evidence searches and replay the ones it already had recorded."""

    def __init__(self, recorded: list[EvidenceCall] | None = None) -> None:
        self._recorded = {
            (call["source"], call["query"], call["max_results"]): call["hits"]
            for call in recorded or []
        }
        self.calls: list[EvidenceCall] = []
        self._live: list[EvidenceCall] = []

    @property
    def live(self) -> int:
        """Searches the recording did not cover, which went to the source."""
        return len(self._live)

    def wrap(
        self, source: str, search: Callable[..., list[dict]]
    ) -> Callable[..., list[dict]]:
        """Wrap a search, serving the recording if there is one and otherwise querying the source."""

        def taped(query: str, *, max_results: int) -> list[dict]:
            # Noted before searching, so a failing source is recorded as failed.
            call: EvidenceCall = {
                "source": source,
                "query": query,
                "max_results": max_results,
                "hits": None,
            }
            self.calls.append(call)
            key = (source, query, max_results)
            if key in self._recorded:
                hits = self._recorded[key]
                if hits is None:
                    # A recorded outage is replayed, so both runs see the same Evidence.
                    raise EvidenceRetrievalError(f"Caída grabada de {source}")
            else:
                self._live.append(call)
                hits = search(query, max_results=max_results)
            call["hits"] = hits
            return hits

        return taped

    @contextmanager
    def install(self) -> Iterator[None]:
        """Replace the investigator's searches with the tape's for the duration of the block."""
        live = {attr: getattr(investigator_module, attr) for attr in _SEARCHES.values()}
        for source, attr in _SEARCHES.items():
            setattr(investigator_module, attr, self.wrap(source, live[attr]))
        try:
            yield
        finally:
            for attr, search in live.items():
                setattr(investigator_module, attr, search)


def _recorded(claim: Claim) -> RecordedClaim:
    """Reduce a claim to what is needed to decide its Verdict again."""
    return {
        "outcome": claim.outcome,
        "evidence": [
            {"url": item.url, "stance": item.stance} for item in claim.evidence
        ],
    }


def _stance_histogram(sources: list[dict]) -> dict[str, int]:
    """Count the Stances assigned to the Sources that survived the judge."""
    counts: dict[str, int] = {}
    for source in sources:
        for statement in source.get("statements") or []:
            stance = str(statement.get("stance"))
            counts[stance] = counts.get(stance, 0) + 1
    return counts


def binary_claims(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the claims with a binary label and a text, adding the cleaned text and expected label the eval and its datasets share."""
    df = df[df["label"].isin(LABEL_BY_CODE)].copy()
    df["expected"] = df["label"].map(LABEL_BY_CODE)
    df["text"] = df["claim"].astype(str).str.replace("\xa0", " ").str.strip()
    return df[df["text"] != ""]


def load_samples(
    partition: str = "test",
    limit: int = 30,
    seed: int = 42,
    data: Path | None = None,
) -> list[Sample]:
    """Load a balanced binary sample from a partition, or from the JSONL ``data`` if given, for evaluation."""
    df = binary_claims(load_jsonl(str(data)) if data else load_dataset(partition))

    # Sample each class equally so the metrics are not biased.
    per_class = max(1, limit // 2)
    frames = [
        subset.sample(n=min(per_class, len(subset)), random_state=seed)
        for _, subset in df.groupby("expected")
    ]
    sampled = pd.concat(frames).sample(frac=1, random_state=seed).head(limit)

    return [
        {"text": str(row["text"]), "expected": str(row["expected"])}
        for _, row in sampled.iterrows()
    ]


def _build_initial_state(text: str) -> dict[str, object]:
    """Build the graph's initial state for an input text."""
    return {
        "input_text": text,
        "claims": [],
        "medical_explanation": "",
    }


def load_checkpoint(path: Path) -> dict[str, EvalRow]:
    """Read the already evaluated rows of a JSONL checkpoint, empty if it does not exist."""
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
                # Corrupt line (e.g. a crash mid-write), ignored.
                continue
            if isinstance(row, dict) and "text" in row:
                done[row["text"]] = cast(EvalRow, row)
    return done


def load_recorded_evidence(path: Path) -> dict[str, list[EvidenceCall]]:
    """Read the raw Evidence recorded in a checkpoint, by sample text."""
    return {
        text: row["evidence"]
        for text, row in load_checkpoint(path).items()
        if "evidence" in row
    }


# Run identity, since resuming with other values would mix configurations under one header.
_RUN_IDENTITY_KEYS = (
    "provider",
    "models",
    "prompts",
    "replay_evidence",
    "langfuse_run",
)


class CheckpointMismatchError(ValueError):
    """The checkpoint was generated with another configuration or does not record it."""


def git_describe() -> str | None:
    """Commit of the evaluated code, with -dirty if there are uncommitted changes, None without git."""
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


def describe_run(
    prompts: Prompts,
    *,
    partition: str,
    seed: int,
    replay_evidence: str | None = None,
    langfuse_run: str | None = None,
) -> dict:
    """Summarise the pipeline configuration that produces a checkpoint's rows."""
    return {
        **describe_pipeline(prompts),
        "partition": partition,
        "seed": seed,
        "git": git_describe(),
        "replay_evidence": replay_evidence,
        # Part of the identity, so an experiment's run scores only count its own rows.
        "langfuse_run": langfuse_run,
    }


def read_checkpoint_run(path: Path) -> dict | None:
    """Return the configuration recorded in the checkpoint header, if any."""
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
    """Write a new checkpoint's header or verify it resumes with the same configuration."""
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        path.write_text(
            json.dumps({"run": run}, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return run
    recorded = read_checkpoint_run(path)
    if recorded is None or any(
        recorded.get(k) != run.get(k) for k in _RUN_IDENTITY_KEYS
    ):
        raise CheckpointMismatchError(
            f"El checkpoint {path} se generó con otra configuración o no la registra; "
            "usa --fresh u otro --checkpoint para no mezclar resultados."
        )
    return recorded


# Evaluates one sample and returns its row, or None if it failed and is left for the resume.
EvaluateSample = Callable[[Sample], Awaitable[EvalRow | None]]

# Runs every pending sample through the evaluation, in order unless an experiment drives it.
RunPending = Callable[[list[Sample], EvaluateSample], Awaitable[None]]


async def run_in_order(pending: list[Sample], evaluate: EvaluateSample) -> None:
    """Evaluate the pending samples one after another."""
    for sample in pending:
        await evaluate(sample)


class MissingDatasetItemsError(ValueError):
    """Some samples have no item in the Langfuse dataset, which is missing or out of date."""


# Run-level metrics recorded as the experiment's scores, so runs can be compared.
RUN_SCORES = ("accuracy", "coverage", "precision", "recall", "f1_score")


def score_sample(*, output: dict, expected_output: dict, **_: Any) -> list[Evaluation]:
    """Score a sample's Verdict against its label, with correctness only for a firm Verdict, as compute_metrics counts it."""
    abstained = _is_abstention(output["label"])
    scores = [
        Evaluation(name="abstained", value=float(abstained), data_type="BOOLEAN"),
        Evaluation(name="confidence", value=output["confidence"]),
    ]
    if not abstained:
        correct = _flags_falsehood(output["label"]) == (
            expected_output["label"] == "falsa"
        )
        scores.append(
            Evaluation(name="correct", value=float(correct), data_type="BOOLEAN")
        )
    return scores


class SampleFailedError(RuntimeError):
    """The sample failed and is left for the resume, which Langfuse shows as an error item."""


class LangfuseExperiment:
    """Run the pending samples as a scored Langfuse experiment, so each sample's trace is linked to its dataset item."""

    def __init__(
        self,
        client: Any,
        dataset_name: str,
        samples: list[Sample],
        run_name: str,
        run: dict,
    ) -> None:
        self._client = client
        self._dataset_name = dataset_name
        self._run_name = run_name
        self._items = {
            item.input["text"]: item for item in client.get_dataset(dataset_name).items
        }
        missing = sum(1 for sample in samples if sample["text"] not in self._items)
        if missing:
            raise MissingDatasetItemsError(
                f"{missing} muestras no están en el dataset {dataset_name} de Langfuse; "
                "súbelo con python -m evaluation.upload_datasets."
            )
        # Langfuse takes metadata as strings only.
        self._metadata = {
            key: value
            if isinstance(value, str)
            else json.dumps(value, ensure_ascii=False)
            for key, value in run.items()
            if value is not None
        }
        # Fixed by the dataset and run name, so every sample and a resume share one experiment without asking Langfuse.
        self.experiment_id = client.create_trace_id(seed=f"{dataset_name}/{run_name}")

    async def __call__(self, pending: list[Sample], evaluate: EvaluateSample) -> None:
        """Evaluate the pending samples one at a time, each under its dataset item."""
        for sample in pending:
            await self._run_one(sample, evaluate)

    async def _run_one(self, sample: Sample, evaluate: EvaluateSample) -> None:
        """Evaluate one sample as an experiment item and raise any error Langfuse would only log."""
        unexpected: list[Exception] = []

        async def task(*, item: Any, **_: Any) -> dict:
            try:
                row = await evaluate(sample)
            except Exception as exc:
                unexpected.append(exc)
                raise
            if row is None:
                raise SampleFailedError("La muestra falló; se reintentará al reanudar.")
            # The full row stays in the checkpoint, and the trace already shows the Evidence.
            return {"label": row["predicted"], "confidence": row["confidence"]}

        # run_experiment starts its own event loop, so it runs in a thread.
        running = asyncio.ensure_future(
            asyncio.to_thread(
                self._client.run_experiment,
                name=f"pipeline-{self._dataset_name}",
                run_name=self._run_name,
                experiment_id=self.experiment_id,
                data=[self._items[sample["text"]]],
                task=task,
                evaluators=[score_sample],
                metadata=self._metadata,
            )
        )
        try:
            await asyncio.shield(running)
        except asyncio.CancelledError:
            # A thread cannot be cancelled, so the sample finishes before the checkpoint closes.
            await running
            raise
        if unexpected:
            raise unexpected[0]

    def record_metrics(self, metrics: dict[str, float]) -> None:
        """Score the experiment with the metrics of all its rows, resumed ones included."""
        for name in RUN_SCORES:
            self._client.create_score(
                dataset_run_id=self.experiment_id,
                # A fixed id per metric, so a resumed run updates its score instead of adding one.
                score_id=f"{self.experiment_id}-{name}",
                name=name,
                value=metrics[name],
            )
        self._client.flush()


async def evaluate_pipeline(
    samples: list[Sample],
    graph: object,
    checkpoint_path: Path | None = None,
    replay: dict[str, list[EvidenceCall]] | None = None,
    run_pending: RunPending = run_in_order,
) -> list[EvalRow]:
    """Run the graph on each sample, with optional checkpoint, resume and recorded Evidence."""
    done: dict[str, EvalRow] = (
        load_checkpoint(checkpoint_path) if checkpoint_path else {}
    )
    pending = [s for s in samples if s["text"] not in done]
    total = len(pending)
    if done:
        logger.info("Reanudando: %d ya evaluadas, %d pendientes", len(done), total)
    # Numbers the log lines in the order the samples start.
    started_numbers = count(1)

    # Only completed samples are persisted, so a failing one is retried on resume.
    handle = checkpoint_path.open("a", encoding="utf-8") if checkpoint_path else None

    async def evaluate(sample: Sample) -> EvalRow | None:
        i = next(started_numbers)
        tape = EvidenceTape((replay or {}).get(sample["text"]))
        started = time()
        try:
            with tape.install():
                result = await ainvoke_graph(
                    graph, _build_initial_state(sample["text"])
                )
        except Exception:
            logger.exception(
                "[%d/%d] fallo al analizar; se reintentará al reanudar", i, total
            )
            return None
        duration = time() - started

        # No Verdict because the text had no verifiable medical claims.
        verdict: Verdict | None = result.get("verdict")
        claims: list[Claim] = result.get("claims") or []
        row: EvalRow = {
            "text": sample["text"],
            "expected": sample["expected"],
            "predicted": verdict.label if verdict else None,
            "confidence": verdict.confidence if verdict else 0.0,
            # Raw fake_avg so the global band can be swept without rerunning.
            "fake_avg": verdict.falsehood if verdict else None,
            # Cost per sample, which sets the affordable n in later evaluations.
            "duration_seconds": round(duration, 3),
            # Lets extractor and translator polarity inversions be detected.
            "extracted": [claim.text for claim in claims],
            "translated": [claim.text_en for claim in claims],
            # Diagnostic that tells "nothing was retrieved" apart from "the judge will not commit".
            "sources_kept": len(result.get("sources") or []),
            "stances": _stance_histogram(result.get("sources") or []),
            "evidence_coverage": verdict.evidence_coverage if verdict else 0.0,
            # Claims whose judge answer was unusable, which the Verdict counts as uncertain.
            "judge_failures": int(result.get("judge_failures") or 0),
            # Full Evidence per claim, so another trim policy can be tested without rerunning.
            "claim_evidence": [_recorded(claim) for claim in claims],
            # Raw hits per search, which another run replays with --replay-evidence.
            "evidence": tape.calls,
            # Searches the recording did not cover, which measure the mismatch with --replay-evidence.
            "evidence_live": tape.live,
            # Expert report (empty without --with-explanation), to evaluate how well it is grounded.
            "explanation": str(result.get("medical_explanation") or ""),
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
            row["predicted"] or "sin_afirmaciones",
            duration,
        )
        return row

    try:
        await run_pending(pending, evaluate)
    finally:
        if handle is not None:
            handle.close()

    # Rows of this run's samples, in order, leaving the failed ones out.
    return [done[s["text"]] for s in samples if s["text"] in done]


def _is_abstention(predicted: str | None) -> bool:
    """No claims (None) or a non-firm Verdict ('incierta') do not score."""
    return predicted is None or kind_of(predicted) == "uncertain"


def _flags_falsehood(predicted: str | None) -> bool:
    """A false or partly false Verdict warns that the text contains something false."""
    return kind_of(predicted) in ("fake", "mixed")


def compute_metrics(rows: list[EvalRow]) -> dict[str, float]:
    """Compute the confusion matrix and metrics taking 'falsa' as positive."""
    # Abstaining ('incierta') is safe, not an error, so it is excluded from the metrics.
    scored = [r for r in rows if not _is_abstention(r["predicted"])]
    skipped = sum(1 for r in rows if r["predicted"] is None)
    uncertain = len(rows) - len(scored) - skipped

    tp = fp = tn = fn = 0
    for row in scored:
        expected_fake = row["expected"] == "falsa"
        predicted_fake = _flags_falsehood(row["predicted"])
        if expected_fake:
            tp += predicted_fake
            fn += not predicted_fake
        else:
            tn += not predicted_fake
            fp += predicted_fake

    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total else 0.0
    # Coverage, the firm Verdicts over the samples that did have claims.
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
        # An unusable judge answer leaves its claim uncertain, as in production, so the row still scores.
        "judge_failed": sum(1 for r in rows if r.get("judge_failures")),
    }


def _format_run(run: dict) -> list[str]:
    """Report lines that attribute the metrics to the configuration that produced them."""
    models = ", ".join(f"{role}={name}" for role, name in run["models"].items())
    prompts = ", ".join(f"{name}={version}" for name, version in run["prompts"].items())
    return [
        f"Proveedor : {run['provider']} · git {run.get('git') or 'desconocido'}",
        f"Partición : {run['partition']} (seed {run['seed']})",
        f"Modelos   : {models}",
        f"Prompts   : {prompts}",
    ]


def _format_replay(run: dict | None, rows: list[EvalRow]) -> list[str]:
    """Report line that says how much Evidence was replayed from the recording."""
    if not run or not run.get("replay_evidence"):
        return []
    searches = sum(len(row.get("evidence") or []) for row in rows)
    live = sum(row.get("evidence_live") or 0 for row in rows)
    source = Path(run["replay_evidence"]).name
    return [
        f"Evidencia : {searches - live}/{searches} búsquedas reproducidas de {source}"
    ]


def format_report(
    metrics: dict[str, float], rows: list[EvalRow], run: dict | None = None
) -> str:
    """Compose a readable report with metrics and misclassified examples."""
    lines = [
        "",
        "===== Evaluación del pipeline multiagente =====",
        *(_format_run(run) if run else []),
        *_format_replay(run, rows),
        f"Muestras evaluadas : {int(metrics['evaluated'])}",
        f"Veredicto incierto : {int(metrics['uncertain'])} (abstención, excluida de las métricas)",
        f"Sin afirmaciones   : {int(metrics['skipped'])} (excluidas de las métricas)",
        f"Juez inservible    : {int(metrics['judge_failed'])} "
        "(afirmaciones sin juzgar, inciertas como en producción)",
        f"TP={int(metrics['tp'])} TN={int(metrics['tn'])} "
        f"FP={int(metrics['fp'])} FN={int(metrics['fn'])}",
        f"Accuracy  : {metrics['accuracy']:.2%}",
        f"Cobertura : {metrics['coverage']:.2%} (veredictos firmes / muestras con afirmaciones)",
        f"Precision : {metrics['precision']:.2%}",
        f"Recall    : {metrics['recall']:.2%}",
        f"F1-score  : {metrics['f1_score']:.2%}",
    ]

    # Only firm Verdicts that disagree with the expected one count as errors.
    errors = [
        r
        for r in rows
        if not _is_abstention(r["predicted"])
        and _flags_falsehood(r["predicted"]) != (r["expected"] == "falsa")
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


def langfuse_run_name(value: str) -> str:
    """Accept a Langfuse run name that is also safe inside the checkpoint's file name."""
    if not re.fullmatch(r"[\w.-]+", value, flags=re.ASCII):
        raise argparse.ArgumentTypeError(
            "usa solo letras, dígitos, '.', '_' y '-' en el nombre de la corrida."
        )
    return value


def default_checkpoint(source: str, langfuse_run: str | None = None) -> Path:
    """Path of a set's checkpoint under results/, one per Langfuse run so switching runs never needs --fresh."""
    suffix = f"_{langfuse_run}" if langfuse_run else ""
    return (
        Path(__file__).resolve().parents[1]
        / "results"
        / f"eval_pipeline_{source}{suffix}.jsonl"
    )


def main() -> dict[str, float]:
    """Script entry point that runs the evaluation and prints the report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--partition",
        default="test",
        choices=["train", "test", "validation", "gold", "negations"],
        help="Partición de HealthVer a muestrear.",
    )
    parser.add_argument(
        "--data",
        default=None,
        metavar="JSONL",
        help="Conjunto etiquetado fuera del repo, como el reservado; sustituye a --partition.",
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
        help="Ruta del checkpoint JSONL (por defecto results/eval_pipeline_<partición>.jsonl, o eval_pipeline_<partición>_<corrida>.jsonl con --langfuse-run).",
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
    parser.add_argument(
        "--replay-evidence",
        default=None,
        metavar="CKPT",
        help="Reproduce la evidencia bruta grabada en otro checkpoint; solo busca en vivo lo que no esté grabado.",
    )
    parser.add_argument(
        "--langfuse-run",
        default=None,
        type=langfuse_run_name,
        metavar="NOMBRE",
        help="Registra la corrida como experimento de Langfuse con este nombre, sobre el dataset de la partición; usa un nombre nuevo por corrida desde cero.",
    )
    args = parser.parse_args()

    if args.langfuse_run:
        if args.data or args.partition not in LANGFUSE_DATASETS:
            raise SystemExit(
                "--langfuse-run solo admite las particiones "
                f"{', '.join(LANGFUSE_DATASETS)}, que tienen dataset en Langfuse."
            )
        if not get_settings().langfuse_enabled():
            raise SystemExit(
                "--langfuse-run exige LANGFUSE_PUBLIC_KEY y LANGFUSE_SECRET_KEY."
            )

    # The report is ~1/3 of the tokens per sample and does not affect the metric.
    if not args.with_explanation:
        os.environ["HEALTH_EXPERT_EXPLANATION_ENABLED"] = "false"
        # Importing the tracing module already loaded the settings, so they are read again.
        get_settings.cache_clear()

    # results/ is git-ignored, and the checkpoint lets a long evaluation resume.
    data = Path(args.data) if args.data else None
    # The set is named after its file when it is not a repo partition.
    source = data.stem if data else args.partition
    checkpoint_path = (
        Path(args.checkpoint)
        if args.checkpoint
        else default_checkpoint(source, args.langfuse_run)
    )
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    replay: dict[str, list[EvidenceCall]] | None = None
    replay_path = Path(args.replay_evidence).resolve() if args.replay_evidence else None
    if replay_path is not None:
        # --fresh would delete exactly the recording meant to be replayed.
        if replay_path == checkpoint_path.resolve():
            raise SystemExit(
                "--replay-evidence debe apuntar a otro checkpoint que --checkpoint."
            )
        replay = load_recorded_evidence(replay_path)
        if not replay:
            raise SystemExit(f"{replay_path} no existe o no guarda evidencia bruta.")

    if args.fresh:
        checkpoint_path.unlink(missing_ok=True)

    ensure_llm_available()

    prompts = load_prompts()
    try:
        run = prepare_checkpoint(
            checkpoint_path,
            describe_run(
                prompts,
                partition=source,
                seed=args.seed,
                replay_evidence=str(replay_path) if replay_path else None,
                langfuse_run=args.langfuse_run,
            ),
        )
    except CheckpointMismatchError as exc:
        raise SystemExit(str(exc)) from exc

    graph = create_graph(prompts)
    samples = load_samples(args.partition, args.limit, args.seed, data)
    logger.info("Evaluando %d muestras de '%s'", len(samples), source)

    experiment: LangfuseExperiment | None = None
    if args.langfuse_run:
        try:
            experiment = LangfuseExperiment(
                langfuse,
                LANGFUSE_DATASETS[args.partition],
                samples,
                args.langfuse_run,
                run,
            )
        except MissingDatasetItemsError as exc:
            raise SystemExit(str(exc)) from exc

    start = time()
    rows = asyncio.run(
        evaluate_pipeline(
            samples, graph, checkpoint_path, replay, experiment or run_in_order
        )
    )
    metrics = compute_metrics(rows)
    # With no row the metrics are all zero, which would score a run that never got a Verdict.
    if experiment is not None and rows:
        experiment.record_metrics(metrics)

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
