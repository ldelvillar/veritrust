"""Compare a PR's pipeline evaluation with main's on the same samples and fail when a gated metric regresses."""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from evaluation.evaluate_pipeline import (
    EvalRow,
    Sample,
    compute_metrics,
    load_checkpoint,
    load_samples,
    read_checkpoint_run,
    replay_counts,
)

# Largest drop each metric may take below main, a few samples wide since n=100 leaves ~5 points of noise.
GATED = {"accuracy": 0.05, "recall": 0.05, "coverage": 0.10, "claims_found": 0.05}

# Metrics shown beside the gated ones without failing the gate.
REPORTED = ("precision", "f1_score")

# Samples an arm may lose to provider errors before the comparison stops being paired.
MAX_MISSING = 5

# Marks the PR comment, so CI edits its own comment instead of adding one per push.
MARKER = "<!-- eval-gate -->"


@dataclass(frozen=True)
class Arm:
    """One side of the comparison: its checkpoint header and its rows by sample text."""

    run: dict | None
    rows: dict[str, EvalRow]

    @classmethod
    def load(cls, path: Path) -> "Arm":
        """Read an arm from its evaluation checkpoint."""
        return cls(read_checkpoint_run(path), load_checkpoint(path))


@dataclass(frozen=True)
class GateResult:
    """Whether the PR passes the gate, with the Markdown report that explains it."""

    passed: bool
    report: str


def _pct(value: float) -> str:
    """Format a ratio as a percentage with one decimal."""
    return f"{value:.1%}"


def _delta(value: float) -> str:
    """Format a change in percentage points with its sign."""
    return f"{value * 100:+.1f} pp"


def _describe(name: str, arm: Arm) -> str:
    """Report line naming an arm's commit, prompt versions and Langfuse run."""
    run = arm.run or {}
    prompts = ", ".join(f"{k}={v}" for k, v in (run.get("prompts") or {}).items())
    langfuse = run.get("langfuse_run")
    return (
        f"- **{name}**: git `{run.get('git') or 'desconocido'}` · prompts {prompts or '—'}"
        + (f" · Langfuse `{langfuse}`" if langfuse else "")
    )


def _metrics(rows: list[EvalRow]) -> dict[str, float]:
    """Compute the eval metrics plus the share of samples with claims, which no other metric counts."""
    metrics = compute_metrics(rows)
    metrics["claims_found"] = 1 - metrics["skipped"] / len(rows) if rows else 0.0
    return metrics


def evaluate_gate(samples: list[Sample], base: Arm, head: Arm) -> GateResult:
    """Score both arms on the samples each completed and fail on a regression beyond its tolerance."""
    texts = [sample["text"] for sample in samples]
    shared = [t for t in texts if t in base.rows and t in head.rows]
    missing = {
        "main": sum(t not in base.rows for t in texts),
        "PR": sum(t not in head.rows for t in texts),
    }
    before = _metrics([base.rows[t] for t in shared])
    after = _metrics([head.rows[t] for t in shared])

    # The epsilon keeps a drop of exactly the tolerance from failing on float rounding.
    regressed = {
        name
        for name, tolerance in GATED.items()
        if before[name] - after[name] > tolerance + 1e-9
    }
    incomplete = {arm: n for arm, n in missing.items() if n > MAX_MISSING}
    passed = not regressed and not incomplete

    lines = [
        MARKER,
        f"### Puerta de evaluación: {'✅ pasa' if passed else '❌ falla'}",
        "",
        f"Gold set, {len(shared)} de {len(texts)} muestras evaluadas en ambas ramas, "
        "con la evidencia de main reproducida en la PR.",
        "",
        "| Métrica | main | PR | Δ | Tolerancia | |",
        "|---|---|---|---|---|---|",
    ]
    for name, tolerance in GATED.items():
        status = "❌" if name in regressed else "✅"
        lines.append(
            f"| {name} | {_pct(before[name])} | {_pct(after[name])} | "
            f"{_delta(after[name] - before[name])} | -{tolerance * 100:.0f} pp | {status} |"
        )
    for name in REPORTED:
        lines.append(
            f"| {name} | {_pct(before[name])} | {_pct(after[name])} | "
            f"{_delta(after[name] - before[name])} | — | |"
        )
    for name in ("fn", "fp", "uncertain", "skipped"):
        lines.append(f"| {name} | {int(before[name])} | {int(after[name])} | | — | |")

    searches, live = replay_counts([head.rows[t] for t in shared])
    lines += [
        "",
        f"Evidencia de la PR: {searches - live}/{searches} búsquedas reproducidas de main "
        "(el resto son consultas nuevas, buscadas en vivo).",
        "",
        _describe("main", base),
        _describe("PR", head),
    ]
    for arm, n in incomplete.items():
        lines.append(
            f"\n**{arm} perdió {n} muestras** (máximo {MAX_MISSING}); "
            "relanza el job para reintentarlas."
        )
    return GateResult(passed, "\n".join(lines))


def main() -> None:
    """Script entry point that prints the report, writes it to --report and exits non-zero on failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True, help="Checkpoint de main.")
    parser.add_argument("--head", type=Path, required=True, help="Checkpoint de la PR.")
    parser.add_argument(
        "--report", type=Path, required=True, help="Markdown de salida."
    )
    parser.add_argument("--partition", default="gold")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    samples = load_samples(args.partition, args.limit, args.seed)
    result = evaluate_gate(samples, Arm.load(args.base), Arm.load(args.head))
    args.report.write_text(result.report + "\n", encoding="utf-8")
    print(result.report)
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
