"""Tests del juez de evidencia con el LLM mockeado."""

from types import SimpleNamespace

from app.agents import relevance
from app.agents.relevance import _format_candidates, get_relevance_chain, judge_evidence


class _FakeChain:
    def __init__(self, stances):
        self._stances = stances

    def invoke(self, payload):
        return SimpleNamespace(stances=self._stances)


def test_judge_evidence_drops_unrelated_and_annotates_stance(monkeypatch):
    monkeypatch.setattr(
        relevance,
        "get_relevance_chain",
        lambda prompt: _FakeChain(["supports", "unrelated"]),
    )
    hits = [{"title": "a", "abstract": "x"}, {"title": "b", "abstract": "y"}]

    kept = judge_evidence("p", "claim", hits)

    assert kept == [{"title": "a", "abstract": "x", "stance": "supports"}]


def test_judge_evidence_returns_empty_without_calling_judge(monkeypatch):
    def _fail(prompt):
        raise AssertionError("no debe construirse la cadena sin candidatas")

    monkeypatch.setattr(relevance, "get_relevance_chain", _fail)

    assert judge_evidence("p", "claim", []) == []


def test_judge_evidence_pads_missing_stances_as_inconclusive(monkeypatch):
    # Una sola postura para dos fuentes: la no juzgada se conserva sin concluir.
    monkeypatch.setattr(
        relevance, "get_relevance_chain", lambda prompt: _FakeChain(["supports"])
    )
    hits = [{"title": "a"}, {"title": "b"}]

    kept = judge_evidence("p", "claim", hits)

    assert kept == [
        {"title": "a", "stance": "supports"},
        {"title": "b", "stance": "inconclusive"},
    ]


def test_judge_evidence_fails_open_on_error(monkeypatch):
    class _BoomChain:
        def invoke(self, payload):
            raise RuntimeError("ollama caído")

    monkeypatch.setattr(relevance, "get_relevance_chain", lambda prompt: _BoomChain())
    hits = [{"title": "a"}]

    # Ante un fallo del juez se conservan todas las fuentes, sin postura.
    assert judge_evidence("p", "claim", hits) == hits


def test_format_candidates_includes_abstract_and_title_only():
    formatted = _format_candidates(
        [{"title": "Con resumen", "abstract": "detalle"}, {"title": "Solo título"}]
    )

    assert "1. Con resumen. detalle" in formatted
    assert "2. Solo título" in formatted


def test_get_relevance_chain_builds_invocable():
    chain = get_relevance_chain("prompt de prueba")

    assert hasattr(chain, "invoke")
