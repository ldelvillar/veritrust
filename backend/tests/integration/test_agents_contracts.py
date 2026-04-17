"""Tests de contrato para agentes individuales con mocks de LLM y herramienta BERT."""

from types import SimpleNamespace
import pytest


@pytest.fixture(scope="module")
def extractor_module():
    from app.agents import extractor as module

    return module


@pytest.fixture(scope="module")
def translator_module():
    from app.agents import translator as module

    return module


@pytest.fixture(scope="module")
def health_module():
    from app.agents import health_expert as module

    return module


def test_extractor_returns_only_expected_field_and_preserves_state(
    monkeypatch, extractor_module
):

    class _FakeChain:
        def invoke(self, payload):
            assert "texto" in payload
            return SimpleNamespace(statements=["Afirmacion 1"])

    monkeypatch.setattr(extractor_module, "extractor_chain", _FakeChain())

    state = {
        "input_text": "Texto médico",
        "other_key": "keep-me",
    }
    update = extractor_module.extractor(state)

    assert set(update.keys()) == {"extracted_statements"}
    merged = {**state, **update}
    assert merged["input_text"] == "Texto médico"
    assert merged["other_key"] == "keep-me"


def test_extractor_handles_empty_llm_output_without_exception(
    monkeypatch, extractor_module
):

    class _FakeChain:
        def invoke(self, payload):
            return SimpleNamespace(statements=[])

    monkeypatch.setattr(extractor_module, "extractor_chain", _FakeChain())

    update = extractor_module.extractor({"input_text": "Sin afirmaciones"})

    assert update == {"extracted_statements": []}


def test_translator_returns_only_expected_field_and_preserves_state(
    monkeypatch, translator_module
):

    class _FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(content="Translated")

    monkeypatch.setattr(translator_module, "ChatOllama", _FakeLLM)

    state = {
        "extracted_statements": ["Afirmación original"],
        "input_text": "Texto base",
        "other_key": 123,
    }
    update = translator_module.translator(state)

    assert set(update.keys()) == {"translated_statements"}
    assert update["translated_statements"] == ["Translated"]
    merged = {**state, **update}
    assert merged["input_text"] == "Texto base"
    assert merged["other_key"] == 123


def test_translator_handles_empty_llm_output_without_exception(
    monkeypatch, translator_module
):

    class _FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(content="   ")

    monkeypatch.setattr(translator_module, "ChatOllama", _FakeLLM)

    update = translator_module.translator({"extracted_statements": ["A"]})

    assert update == {"translated_statements": [""]}


def test_translator_returns_empty_list_when_no_statements_and_skips_llm(
    monkeypatch, translator_module
):

    class _ShouldNotBeCalled:
        def __init__(self, *args, **kwargs):
            raise AssertionError("ChatOllama no debe instanciarse sin afirmaciones")

    monkeypatch.setattr(translator_module, "ChatOllama", _ShouldNotBeCalled)

    update = translator_module.translator({"extracted_statements": []})

    assert update == {"translated_statements": []}


def test_health_expert_returns_only_expected_fields_and_preserves_state(
    monkeypatch, health_module
):

    class _FakeTool:
        def invoke(self, payload):
            return {"label": "verdadera", "confidence": 0.9}

    class _FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(content="Informe médico")

    monkeypatch.setattr(health_module, "FakeNewsDetectorTool", _FakeTool)
    monkeypatch.setattr(health_module, "ChatOllama", _FakeLLM)

    state = {
        "input_text": "Texto base",
        "extracted_statements": ["S1"],
        "translated_statements": ["T1"],
        "other_key": "keep-me",
    }
    update = health_module.health_expert(state)

    assert set(update.keys()) == {"label", "confidence", "medical_explanation"}
    merged = {**state, **update}
    assert merged["input_text"] == "Texto base"
    assert merged["other_key"] == "keep-me"


def test_health_expert_handles_empty_llm_output_without_exception(
    monkeypatch, health_module
):

    class _FakeTool:
        def invoke(self, payload):
            return {"label": "falsa", "confidence": 0.6}

    class _FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(content="")

    monkeypatch.setattr(health_module, "FakeNewsDetectorTool", _FakeTool)
    monkeypatch.setattr(health_module, "ChatOllama", _FakeLLM)

    update = health_module.health_expert(
        {
            "extracted_statements": ["S1"],
            "translated_statements": ["T1"],
        }
    )

    assert set(update.keys()) == {"label", "confidence", "medical_explanation"}
    assert update["medical_explanation"] == ""


def test_health_expert_parses_stringified_tool_output(monkeypatch, health_module):

    class _FakeTool:
        def invoke(self, payload):
            return "{'label': 'falsa', 'confidence': 0.8}"

    class _FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(content="Informe consolidado")

    monkeypatch.setattr(health_module, "FakeNewsDetectorTool", _FakeTool)
    monkeypatch.setattr(health_module, "ChatOllama", _FakeLLM)

    update = health_module.health_expert(
        {
            "extracted_statements": ["S1"],
            "translated_statements": ["T1"],
        }
    )

    assert update["label"] == "falsa"
    assert 0.0 <= update["confidence"] <= 1.0
    assert update["medical_explanation"] == "Informe consolidado"


def test_health_expert_raises_value_error_on_invalid_detector_output(
    monkeypatch, health_module
):

    class _FakeTool:
        def invoke(self, payload):
            return "not-a-dict"

    class _FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(content="No debería usarse")

    monkeypatch.setattr(health_module, "FakeNewsDetectorTool", _FakeTool)
    monkeypatch.setattr(health_module, "ChatOllama", _FakeLLM)

    try:
        health_module.health_expert(
            {
                "extracted_statements": ["S1"],
                "translated_statements": ["T1"],
            }
        )
        raise AssertionError("Se esperaba ValueError por salida inválida")
    except ValueError as exc:
        assert "Salida inesperada del detector" in str(exc)


def test_health_expert_raises_value_error_when_detector_missing_keys(
    monkeypatch, health_module
):

    class _FakeTool:
        def invoke(self, payload):
            return {"label": "falsa"}

    class _FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(content="No debería usarse")

    monkeypatch.setattr(health_module, "FakeNewsDetectorTool", _FakeTool)
    monkeypatch.setattr(health_module, "ChatOllama", _FakeLLM)

    try:
        health_module.health_expert(
            {
                "extracted_statements": ["S1"],
                "translated_statements": ["T1"],
            }
        )
        raise AssertionError("Se esperaba ValueError por claves faltantes")
    except ValueError as exc:
        assert "Salida inesperada del detector" in str(exc)
