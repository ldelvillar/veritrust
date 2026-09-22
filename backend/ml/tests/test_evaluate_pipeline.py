"""Tests unitarios para la evaluación del pipeline multiagente."""

import asyncio
import json

import pandas as pd
import pytest

from app.agents import investigator as investigator_module
from app.utils.evidence import EvidenceRetrievalError
from ml import evaluate_pipeline as ep


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
        _row("falsa", None),  # sin afirmaciones -> excluida
    ]
    metrics = ep.compute_metrics(rows)

    assert (metrics["tp"], metrics["fn"], metrics["fp"], metrics["tn"]) == (1, 1, 1, 1)
    assert metrics["evaluated"] == 4
    assert metrics["skipped"] == 1
    assert metrics["accuracy"] == 0.5


def test_compute_metrics_treats_incierta_as_abstention() -> None:
    rows = [
        _row("falsa", "falsa"),  # tp
        _row("verdadera", "incierta"),  # abstención -> no puntúa
        _row("falsa", "incierta"),  # abstención -> no puntúa
        _row("verdadera", None),  # sin afirmaciones -> excluida
    ]
    metrics = ep.compute_metrics(rows)

    assert (metrics["tp"], metrics["fn"], metrics["fp"], metrics["tn"]) == (1, 0, 0, 0)
    assert metrics["evaluated"] == 1
    assert metrics["uncertain"] == 2
    assert metrics["skipped"] == 1
    # Abstenerse no penaliza: el único veredicto firme es correcto.
    assert metrics["accuracy"] == 1.0
    # La cobertura sí refleja las abstenciones: 1 firme de 3 con afirmaciones.
    assert metrics["coverage"] == pytest.approx(1 / 3)


def test_reconstruct_fake_avg_inverts_coverage_attenuation() -> None:
    # fake_avg 0.62 reportada como falsa con cobertura 0.5: 0.62 * 0.875 = 0.5425.
    assert ep._reconstruct_fake_avg("falsa", 0.62 * 0.875, 0.5) == pytest.approx(0.62)


def test_reconstruct_fake_avg_mirrors_non_fake_labels() -> None:
    # verdadera/incierta reportan 1 - fake_avg; cobertura completa no atenúa.
    assert ep._reconstruct_fake_avg("verdadera", 0.8, 1.0) == pytest.approx(0.2)
    assert ep._reconstruct_fake_avg("incierta", 0.55, 1.0) == pytest.approx(0.45)


def test_reconstruct_fake_avg_is_none_without_label() -> None:
    assert ep._reconstruct_fake_avg("", 0.0, 0.0) is None


def test_format_report_excludes_abstentions_from_errors() -> None:
    rows = [_row("falsa", "incierta"), _row("verdadera", "verdadera")]
    metrics = ep.compute_metrics(rows)

    report = ep.format_report(metrics, rows)

    assert "Errores de clasificación" not in report
    assert "Veredicto incierto : 1" in report


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
            # 0->verdadera, 1->falsa; NEI (2) se descarta
            "label": [0, 0, 0, 1, 1, 1, 2, 2],
        }
    )
    monkeypatch.setattr(ep, "load_dataset", lambda partition: df.copy())

    samples = ep.load_samples(partition="validation", limit=4, seed=1)

    assert len(samples) == 4
    labels = {s["expected"] for s in samples}
    assert labels <= {"verdadera", "falsa"}
    # La clase 'NEI' (2) nunca debe aparecer.
    assert all(s["text"] not in {"c6", "c7"} for s in samples)


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

    # ainvoke_graph consume el grafo por streaming (astream), no ainvoke.
    class FakeGraph:
        async def astream(self, state: dict, stream_mode: object = None):
            if "sin" in state["input_text"]:
                yield (
                    "values",
                    {"label": "", "confidence": 0.0, "medical_explanation": ""},
                )
            else:
                yield (
                    "values",
                    {
                        "label": "falsa",
                        "confidence": 0.8,
                        "medical_explanation": "informe",
                    },
                )

    rows = asyncio.run(ep.evaluate_pipeline(samples, FakeGraph()))

    assert rows[0]["predicted"] == "falsa"
    assert rows[1]["predicted"] is None
    assert rows[1]["confidence"] == 0.0


def test_format_report_lists_misclassifications() -> None:
    rows = [_row("falsa", "verdadera", 0.7), _row("verdadera", "verdadera")]
    metrics = ep.compute_metrics(rows)

    report = ep.format_report(metrics, rows)

    assert "Evaluación del pipeline multiagente" in report
    assert "Errores de clasificación (1)" in report


