"""Unit tests for the multi-agent pipeline evaluation."""

import asyncio
import json
import threading
import time
from dataclasses import replace
from types import SimpleNamespace

import pandas as pd
import pytest

from app.agents import investigator as investigator_module
from app.core.claim import Claim, Evidence
from app.core.config import get_settings
from app.core.verdict import Verdict
from app.utils.evidence import EvidenceRetrievalError
from evaluation import evaluate_pipeline as ep


def _verdict(kind, confidence: float, falsehood: float = 0.5) -> Verdict:
    """Minimal Verdict as the expert leaves it in the graph state."""
    return Verdict(
        kind=kind,
        confidence=confidence,
        falsehood=falsehood,
        evidence_coverage=1.0,
        claims=(),
    )


def _row(expected: str, predicted: str | None, confidence: float = 0.9) -> ep.EvalRow:
    return {
        "text": "afirmacion de prueba",
        "expected": expected,
        "predicted": predicted,
        "confidence": confidence,
        "fake_avg": None,
        "duration_seconds": 0.0,
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
    assert metrics["coverage"] == 1.0


def test_compute_metrics_counts_confusion_and_skips() -> None:
    rows = [
        _row("falsa", "falsa"),  # tp
        _row("falsa", "verdadera"),  # fn
        _row("verdadera", "falsa"),  # fp
        _row("verdadera", "verdadera"),  # tn
        _row("falsa", None),  # no claims, excluded
    ]
    metrics = ep.compute_metrics(rows)

    assert (metrics["tp"], metrics["fn"], metrics["fp"], metrics["tn"]) == (1, 1, 1, 1)
    assert metrics["evaluated"] == 4
    assert metrics["skipped"] == 1
    assert metrics["accuracy"] == 0.5


def test_compute_metrics_treats_incierta_as_abstention() -> None:
    rows = [
        _row("falsa", "falsa"),  # tp
        _row("verdadera", "incierta"),  # abstention, does not score
        _row("falsa", "incierta"),  # abstention, does not score
        _row("verdadera", None),  # no claims, excluded
    ]
    metrics = ep.compute_metrics(rows)

    assert (metrics["tp"], metrics["fn"], metrics["fp"], metrics["tn"]) == (1, 0, 0, 0)
    assert metrics["evaluated"] == 1
    assert metrics["uncertain"] == 2
    assert metrics["skipped"] == 1
    # Abstaining is not penalised, since the only firm Verdict is correct.
    assert metrics["accuracy"] == 1.0
    # Coverage does reflect abstentions, 1 firm out of 3 with claims.
    assert metrics["coverage"] == pytest.approx(1 / 3)


def test_evaluate_pipeline_records_the_raw_falsehood_the_band_saw() -> None:
    samples: list[ep.Sample] = [{"text": "afirmacion", "expected": "falsa"}]

    class FakeGraph:
        async def astream(
            self, state: dict, stream_mode: object = None, config: object = None
        ):
            yield ("values", {"verdict": _verdict("fake", 0.5425, falsehood=0.62)})

    [row] = asyncio.run(ep.evaluate_pipeline(samples, FakeGraph()))

    # The falsehood arrives unattenuated, so coverage no longer needs inverting.
    assert (row["predicted"], row["confidence"]) == ("falsa", 0.5425)
    assert row["fake_avg"] == 0.62
    assert row["evidence_coverage"] == 1.0


def test_evaluate_pipeline_records_every_claim_evidence_before_the_report_cap() -> None:
    samples: list[ep.Sample] = [{"text": "afirmacion", "expected": "falsa"}]
    found = [
        Claim(
            index=0,
            text="A",
            query='"a"',
            outcome="judged",
            evidence=(
                Evidence(title="T1", url="u1", stance="contradicts"),
                Evidence(title="T2", url="u2", stance="supports"),
            ),
        ),
        Claim(index=1, text="B", query='"b"', outcome="unavailable"),
        Claim(index=2, text="C"),
    ]

    class FakeGraph:
        async def astream(
            self, state: dict, stream_mode: object = None, config: object = None
        ):
            # The report only showed the first Source and the row keeps both.
            shown = [replace(found[0], evidence=found[0].evidence[:1]), *found[1:]]
            yield (
                "values",
                {
                    "verdict": _verdict("fake", 0.6),
                    "claims": found,
                    "shown_claims": shown,
                },
            )

    [row] = asyncio.run(ep.evaluate_pipeline(samples, FakeGraph()))

    assert row["claim_evidence"] == [
        {
            "outcome": "judged",
            "evidence": [
                {"url": "u1", "stance": "contradicts"},
                {"url": "u2", "stance": "supports"},
            ],
        },
        {"outcome": "unavailable", "evidence": []},
        {"outcome": "unsearchable", "evidence": []},
    ]
    # The claims' text still comes from the same record.
    assert row["extracted"] == ["A", "B", "C"]


def test_format_report_excludes_abstentions_from_errors() -> None:
    rows = [_row("falsa", "incierta"), _row("verdadera", "verdadera")]
    metrics = ep.compute_metrics(rows)

    report = ep.format_report(metrics, rows)

    assert "Errores de clasificación" not in report
    assert "Veredicto incierto : 1" in report


def test_compute_metrics_scores_a_row_with_an_unusable_judge_answer() -> None:
    row: ep.EvalRow = {**_row("falsa", "falsa"), "judge_failures": 1}

    metrics = ep.compute_metrics([row])

    # Production keeps the Verdict and shows the unjudged claim as uncertain, so the row scores like any other (ADR-0006).
    assert (metrics["tp"], metrics["evaluated"]) == (1, 1)
    assert metrics["judge_failed"] == 1


def test_compute_metrics_empty_rows_are_zero() -> None:
    metrics = ep.compute_metrics([])

    assert metrics["accuracy"] == 0.0
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1_score"] == 0.0
    assert metrics["evaluated"] == 0
    assert metrics["coverage"] == 0.0


def test_load_samples_balances_classes_and_maps_labels(monkeypatch) -> None:
    df = pd.DataFrame(
        {
            "claim": [f"c{i}" for i in range(8)],
            # 0 is verdadera, 1 is falsa and NEI (2) is dropped.
            "label": [0, 0, 0, 1, 1, 1, 2, 2],
        }
    )
    monkeypatch.setattr(ep, "load_dataset", lambda partition: df.copy())

    samples = ep.load_samples(partition="validation", limit=4, seed=1)

    assert len(samples) == 4
    labels = {s["expected"] for s in samples}
    assert labels <= {"verdadera", "falsa"}
    # The 'NEI' class (2) must never appear.
    assert all(s["text"] not in {"c6", "c7"} for s in samples)


def test_load_samples_reads_a_jsonl_outside_the_repo(monkeypatch, tmp_path) -> None:
    data = tmp_path / "reservado.jsonl"
    rows = [{"claim": "verdad", "label": 0}, {"claim": "bulo", "label": 1}]
    data.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def _no_partition(partition):
        raise AssertionError("con un archivo no se lee ninguna partición")

    monkeypatch.setattr(ep, "load_dataset", _no_partition)

    samples = ep.load_samples(limit=2, seed=1, data=data)

    assert sorted((s["text"], s["expected"]) for s in samples) == [
        ("bulo", "falsa"),
        ("verdad", "verdadera"),
    ]


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

    # ainvoke_graph consumes the graph by streaming (astream), not ainvoke.
    class FakeGraph:
        async def astream(
            self, state: dict, stream_mode: object = None, config: object = None
        ):
            if "sin" in state["input_text"]:
                yield ("values", {"verdict": None, "medical_explanation": ""})
            else:
                yield (
                    "values",
                    {
                        "verdict": _verdict("fake", 0.8),
                        "medical_explanation": "informe",
                    },
                )

    rows = asyncio.run(ep.evaluate_pipeline(samples, FakeGraph()))

    assert rows[0]["predicted"] == "falsa"
    assert rows[1]["predicted"] is None
    assert rows[1]["confidence"] == 0.0


def test_evaluate_pipeline_records_the_explanation() -> None:
    samples: list[ep.Sample] = [{"text": "afirmacion", "expected": "falsa"}]

    class FakeGraph:
        async def astream(
            self, state: dict, stream_mode: object = None, config: object = None
        ):
            yield (
                "values",
                {"verdict": _verdict("fake", 0.8), "medical_explanation": "informe"},
            )

    rows = asyncio.run(ep.evaluate_pipeline(samples, FakeGraph()))

    assert rows[0]["explanation"] == "informe"


def test_partly_false_counts_as_flagging_the_falsehood() -> None:
    rows = [
        _row("falsa", "parcialmente falsa"),  # tp, warns of something false
        _row(
            "verdadera", "parcialmente falsa"
        ),  # fp, a true one contains nothing false
    ]
    metrics = ep.compute_metrics(rows)

    assert (metrics["tp"], metrics["fn"], metrics["fp"], metrics["tn"]) == (1, 0, 1, 0)
    assert "Errores de clasificación (1)" in ep.format_report(metrics, rows)


def test_format_report_lists_misclassifications() -> None:
    rows = [_row("falsa", "verdadera", 0.7), _row("verdadera", "verdadera")]
    metrics = ep.compute_metrics(rows)

    report = ep.format_report(metrics, rows)

    assert "Evaluación del pipeline multiagente" in report
    assert "Errores de clasificación (1)" in report


def test_build_initial_state_has_pipeline_keys() -> None:
    state = ep._build_initial_state("hola")

    assert state["input_text"] == "hola"
    assert state["claims"] == []
    assert state["medical_explanation"] == ""


def test_load_checkpoint_reads_rows_and_ignores_corrupt(tmp_path) -> None:
    path = tmp_path / "ckpt.jsonl"
    good = {"text": "a", "expected": "falsa", "predicted": "falsa", "confidence": 0.9}
    path.write_text(json.dumps(good) + "\n\n{corrupto\n", encoding="utf-8")

    done = ep.load_checkpoint(path)

    assert set(done) == {"a"}
    assert done["a"]["predicted"] == "falsa"


def test_load_checkpoint_missing_file_is_empty(tmp_path) -> None:
    assert ep.load_checkpoint(tmp_path / "nope.jsonl") == {}


def test_evaluate_pipeline_resumes_and_appends(tmp_path) -> None:
    path = tmp_path / "ckpt.jsonl"
    prior = {
        "text": "hecha",
        "expected": "falsa",
        "predicted": "falsa",
        "confidence": 0.9,
    }
    path.write_text(json.dumps(prior) + "\n", encoding="utf-8")

    samples: list[ep.Sample] = [
        {"text": "hecha", "expected": "falsa"},
        {"text": "nueva", "expected": "verdadera"},
    ]

    class FakeGraph:
        def __init__(self) -> None:
            self.seen: list[str] = []

        async def astream(
            self, state: dict, stream_mode: object = None, config: object = None
        ):
            self.seen.append(state["input_text"])
            yield (
                "values",
                {"verdict": _verdict("real", 0.7), "medical_explanation": "ok"},
            )

    graph = FakeGraph()
    rows = asyncio.run(ep.evaluate_pipeline(samples, graph, path))

    # The already evaluated sample is not run again.
    assert graph.seen == ["nueva"]
    # The sample order and the checkpoint's previous row are preserved.
    assert [r["text"] for r in rows] == ["hecha", "nueva"]
    assert rows[0]["predicted"] == "falsa"
    assert rows[1]["predicted"] == "verdadera"
    assert len(path.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_evaluate_pipeline_skips_failed_samples_for_retry(tmp_path) -> None:
    path = tmp_path / "ckpt.jsonl"
    samples: list[ep.Sample] = [
        {"text": "buena", "expected": "falsa"},
        {"text": "rompe", "expected": "verdadera"},
    ]

    class FakeGraph:
        async def astream(
            self, state: dict, stream_mode: object = None, config: object = None
        ):
            if state["input_text"] == "rompe":
                raise RuntimeError("boom")
            yield (
                "values",
                {"verdict": _verdict("fake", 0.8), "medical_explanation": "ok"},
            )

    rows = asyncio.run(ep.evaluate_pipeline(samples, FakeGraph(), path))

    # The failing sample is neither included nor persisted, so it is retried on resume.
    assert [r["text"] for r in rows] == ["buena"]
    assert len(path.read_text(encoding="utf-8").strip().splitlines()) == 1


def _run(**overrides: object) -> dict:
    run = {
        "provider": "mistral",
        "models": {"extractor": "m-ext", "judge": "m-judge"},
        "prompts": {"extractor": "v4", "judge": "v3"},
        "partition": "gold",
        "seed": 42,
        "git": "abc1234",
        "replay_evidence": None,
    }
    return {**run, **overrides}


def test_prepare_checkpoint_writes_a_header_that_is_not_a_row(tmp_path) -> None:
    path = tmp_path / "ckpt.jsonl"

    recorded = ep.prepare_checkpoint(path, _run())

    assert recorded == _run()
    assert ep.read_checkpoint_run(path) == _run()
    # The header does not count as an evaluated sample on resume.
    assert ep.load_checkpoint(path) == {}


def test_prepare_checkpoint_resumes_with_same_config_after_a_new_commit(
    tmp_path,
) -> None:
    path = tmp_path / "ckpt.jsonl"
    ep.prepare_checkpoint(path, _run())

    recorded = ep.prepare_checkpoint(path, _run(git="def5678", seed=7))

    # The original header is kept and not duplicated.
    assert recorded["git"] == "abc1234"
    assert len(path.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_prepare_checkpoint_rejects_resuming_with_another_prompt_version(
    tmp_path,
) -> None:
    path = tmp_path / "ckpt.jsonl"
    ep.prepare_checkpoint(path, _run())

    with pytest.raises(ep.CheckpointMismatchError, match="--fresh"):
        ep.prepare_checkpoint(path, _run(prompts={"extractor": "v4", "judge": "v4"}))


def test_prepare_checkpoint_rejects_a_legacy_checkpoint_without_header(
    tmp_path,
) -> None:
    path = tmp_path / "ckpt.jsonl"
    path.write_text(json.dumps({"text": "a", "predicted": "falsa"}) + "\n")

    with pytest.raises(ep.CheckpointMismatchError):
        ep.prepare_checkpoint(path, _run())


def test_prepare_checkpoint_rejects_resuming_with_another_evidence_source(
    tmp_path,
) -> None:
    path = tmp_path / "ckpt.jsonl"
    ep.prepare_checkpoint(path, _run())

    # Resuming while replaying Evidence would mix live and replayed rows.
    with pytest.raises(ep.CheckpointMismatchError):
        ep.prepare_checkpoint(path, _run(replay_evidence="/r/base.jsonl"))


def test_format_report_echoes_the_run_configuration() -> None:
    rows = [_row("falsa", "falsa")]

    report = ep.format_report(ep.compute_metrics(rows), rows, _run())

    assert "mistral · git abc1234" in report
    assert "judge=m-judge" in report
    assert "judge=v3" in report


def test_describe_run_records_every_prompt_version(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agents.main.configured_models", lambda: {"judge": "m-judge"}
    )
    monkeypatch.setattr(ep, "git_describe", lambda: "abc1234")
    prompts = ep.load_prompts()

    run = ep.describe_run(prompts, partition="gold", seed=42)

    assert run["prompts"] == {
        "extractor": prompts.extractor.version,
        "translator": prompts.translator.version,
        "judge": prompts.judge.version,
        "health_expert": prompts.health_expert.version,
    }
    assert run["models"] == {"judge": "m-judge"}
    assert run["git"] == "abc1234"


def _hit(title: str) -> dict:
    return {"title": title, "url": f"https://doi.org/{title}", "abstract": "resumen"}


def _call(source: str, query: str, hits: list[dict] | None) -> ep.EvidenceCall:
    return {"source": source, "query": query, "max_results": 3, "hits": hits}


def _unreachable(query: str, *, max_results: int) -> list[dict]:
    raise AssertionError("una búsqueda grabada no debe ir a la fuente")


def test_evidence_tape_records_live_hits_and_failures() -> None:
    tape = ep.EvidenceTape()

    def down(query: str, *, max_results: int) -> list[dict]:
        raise EvidenceRetrievalError("503")

    found = tape.wrap("pubmed", lambda query, *, max_results: [_hit("p")])
    assert found("q", max_results=3) == [_hit("p")]
    with pytest.raises(EvidenceRetrievalError):
        tape.wrap("europepmc", down)("q", max_results=3)

    assert tape.calls == [
        _call("pubmed", "q", [_hit("p")]),
        _call("europepmc", "q", None),
    ]
    assert tape.live == 2


def test_evidence_tape_replays_hits_and_failures_without_searching() -> None:
    tape = ep.EvidenceTape(
        [_call("pubmed", "q", [_hit("p")]), _call("cima", "ibuprofeno", None)]
    )

    assert tape.wrap("pubmed", _unreachable)("q", max_results=3) == [_hit("p")]
    # A recorded outage replays as an outage and is not retried live.
    with pytest.raises(EvidenceRetrievalError):
        tape.wrap("cima", _unreachable)("ibuprofeno", max_results=3)

    assert tape.live == 0
    assert tape.calls == [
        _call("pubmed", "q", [_hit("p")]),
        _call("cima", "ibuprofeno", None),
    ]


def test_evidence_tape_searches_live_what_the_recording_lacks() -> None:
    tape = ep.EvidenceTape([_call("pubmed", "q", [_hit("grabada")])])

    def live(query: str, *, max_results: int) -> list[dict]:
        return [_hit("viva")]

    # Another query, source or cap is not the recorded search.
    assert tape.wrap("pubmed", live)("otra", max_results=3) == [_hit("viva")]
    assert tape.wrap("europepmc", live)("q", max_results=3) == [_hit("viva")]
    assert tape.wrap("pubmed", live)("q", max_results=5) == [_hit("viva")]
    assert tape.live == 3


def test_evidence_tape_intercepts_every_search_of_the_investigator(
    monkeypatch,
) -> None:
    sources = ("europepmc", "pubmed", "openfda", "cima")
    for name in sources:
        monkeypatch.setattr(
            investigator_module,
            f"search_{name}",
            lambda query, *, max_results, name=name: [_hit(f"{name}:{query}")],
        )
    live = {name: getattr(investigator_module, f"search_{name}") for name in sources}
    state = {
        "claims": [
            Claim(
                index=0,
                text="El ibuprofeno daña los riñones",
                text_en="Ibuprofen damages the kidneys",
                query="ibuprofen kidney damage",
                drug_term="ibuprofeno",
            )
        ]
    }

    tape = ep.EvidenceTape()
    with tape.install():
        claims = investigator_module.gather_evidence(state["claims"])

    assert sorted((call["source"], call["query"]) for call in tape.calls) == [
        ("cima", "ibuprofeno"),
        ("europepmc", "ibuprofen kidney damage"),
        ("openfda", "ibuprofen kidney damage"),
        ("pubmed", "ibuprofen kidney damage"),
    ]
    # On leaving the block the investigator uses its own searches again.
    assert all(
        getattr(investigator_module, f"search_{name}") is live[name] for name in sources
    )

    for name in sources:
        monkeypatch.setattr(investigator_module, f"search_{name}", _unreachable)
    replay = ep.EvidenceTape(tape.calls)
    with replay.install():
        replayed = investigator_module.gather_evidence(state["claims"])

    assert replayed == claims
    assert replay.live == 0


def test_evaluate_pipeline_records_evidence_that_a_later_run_replays(
    monkeypatch, tmp_path
) -> None:
    samples: list[ep.Sample] = [{"text": "afirmacion", "expected": "falsa"}]

    class FakeGraph:
        def __init__(self) -> None:
            self.hits: list[dict] = []

        async def astream(
            self, state: dict, stream_mode: object = None, config: object = None
        ):
            self.hits = investigator_module.search_pubmed("q", max_results=3)
            yield ("values", {"verdict": _verdict("fake", 0.8)})

    monkeypatch.setattr(
        investigator_module,
        "search_pubmed",
        lambda query, *, max_results: [_hit("indice de ayer")],
    )
    base = tmp_path / "base.jsonl"
    asyncio.run(ep.evaluate_pipeline(samples, FakeGraph(), base))
    recorded = ep.load_recorded_evidence(base)
    assert recorded == {"afirmacion": [_call("pubmed", "q", [_hit("indice de ayer")])]}

    # The index changes between runs, so the variant must see the base's Evidence.
    monkeypatch.setattr(
        investigator_module,
        "search_pubmed",
        lambda query, *, max_results: [_hit("indice de hoy")],
    )
    graph = FakeGraph()
    rows = asyncio.run(ep.evaluate_pipeline(samples, graph, replay=recorded))

    assert graph.hits == [_hit("indice de ayer")]
    assert rows[0]["evidence_live"] == 0


def test_load_recorded_evidence_skips_rows_recorded_before_the_tape(tmp_path) -> None:
    path = tmp_path / "ckpt.jsonl"
    records = [
        {"run": _run()},
        {"text": "vieja", "predicted": "falsa"},
        {"text": "nueva", "evidence": [_call("pubmed", "q", None)]},
    ]
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )

    assert ep.load_recorded_evidence(path) == {"nueva": [_call("pubmed", "q", None)]}


def test_format_report_says_how_much_evidence_was_replayed() -> None:
    rows: list[ep.EvalRow] = [
        {
            **_row("falsa", "falsa"),
            "evidence": [_call("pubmed", "q", []), _call("cima", "x", [])],
            "evidence_live": 1,
        },
        _row("verdadera", "verdadera"),
    ]
    run = _run(replay_evidence="/results/base.jsonl")

    report = ep.format_report(ep.compute_metrics(rows), rows, run)

    assert "Evidencia : 1/2 búsquedas reproducidas de base.jsonl" in report
    assert "Evidencia" not in ep.format_report(ep.compute_metrics(rows), rows, _run())


class _Item:
    """A Langfuse dataset item, with the input and expected output the uploader gives it."""

    def __init__(self, text: str) -> None:
        self.input = {"text": text}
        self.expected_output = {"label": "falsa"}


class _FakeLangfuse:
    """Serve a dataset and run experiments on their own event loop, logging task errors as Langfuse does."""

    def __init__(self, texts: list[str]) -> None:
        self.dataset = SimpleNamespace(items=[_Item(text) for text in texts])
        self.experiments: list[dict] = []
        self.scores: dict[str, dict] = {}
        self.flushed = False

    def get_dataset(self, name: str) -> SimpleNamespace:
        return self.dataset

    def run_experiment(
        self, *, data: list, task, evaluators: list, **kwargs
    ) -> SimpleNamespace:
        async def run_item(item: _Item) -> tuple:
            try:
                output = await task(item=item)
            except Exception as exc:
                return f"Error: {exc}", []
            scores = [
                (e.name, e.value)
                for evaluator in evaluators
                for e in evaluator(output=output, expected_output=item.expected_output)
            ]
            return output, scores

        [(output, scores)] = [asyncio.run(run_item(item)) for item in data]
        self.experiments.append(
            {
                "item": data[0].input["text"],
                "output": output,
                "scores": scores,
                **kwargs,
            }
        )
        return SimpleNamespace(experiment_id=f"exp:{kwargs['run_name']}")

    def create_score(self, *, score_id: str, **fields) -> None:
        self.scores[score_id] = fields

    def flush(self) -> None:
        self.flushed = True


class _VerdictGraph:
    async def astream(
        self, state: dict, stream_mode: object = None, config: object = None
    ):
        if state["input_text"] == "rota":
            raise RuntimeError("caída")
        yield ("values", {"verdict": _verdict("fake", 0.8)})


def test_a_langfuse_run_links_each_pending_sample_to_its_dataset_item(tmp_path) -> None:
    path = tmp_path / "ckpt.jsonl"
    path.write_text(
        json.dumps({"text": "vieja", "predicted": "falsa"}) + "\n", encoding="utf-8"
    )
    samples: list[ep.Sample] = [
        {"text": text, "expected": "falsa"} for text in ("vieja", "nueva", "rota")
    ]
    client = _FakeLangfuse(["vieja", "nueva", "rota", "otra"])
    experiment = ep.LangfuseExperiment(
        client,
        "gold-es",
        samples,
        "mistral-v2",
        {"provider": "mistral", "models": {"judge": "m"}, "git": None},
    )

    rows = asyncio.run(
        ep.evaluate_pipeline(samples, _VerdictGraph(), path, run_pending=experiment)
    )

    nueva, rota = client.experiments
    # Only the pending samples run, each under its own item.
    assert (nueva["item"], rota["item"]) == ("nueva", "rota")
    assert nueva["output"] == {"label": "falsa", "confidence": 0.8}
    assert nueva["scores"] == [
        ("abstained", 0.0),
        ("confidence", 0.8),
        ("correct", 1.0),
    ]
    # A failed sample shows as an error item, and the run carries on.
    assert rota["output"].startswith("Error:")
    assert rota["scores"] == []
    assert nueva["run_name"] == "mistral-v2"
    assert nueva["metadata"] == {"provider": "mistral", "models": '{"judge": "m"}'}
    assert experiment.experiment_id == "exp:mistral-v2"
    # The checkpoint still keeps the rows, so the run resumes and reports as before.
    assert [row["text"] for row in rows] == ["vieja", "nueva"]
    assert "nueva" in ep.load_checkpoint(path)


def test_a_langfuse_run_stops_on_an_error_langfuse_would_only_log() -> None:
    samples: list[ep.Sample] = [
        {"text": text, "expected": "falsa"} for text in ("una", "otra")
    ]
    client = _FakeLangfuse(["una", "otra"])
    experiment = ep.LangfuseExperiment(client, "gold-es", samples, "r", {})

    async def broken(sample: ep.Sample) -> ep.EvalRow | None:
        raise KeyError("verdict")

    with pytest.raises(KeyError, match="verdict"):
        asyncio.run(experiment(samples, broken))

    # The bug surfaces at the first sample instead of failing every one.
    assert [run["item"] for run in client.experiments] == ["una"]


def test_cancelling_a_langfuse_run_lets_the_running_sample_finish() -> None:
    samples: list[ep.Sample] = [{"text": "una", "expected": "falsa"}]
    started = threading.Event()
    finished: list[bool] = []

    class _SlowLangfuse(_FakeLangfuse):
        def run_experiment(self, **kwargs) -> SimpleNamespace:
            started.set()
            time.sleep(0.2)
            finished.append(True)
            return SimpleNamespace(experiment_id="exp")

    experiment = ep.LangfuseExperiment(
        _SlowLangfuse(["una"]), "gold-es", samples, "r", {}
    )

    async def cancel_mid_sample() -> None:
        running = asyncio.create_task(experiment(samples, None))  # type: ignore[arg-type]
        await asyncio.to_thread(started.wait)
        running.cancel()
        with pytest.raises(asyncio.CancelledError):
            await running

    asyncio.run(cancel_mid_sample())

    # The checkpoint closes only after the thread's sample is done.
    assert finished == [True]


def test_a_langfuse_run_refuses_samples_its_dataset_lacks() -> None:
    samples: list[ep.Sample] = [{"text": "nueva", "expected": "falsa"}]

    with pytest.raises(ep.MissingDatasetItemsError, match="1 muestras"):
        ep.LangfuseExperiment(_FakeLangfuse(["otra"]), "gold-es", samples, "r", {})


def test_a_langfuse_run_needs_a_partition_with_a_dataset(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv", ["evaluate_pipeline", "--partition", "train", "--langfuse-run", "r"]
    )

    with pytest.raises(SystemExit, match="--langfuse-run"):
        ep.main()


def test_prepare_checkpoint_rejects_resuming_under_another_langfuse_run(
    tmp_path,
) -> None:
    path = tmp_path / "ckpt.jsonl"
    ep.prepare_checkpoint(path, _run())

    # Its run scores would otherwise count rows the experiment never ran.
    with pytest.raises(ep.CheckpointMismatchError):
        ep.prepare_checkpoint(path, _run(langfuse_run="mistral-v2"))


def test_a_langfuse_run_scores_each_sample_as_compute_metrics_counts_it() -> None:
    falsa = {"label": "falsa"}
    verdadera = {"label": "verdadera"}

    def scores(output: dict | None, expected: dict) -> dict:
        return {
            e.name: e.value
            for e in ep.score_sample(output=output, expected_output=expected)
        }

    assert scores({"label": "falsa", "confidence": 0.8}, falsa) == {
        "abstained": 0.0,
        "confidence": 0.8,
        "correct": 1.0,
    }
    assert scores({"label": "falsa", "confidence": 0.7}, verdadera)["correct"] == 0.0
    # An abstention scores no correctness.
    assert scores({"label": "incierta", "confidence": 0.0}, falsa) == {
        "abstained": 1.0,
        "confidence": 0.0,
    }
    assert scores({"label": None, "confidence": 0.0}, falsa)["abstained"] == 1.0


def test_a_resumed_langfuse_run_updates_its_metrics_in_the_same_experiment() -> None:
    samples: list[ep.Sample] = [{"text": "nueva", "expected": "falsa"}]
    client = _FakeLangfuse(["nueva"])
    metrics = {name: 0.5 for name in ep.RUN_SCORES}

    async def evaluate(sample: ep.Sample) -> ep.EvalRow:
        return {**_row("falsa", "falsa"), "text": sample["text"]}

    first = ep.LangfuseExperiment(client, "gold-es", samples, "mistral-v2", {})
    asyncio.run(first(samples, evaluate))
    first.record_metrics(metrics)
    resumed = ep.LangfuseExperiment(client, "gold-es", samples, "mistral-v2", {})
    asyncio.run(resumed(samples, evaluate))
    resumed.record_metrics({**metrics, "accuracy": 0.75})

    assert len(client.scores) == len(ep.RUN_SCORES)
    assert client.scores["exp:mistral-v2-accuracy"] == {
        "dataset_run_id": "exp:mistral-v2",
        "name": "accuracy",
        "value": 0.75,
    }
    assert client.flushed


def test_a_langfuse_run_with_nothing_pending_scores_no_experiment() -> None:
    client = _FakeLangfuse(["nueva"])
    experiment = ep.LangfuseExperiment(client, "gold-es", [], "r", {})

    asyncio.run(experiment([], None))  # type: ignore[arg-type]
    experiment.record_metrics({name: 1.0 for name in ep.RUN_SCORES})

    assert client.experiments == []
    assert client.scores == {}


def test_main_turns_the_explanation_off_even_with_settings_already_loaded(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("HEALTH_EXPERT_EXPLANATION_ENABLED", "true")
    get_settings.cache_clear()
    assert get_settings().health_expert_explanation_enabled

    class Stop(Exception):
        pass

    def stop() -> None:
        raise Stop

    monkeypatch.setattr(ep, "ensure_llm_available", stop)
    monkeypatch.setattr(
        "sys.argv", ["evaluate_pipeline", "--checkpoint", str(tmp_path / "c.jsonl")]
    )

    with pytest.raises(Stop):
        ep.main()

    assert not get_settings().health_expert_explanation_enabled
    get_settings.cache_clear()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
