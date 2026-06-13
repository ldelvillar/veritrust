"""Tests del juez de relevancia con el LLM mockeado."""

from types import SimpleNamespace

from app.agents import relevance
from app.agents.relevance import _format_candidates, get_relevance_chain, keep_relevant


class _FakeChain:
    def __init__(self, flags):
        self._flags = flags

    def invoke(self, payload):
        return SimpleNamespace(relevant=self._flags)


def test_keep_relevant_drops_irrelevant_sources(monkeypatch):
    monkeypatch.setattr(
        relevance, "get_relevance_chain", lambda prompt: _FakeChain([True, False])
    )
    hits = [{"title": "a", "abstract": "x"}, {"title": "b", "abstract": "y"}]

    assert keep_relevant("p", "claim", hits) == [hits[0]]


def test_keep_relevant_returns_empty_without_calling_judge(monkeypatch):
    def _fail(prompt):
        raise AssertionError("no debe construirse la cadena sin candidatas")

    monkeypatch.setattr(relevance, "get_relevance_chain", _fail)

    assert keep_relevant("p", "claim", []) == []


def test_keep_relevant_keeps_unjudged_when_flags_missing(monkeypatch):
    # Un solo flag para dos fuentes: la no juzgada se conserva.
    monkeypatch.setattr(
        relevance, "get_relevance_chain", lambda prompt: _FakeChain([True])
    )
    hits = [{"title": "a"}, {"title": "b"}]

    assert keep_relevant("p", "claim", hits) == hits


def test_keep_relevant_fails_open_on_judge_error(monkeypatch):
    class _BoomChain:
        def invoke(self, payload):
            raise RuntimeError("ollama caído")

    monkeypatch.setattr(relevance, "get_relevance_chain", lambda prompt: _BoomChain())
    hits = [{"title": "a"}]

    # Ante un fallo del juez se conservan todas las fuentes.
    assert keep_relevant("p", "claim", hits) == hits


def test_format_candidates_includes_abstract_and_title_only():
    formatted = _format_candidates(
        [{"title": "Con resumen", "abstract": "detalle"}, {"title": "Solo título"}]
    )

    assert "1. Con resumen. detalle" in formatted
    assert "2. Solo título" in formatted


def test_get_relevance_chain_builds_invocable():
    chain = get_relevance_chain("prompt de prueba")

    assert hasattr(chain, "invoke")