def test_build_initial_state_has_pipeline_keys() -> None:
    state = ep._build_initial_state("hola")

    assert state["input_text"] == "hola"
    assert state["extracted_statements"] == []
    assert state["label"] == ""


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

        async def astream(self, state: dict, stream_mode: object = None):
            self.seen.append(state["input_text"])
            yield (
                "values",
                {"label": "verdadera", "confidence": 0.7, "medical_explanation": "ok"},
            )

    graph = FakeGraph()
    rows = asyncio.run(ep.evaluate_pipeline(samples, graph, path))

    # La muestra ya evaluada no se vuelve a ejecutar.
    assert graph.seen == ["nueva"]
    # Se preserva el orden de las muestras y la fila previa del checkpoint.
    assert [r["text"] for r in rows] == ["hecha", "nueva"]
    assert rows[0]["predicted"] == "falsa"
    assert rows[1]["predicted"] == "verdadera"
    # La nueva fila se anexó al checkpoint (2 líneas en total).
    assert len(path.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_evaluate_pipeline_skips_failed_samples_for_retry(tmp_path) -> None:
    path = tmp_path / "ckpt.jsonl"
    samples: list[ep.Sample] = [
        {"text": "buena", "expected": "falsa"},
        {"text": "rompe", "expected": "verdadera"},
    ]

    class FakeGraph:
        async def astream(self, state: dict, stream_mode: object = None):
            if state["input_text"] == "rompe":
                raise RuntimeError("boom")
            yield (
                "values",
                {"label": "falsa", "confidence": 0.8, "medical_explanation": "ok"},
            )

    rows = asyncio.run(ep.evaluate_pipeline(samples, FakeGraph(), path))

    # La muestra que falla no se incluye ni se persiste: se reintentará al reanudar.
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
    # La cabecera no cuenta como muestra evaluada al reanudar.
    assert ep.load_checkpoint(path) == {}


def test_prepare_checkpoint_resumes_with_same_config_after_a_new_commit(
    tmp_path,
) -> None:
    path = tmp_path / "ckpt.jsonl"
    ep.prepare_checkpoint(path, _run())

    recorded = ep.prepare_checkpoint(path, _run(git="def5678", seed=7))

    # Se conserva la cabecera original y no se duplica.
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

    # Reanudar reproduciendo evidencia mezclaría filas en vivo y reproducidas.
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
    monkeypatch.setattr(ep, "_git_describe", lambda: "abc1234")
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
    # Una caída grabada se reproduce como caída, no se reintenta en vivo.
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

    # Otra consulta, otra fuente u otra cota no son la búsqueda grabada.
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
        "translated_statements": ["Ibuprofen damages the kidneys"],
        "search_queries": ["ibuprofen kidney damage"],
        "drug_terms": ["ibuprofeno"],
    }

    tape = ep.EvidenceTape()
    with tape.install():
        _, claims = investigator_module.gather_evidence(state)

    assert sorted((call["source"], call["query"]) for call in tape.calls) == [
        ("cima", "ibuprofeno"),
        ("europepmc", "ibuprofen kidney damage"),
        ("openfda", "ibuprofen kidney damage"),
        ("pubmed", "ibuprofen kidney damage"),
    ]
    # Al salir del bloque el investigador vuelve a usar sus búsquedas.
    assert all(
        getattr(investigator_module, f"search_{name}") is live[name] for name in sources
    )

    for name in sources:
        monkeypatch.setattr(investigator_module, f"search_{name}", _unreachable)
    replay = ep.EvidenceTape(tape.calls)
    with replay.install():
        _, replayed = investigator_module.gather_evidence(state)

    assert replayed == claims
    assert replay.live == 0


def test_evaluate_pipeline_records_evidence_that_a_later_run_replays(
    monkeypatch, tmp_path
) -> None:
    samples: list[ep.Sample] = [{"text": "afirmacion", "expected": "falsa"}]

    class FakeGraph:
        def __init__(self) -> None:
            self.hits: list[dict] = []

        async def astream(self, state: dict, stream_mode: object = None):
            self.hits = investigator_module.search_pubmed("q", max_results=3)
            yield ("values", {"label": "falsa", "confidence": 0.8})

    monkeypatch.setattr(
        investigator_module,
        "search_pubmed",
        lambda query, *, max_results: [_hit("indice de ayer")],
    )
    base = tmp_path / "base.jsonl"
    asyncio.run(ep.evaluate_pipeline(samples, FakeGraph(), base))
    recorded = ep.load_recorded_evidence(base)
    assert recorded == {"afirmacion": [_call("pubmed", "q", [_hit("indice de ayer")])]}

    # El índice cambia entre corridas: la variante debe ver la evidencia de la base.
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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
