"""Tests of the judge evaluation on recorded cases, with the judge mocked."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.claim import Claim, with_hits
from evaluation import evaluate_judge as ej
from evaluation import load_data


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
    """Case whose English claim is ``<text> EN``, with one candidate Source per key."""
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
            # Recorded in the order the threads finished, not in source order.
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
    # Europe PMC, PubMed, openFDA and CIMA, where a repeated URL counts once.
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

    assert [(r["text"], r["claim"], r["predicted"]) for r in rows] == [
        ("A", "A", "verdadera"),
        ("B", "B", "falsa"),
    ]
    # Each Stance stays with its Source's URL, not by position.
    assert rows[1]["sources"] == [
        {"url": "https://e.org/3", "stance": "contradicts"},
        {"url": "https://e.org/4", "stance": "contradicts"},
    ]
    # An unanswered case is not saved, so it is retried on resume.
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
    # The deadline is set at t=0, the first case starts at t=0 and the second at t=61 s.
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
    text = f"{expected}-{predicted}-{len(stances)}"
    return {
        "text": text,
        "claim": text,
        "expected": expected,
        "sources": [
            {"url": f"https://e.org/{i}", "stance": stance}
            for i, stance in enumerate(stances)
        ],
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
        "replay_evidence": ["/results/base.jsonl", "/results/neg.jsonl"],
        "git": "abc1234",
    }

    report = ej.format_judge_report(ej.compute_judge_metrics(rows), run, cases=3)

    assert "mistral-small-latest · prompt v6" in report
    assert "base.jsonl, neg.jsonl" in report
    assert "Juzgados  : 2/3" in report
    assert "falsa      supports    2 · contradicts    1" in report
    assert "s:c 2.00" in report
    # Without any contradicts the ratio has no denominator.
    assert "s:c ∞" in report


def _offline(monkeypatch) -> None:
    """Replace what main queries outside the process: the LLM, git and the configuration."""
    monkeypatch.setattr(ej, "ensure_llm_available", lambda: None)
    monkeypatch.setattr(ej, "git_describe", lambda: "abc1234")
    monkeypatch.setattr(
        ej, "get_settings", lambda: SimpleNamespace(llm_provider_name=lambda: "ollama")
    )
    monkeypatch.setattr(ej, "configured_models", lambda: {"judge": "gemma4:12b"})


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
    _offline(monkeypatch)
    monkeypatch.setattr(
        ej, "judge_stances", _fake_judge({"A EN": ("contradicts",)}, [])
    )

    metrics = ej.main()

    header = json.loads(checkpoint.read_text().splitlines()[0])["run"]
    assert header["models"] == {"judge": "gemma4:12b"}
    assert header["replay_evidence"] == [str(recorded.resolve())]
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


def _label(
    claim: str, key: str, label: str, stance: str, reason: str
) -> ej.StanceLabel:
    return ej.StanceLabel(
        claim=claim,
        url=f"https://e.org/{key}",
        label=label,
        stance=stance,
        reason=reason,
    )


def test_score_stances_separates_loose_strict_and_inverted_stances():
    row = _judged(
        "verdadera", "falsa", "contradicts", "supports", "inconclusive", "supports"
    )
    claim = row["claim"]
    labels = [
        # Unfounded firm Stance, towards the wrong Verdict.
        _label(claim, "0", "verdadera", "inconclusive", "off_point"),
        # Unfounded firm Stance, in the label's direction.
        _label(claim, "1", "verdadera", "unrelated", "indirect"),
        _label(claim, "2", "verdadera", "supports", "on_point"),
        _label(claim, "3", "verdadera", "contradicts", "on_point"),
        # A Source the judge did not see is not scored.
        _label(claim, "9", "verdadera", "supports", "on_point"),
    ]

    scores = ej.score_stances([row], labels)

    assert (scores["labels"], scores["scored"], scores["judge_firm"]) == (5, 4, 3)
    assert (scores["loose"], scores["loose_wrong_way"]) == (2, 1)
    assert scores["loose_reasons"] == {"off_point": 1, "indirect": 1}
    assert (scores["gold_firm"], scores["strict"], scores["polarity"]) == (2, 1, 1)


def test_main_judges_several_checkpoints_and_scores_the_stance_labels(
    tmp_path, monkeypatch, capsys
):
    gold = _write(
        tmp_path / "gold.jsonl",
        _row("A", "verdadera", ["A EN"], [_call("europepmc", "E1", "E2")]),
    )
    negations = _write(
        tmp_path / "negations.jsonl",
        _row("B", "falsa", ["B EN"], [_call("pubmed", "P1")]),
    )
    labels = _write(
        tmp_path / "labels.jsonl",
        {
            "claim": "A (extraída)",
            "url": "https://e.org/E1",
            "label": "verdadera",
            "stance": "supports",
            "reason": "on_point",
        },
        {
            "claim": "A (extraída)",
            "url": "https://e.org/E2",
            "label": "verdadera",
            "stance": "unrelated",
            "reason": "off_point",
        },
        {
            "claim": "B (extraída)",
            "url": "https://e.org/P1",
            "label": "falsa",
            "stance": "contradicts",
            "reason": "on_point",
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate_judge",
            "--cases",
            str(gold),
            str(negations),
            "--checkpoint",
            str(tmp_path / "judge.jsonl"),
            "--stance-labels",
            str(labels),
        ],
    )
    _offline(monkeypatch)
    monkeypatch.setattr(
        ej,
        "judge_stances",
        _fake_judge({"A EN": ("supports", "supports"), "B EN": ("contradicts",)}, []),
    )

    metrics = ej.main()

    assert metrics["judged"] == 2
    scores = metrics["stance_labels"]
    assert (scores["scored"], scores["judge_firm"], scores["loose"]) == (3, 3, 1)
    out = capsys.readouterr().out
    assert "gold.jsonl, negations.jsonl" in out
    assert "Firmes sin base     : 1/3 (33.3%) · 0 hacia el veredicto equivocado" in out
    assert "Descartes de más    : 0/2 (0.0%)" in out


def test_stance_labels_give_an_on_point_reason_only_to_firm_stances():
    path = Path(load_data.BASE_DIR) / "data" / "judge_stances_es.jsonl"
    labels = ej.load_stance_labels(path)

    assert len({(label.claim, label.url) for label in labels}) == len(labels)
    for label in labels:
        assert label.stance in ("supports", "contradicts", "inconclusive", "unrelated")
        firm = label.stance in ("supports", "contradicts")
        assert firm == (label.reason in ("on_point", "background")), label
