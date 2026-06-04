"""Tests de integración para el grafo completo de agentes definido en app.agents.main."""

import importlib
import sys
import types
from pathlib import Path

import pytest

from app.prompts.agents import PromptItem, Prompts


@pytest.fixture(scope="module")
def dummy_prompts():
    return Prompts(
        extractor=PromptItem(version="v1", text="extractor"),
        translator=PromptItem(version="v1", text="translator"),
        health_expert=PromptItem(version="v1", text="health_expert"),
    )


def _load_main_module(
    monkeypatch, extractor_impl, translator_impl, health_impl, investigator_impl=None
):
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    if investigator_impl is None:

        def investigator_impl(state):
            return {"sources": [], "evidence_coverage": 1.0}

    fake_extractor_module = types.ModuleType("app.agents.extractor")
    fake_extractor_module.extractor = extractor_impl

    fake_translator_module = types.ModuleType("app.agents.translator")
    fake_translator_module.translator = translator_impl

    fake_investigator_module = types.ModuleType("app.agents.investigator")
    fake_investigator_module.investigator = investigator_impl

    fake_health_module = types.ModuleType("app.agents.health_expert")
    fake_health_module.health_expert = health_impl

    fake_start_module = types.ModuleType("app.utils.ollama")
    fake_start_module.ensure_ollama_available = lambda: None

    monkeypatch.setitem(sys.modules, "app.agents.extractor", fake_extractor_module)
    monkeypatch.setitem(sys.modules, "app.agents.translator", fake_translator_module)
    monkeypatch.setitem(
        sys.modules, "app.agents.investigator", fake_investigator_module
    )
    monkeypatch.setitem(sys.modules, "app.agents.health_expert", fake_health_module)
    monkeypatch.setitem(sys.modules, "app.utils.ollama", fake_start_module)

    sys.modules.pop("app.agents.main", None)
    return importlib.import_module("app.agents.main")


def _minimal_state():
    return {
        "input_text": "Texto de prueba",
        "extracted_statements": [],
        "translated_statements": [],
        "label": "",
        "confidence": "",
        "medical_explanation": "",
    }


def test_create_graph_returns_compiled_invocable(monkeypatch, dummy_prompts):
    def extractor(state, prompts):
        return {"extracted_statements": ["Claim"]}

    def translator(state, prompts):
        return {"translated_statements": ["Claim"]}

    def health_expert(state, prompts):
        return {
            "label": "falsa",
            "confidence": "0.95",
            "medical_explanation": "Explicación médica de prueba.",
        }

    main_module = _load_main_module(monkeypatch, extractor, translator, health_expert)
    graph = main_module.create_graph(dummy_prompts)

    assert hasattr(graph, "invoke")
    assert callable(graph.invoke)


def test_graph_invocation_with_min_state_contains_expected_keys(
    monkeypatch, dummy_prompts
):
    def extractor(state, prompts):
        return {"extracted_statements": ["A"]}

    def translator(state, prompts):
        return {"translated_statements": ["A"]}

    def health_expert(state, prompts):
        return {
            "label": "verdadera",
            "confidence": "0.70",
            "medical_explanation": "Todo correcto.",
        }

    main_module = _load_main_module(monkeypatch, extractor, translator, health_expert)
    graph = main_module.create_graph(dummy_prompts)
    result = graph.invoke(_minimal_state())

    expected_keys = {
        "input_text",
        "extracted_statements",
        "translated_statements",
        "label",
        "confidence",
        "medical_explanation",
    }
    assert expected_keys.issubset(result.keys())


def test_graph_keeps_contract_when_nodes_return_empty_values(
    monkeypatch, dummy_prompts
):
    def extractor(state, prompts):
        return {"extracted_statements": []}

    def translator(state, prompts):
        return {"translated_statements": []}

    def health_expert(state, prompts):
        return {
            "label": "",
            "confidence": "",
            "medical_explanation": "",
        }

    main_module = _load_main_module(monkeypatch, extractor, translator, health_expert)
    graph = main_module.create_graph(dummy_prompts)
    result = graph.invoke(_minimal_state())

    assert result["input_text"] == "Texto de prueba"
    assert result["extracted_statements"] == []
    assert result["translated_statements"] == []
    assert result["label"] == ""
    assert result["confidence"] == ""
    assert result["medical_explanation"] == ""


def test_graph_runs_investigator_and_propagates_sources(monkeypatch, dummy_prompts):
    fuentes = [{"title": "Estudio", "url": "https://doi.org/10.1/x"}]

    def extractor(state, prompts):
        return {"extracted_statements": ["A"]}

    def translator(state, prompts):
        return {"translated_statements": ["A-en"]}

    def investigator(state):
        # El investigador corre tras el traductor y ve sus afirmaciones.
        assert state["translated_statements"] == ["A-en"]
        return {"sources": fuentes, "evidence_coverage": 1.0}

    def health_expert(state, prompts):
        # Las fuentes y la cobertura llegan al experto en el estado.
        assert state["sources"] == fuentes
        assert state["evidence_coverage"] == 1.0
        return {
            "label": "falsa",
            "confidence": 0.9,
            "medical_explanation": "Informe.",
        }

    main_module = _load_main_module(
        monkeypatch, extractor, translator, health_expert, investigator
    )
    graph = main_module.create_graph(dummy_prompts)
    result = graph.invoke(_minimal_state())

    assert result["sources"] == fuentes
    assert result["evidence_coverage"] == 1.0
