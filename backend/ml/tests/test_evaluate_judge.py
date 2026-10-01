"""Tests de la evaluación del juez sobre casos grabados, con el juez simulado."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.claim import Claim, with_hits
from ml import evaluate_judge as ej


def _hit(key: str) -> dict:
    return {
        "title": f"Estudio {key}",
        "url": f"https://e.org/{key}",
        "source": "BMJ",
        "year": "2021",
        "abstract": f"Resumen {key}.",
    }


def _call(source: str, *keys: str, down: bool = False) -> dict:
    return {
        "source": source,
        "query": "q",
        "max_results": 3,
        "hits": None if down else [_hit(key) for key in keys],
    }


def _row(text: str, expected: str, translated: list[str], evidence: list[dict]) -> dict:
    return {
        "text": text,
        "expected": expected,
        "extracted": [f"{text} (extraída)" for _ in translated],
        "translated": translated,
        "evidence": evidence,
    }


def _write(path: Path, *rows: dict) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _case(text: str, expected: str, *keys: str) -> ej.JudgeCase:
    """Caso cuya afirmación en inglés es ``<text> EN``, con una fuente candidata por clave."""
    claim = with_hits(
        Claim(index=0, text=text, text_en=f"{text} EN"), [_hit(k) for k in keys]
    )
    return ej.JudgeCase(text=text, expected=expected, claim=claim)


def test_load_cases_rebuilds_the_candidates_in_the_investigators_order(tmp_path):
    recorded = _write(
        tmp_path / "pipeline.jsonl",
        {"run": {"provider": "ollama"}},
        _row(
            "A",
            "falsa",
            ["A EN"],
            # Grabadas en el orden en que terminaron los hilos, no en el de las fuentes.
            [
                _call("cima", "C1"),
                _call("pubmed", "P1", "E1"),
                _call("openfda", down=True),
                _call("europepmc", "E1", "E2"),
            ],
        ),
    )

    (case,) = ej.load_cases(recorded)

    assert (case.text, case.expected) == ("A", "falsa")
    assert (case.claim.text, case.claim.text_en) == ("A (extraída)", "A EN")
    # Europe PMC, PubMed, openFDA y CIMA; una URL repetida cuenta una vez.
    assert [item.url for item in case.claim.evidence] == [
        "https://e.org/E1",
        "https://e.org/E2",
        "https://e.org/P1",
        "https://e.org/C1",
    ]


@pytest.mark.parametrize(
    "row",
    [
        _row("varias", "falsa", ["X EN", "Y EN"], [_call("europepmc", "E1")]),
        _row("sin traducción", "falsa", [""], [_call("europepmc", "E1")]),
        _row("sin fuentes", "falsa", ["Z EN"], [_call("europepmc")]),
        _row("fuentes caídas", "falsa", ["Z EN"], [_call("pubmed", down=True)]),
        {"text": "sin evidencia grabada", "expected": "falsa", "translated": ["Z EN"]},
    ],
    ids=["several-claims", "untranslated", "no-hits", "sources-down", "unrecorded"],
)
def test_load_cases_skips_rows_without_a_single_judgeable_claim(tmp_path, row):
    assert ej.load_cases(_write(tmp_path / "pipeline.jsonl", row)) == []


def _fake_judge(answers: dict[str, tuple | None], calls: list[str]):
    def judge(prompt_text, claim, evidence):
        calls.append(claim)
        return answers[claim]

    return judge


def test_judge_cases_saves_each_answer_with_the_verdict_it_decides(
    tmp_path, monkeypatch
):
    calls: list[str] = []
    monkeypatch.setattr(
        ej,
        "judge_stances",
        _fake_judge(
            {
                "A EN": ("supports", "supports"),
                "B EN": ("contradicts", "contradicts"),
                "C EN": None,
            },
            calls,
        ),
    )
    checkpoint = tmp_path / "judge.jsonl"
    cases = [
        _case("A", "verdadera", "1", "2"),
        _case("B", "verdadera", "3", "4"),
        _case("C", "falsa", "5"),
    ]

    rows = ej.judge_cases(cases, "prompt", checkpoint)

    assert [(r["text"], r["stances"], r["predicted"]) for r in rows] == [
        ("A", ["supports", "supports"], "verdadera"),
        ("B", ["contradicts", "contradicts"], "falsa"),
    ]
    # Un caso sin respuesta no queda guardado: se reintenta al reanudar.
    saved = [json.loads(line)["text"] for line in checkpoint.read_text().splitlines()]
    assert saved == ["A", "B"]


def test_judge_cases_resumes_only_the_cases_without_a_saved_answer(
    tmp_path, monkeypatch
):
    checkpoint = tmp_path / "judge.jsonl"
    cases = [_case("A", "verdadera", "1"), _case("B", "falsa", "2")]
    first: list[str] = []
    monkeypatch.setattr(
        ej, "judge_stances", _fake_judge({"A EN": ("supports",), "B EN": None}, first)
    )
    ej.judge_cases(cases, "prompt", checkpoint)

    second: list[str] = []
    monkeypatch.setattr(
        ej, "judge_stances", _fake_judge({"B EN": ("contradicts",)}, second)
    )
    rows = ej.judge_cases(cases, "prompt", checkpoint)

    assert second == ["B EN"]
    assert [r["text"] for r in rows] == ["A", "B"]


def test_judge_cases_stops_starting_cases_once_the_time_budget_runs_out(
    tmp_path, monkeypatch
):
    calls: list[str] = []
    monkeypatch.setattr(
        ej,
        "judge_stances",
        _fake_judge({"A EN": ("supports",), "B EN": ("supports",)}, calls),
    )
    # El plazo se fija en t=0; el primer caso empieza en t=0 y el segundo en t=61 s.
    clock = iter([0.0, 0.0, 61.0])
    monkeypatch.setattr(ej, "time", lambda: next(clock))

    rows = ej.judge_cases(
        [_case("A", "verdadera", "1"), _case("B", "verdadera", "2")],
        "prompt",
        tmp_path / "judge.jsonl",
        minutes=1,
    )

    assert calls == ["A EN"]
    assert [r["text"] for r in rows] == ["A"]


def _judged(expected: str, predicted: str, *stances: str) -> ej.JudgeRow:
    return {
        "text": f"{expected}-{predicted}-{len(stances)}",
        "expected": expected,
        "stances": list(stances),
        "predicted": predicted,
    }


def test_compute_judge_metrics_scores_firm_verdicts_and_splits_stances_by_label():
    rows = [
        _judged("verdadera", "verdadera", "supports", "supports", "unrelated"),
        _judged("falsa", "verdadera", "supports", "inconclusive"),
        _judged("falsa", "falsa", "contradicts", "contradicts"),
        _judged("verdadera", "falsa", "contradicts"),
        _judged("falsa", "incierta", "inconclusive"),
    ]

    metrics = ej.compute_judge_metrics(rows)

    assert (metrics["judged"], metrics["firm"], metrics["correct"]) == (5, 4, 2)
    assert metrics["accuracy"] == 0.5
    assert (metrics["false_as_true"], metrics["true_as_false"]) == (1, 1)
    assert metrics["stances"]["falsa"] == {
        "supports": 1,
        "inconclusive": 2,
        "contradicts": 2,
    }


def test_format_judge_report_names_the_judge_and_the_stance_ratio():
    rows = [
        _judged("falsa", "verdadera", "supports", "supports", "contradicts"),
        _judged("verdadera", "verdadera", "supports"),
    ]
    run = {
        "provider": "mistral",
        "models": {"judge": "mistral-small-latest"},
        "prompts": {"judge": "v6"},
        "replay_evidence": "/results/base.jsonl",
        "git": "abc1234",
    }

    report = ej.format_judge_report(ej.compute_judge_metrics(rows), run, cases=3)

    assert "mistral-small-latest · prompt v6" in report
    assert "base.jsonl" in report
    assert "Juzgados  : 2/3" in report
    assert "falsa      supports    2 · contradicts    1" in report
    assert "s:c 2.00" in report
    # Sin ningún contradicts la razón no tiene denominador.
    assert "s:c ∞" in report


def test_main_judges_the_recorded_cases_and_records_the_judge_in_the_header(
    tmp_path, monkeypatch, capsys
):
    recorded = _write(
        tmp_path / "pipeline.jsonl",
        _row("A", "falsa", ["A EN"], [_call("europepmc", "E1")]),
    )
    checkpoint = tmp_path / "judge.jsonl"
    monkeypatch.setattr(
        sys,
        "argv",
        ["evaluate_judge", "--cases", str(recorded), "--checkpoint", str(checkpoint)],
    )
    monkeypatch.setattr(ej, "ensure_llm_available", lambda: None)
    monkeypatch.setattr(ej, "git_describe", lambda: "abc1234")
    monkeypatch.setattr(
        ej, "get_settings", lambda: SimpleNamespace(llm_provider_name=lambda: "ollama")
    )
    monkeypatch.setattr(ej, "configured_models", lambda: {"judge": "gemma4:12b"})
    monkeypatch.setattr(
        ej, "judge_stances", _fake_judge({"A EN": ("contradicts",)}, [])
    )

    metrics = ej.main()

    header = json.loads(checkpoint.read_text().splitlines()[0])["run"]
    assert header["models"] == {"judge": "gemma4:12b"}
    assert header["replay_evidence"] == str(recorded.resolve())
    assert (metrics["firm"], metrics["correct"]) == (1, 1)
    assert "gemma4:12b" in capsys.readouterr().out


def test_main_refuses_to_judge_into_the_recorded_checkpoint(tmp_path, monkeypatch):
    recorded = _write(
        tmp_path / "pipeline.jsonl",
        _row("A", "falsa", ["A EN"], [_call("europepmc", "E1")]),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["evaluate_judge", "--cases", str(recorded), "--checkpoint", str(recorded)],
    )

    with pytest.raises(SystemExit):
        ej.main()
