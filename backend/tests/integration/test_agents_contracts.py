"""Tests de contrato para agentes individuales con mocks de LLM y herramienta BERT."""

from types import SimpleNamespace

import pytest

from app.prompts.agents import PromptItem, Prompts


@pytest.fixture(scope="module")
def dummy_prompts():
    return Prompts(
        extractor=PromptItem(version="v1", text="extractor"),
        translator=PromptItem(version="v1", text="translator"),
        health_expert=PromptItem(version="v1", text="health_expert"),
    )


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
    monkeypatch, extractor_module, dummy_prompts
):

    class _FakeChain:
        def invoke(self, payload):
            assert "texto" in payload
            return SimpleNamespace(statements=["Afirmacion 1"])

    monkeypatch.setattr(
        extractor_module, "get_extractor_chain", lambda prompt_text: _FakeChain()
    )

    state = {
        "input_text": "Texto médico",
        "other_key": "keep-me",
    }
    update = extractor_module.extractor(state, dummy_prompts)

    assert set(update.keys()) == {"extracted_statements"}
    merged = {**state, **update}
    assert merged["input_text"] == "Texto médico"
    assert merged["other_key"] == "keep-me"


def test_extractor_handles_empty_llm_output_without_exception(
    monkeypatch, extractor_module, dummy_prompts
):

    class _FakeChain:
        def invoke(self, payload):
            return SimpleNamespace(statements=[])

    monkeypatch.setattr(
        extractor_module, "get_extractor_chain", lambda prompt_text: _FakeChain()
    )

    update = extractor_module.extractor(
        {"input_text": "Sin afirmaciones"}, dummy_prompts
    )

    assert update == {"extracted_statements": []}


def test_translator_returns_only_expected_field_and_preserves_state(
    monkeypatch, translator_module, dummy_prompts
):

    class _FakeChain:
        def invoke(self, payload):
            assert "statements" in payload
            return SimpleNamespace(translations=["Translated"])

    monkeypatch.setattr(
        translator_module, "get_translator_chain", lambda prompt_text: _FakeChain()
    )

    state = {
        "extracted_statements": ["Afirmación original"],
        "input_text": "Texto base",
        "other_key": 123,
    }
    update = translator_module.translator(state, dummy_prompts)

    assert set(update.keys()) == {"translated_statements"}
    assert update["translated_statements"] == ["Translated"]
    merged = {**state, **update}
    assert merged["input_text"] == "Texto base"
    assert merged["other_key"] == 123


def test_translator_pads_when_llm_returns_fewer_translations(
    monkeypatch, translator_module, dummy_prompts
):

    class _FakeChain:
        def invoke(self, payload):
            return SimpleNamespace(translations=["only-first"])

    monkeypatch.setattr(
        translator_module, "get_translator_chain", lambda prompt_text: _FakeChain()
    )

    update = translator_module.translator(
        {"extracted_statements": ["A", "B"]}, dummy_prompts
    )

    assert update == {"translated_statements": ["only-first", ""]}


def test_translator_truncates_when_llm_returns_extra_translations(
    monkeypatch, translator_module, dummy_prompts
):

    class _FakeChain:
        def invoke(self, payload):
            return SimpleNamespace(translations=["t1", "t2", "extra"])

    monkeypatch.setattr(
        translator_module, "get_translator_chain", lambda prompt_text: _FakeChain()
    )

    update = translator_module.translator(
        {"extracted_statements": ["A", "B"]}, dummy_prompts
    )

    assert update == {"translated_statements": ["t1", "t2"]}


def test_translator_returns_empty_list_when_no_statements_and_skips_llm(
    monkeypatch, translator_module, dummy_prompts
):

    def _should_not_be_called(prompt_text):
        raise AssertionError("get_translator_chain no debe llamarse sin afirmaciones")

    monkeypatch.setattr(
        translator_module, "get_translator_chain", _should_not_be_called
    )

    update = translator_module.translator({"extracted_statements": []}, dummy_prompts)

    assert update == {"translated_statements": []}


def test_health_expert_returns_only_expected_fields_and_preserves_state(
    monkeypatch, health_module, dummy_prompts
):

    class _FakeTool:
        def predict_batch(self, texts):
            return [{"label": "verdadera", "confidence": 0.9} for _ in texts]

    class _FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(content="Informe médico")

    monkeypatch.setattr(health_module, "FakeNewsDetectorTool", _FakeTool)
    monkeypatch.setattr(health_module, "get_health_expert_llm", lambda: _FakeLLM())

    state = {
        "input_text": "Texto base",
        "extracted_statements": ["S1"],
        "translated_statements": ["T1"],
        "other_key": "keep-me",
    }
    update = health_module.health_expert(state, dummy_prompts)

    assert set(update.keys()) == {"label", "confidence", "medical_explanation"}
    merged = {**state, **update}
    assert merged["input_text"] == "Texto base"
    assert merged["other_key"] == "keep-me"


def test_health_expert_handles_empty_llm_output_without_exception(
    monkeypatch, health_module, dummy_prompts
):

    class _FakeTool:
        def predict_batch(self, texts):
            return [{"label": "falsa", "confidence": 0.6} for _ in texts]

    class _FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(content="")

    monkeypatch.setattr(health_module, "FakeNewsDetectorTool", _FakeTool)
    monkeypatch.setattr(health_module, "get_health_expert_llm", lambda: _FakeLLM())

    update = health_module.health_expert(
        {
            "extracted_statements": ["S1"],
            "translated_statements": ["T1"],
        },
        dummy_prompts,
    )

    assert set(update.keys()) == {"label", "confidence", "medical_explanation"}
    assert update["medical_explanation"] == ""


def test_health_expert_returns_empty_explanation_when_no_statements(
    monkeypatch, health_module, dummy_prompts
):
    def _fail_if_called(*args, **kwargs):
        raise AssertionError(
            "No deben invocarse LLM ni detector sin afirmaciones que evaluar"
        )

    monkeypatch.setattr(health_module, "FakeNewsDetectorTool", _fail_if_called)
    monkeypatch.setattr(health_module, "get_health_expert_llm", _fail_if_called)

    update = health_module.health_expert(
        {"extracted_statements": [], "translated_statements": []},
        dummy_prompts,
    )

    # Explicación vacía es el centinela que la ruta traduce a NO_MEDICAL_CLAIMS.
    assert set(update.keys()) == {"label", "confidence", "medical_explanation"}
    assert update["medical_explanation"] == ""
    assert update["label"] == ""
    assert update["confidence"] == 0.0


def test_health_expert_raises_value_error_on_invalid_detector_output(
    monkeypatch, health_module, dummy_prompts
):

    class _FakeTool:
        def predict_batch(self, texts):
            return ["not-a-dict" for _ in texts]

    class _FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(content="No debería usarse")

    monkeypatch.setattr(health_module, "FakeNewsDetectorTool", _FakeTool)
    monkeypatch.setattr(health_module, "get_health_expert_llm", lambda: _FakeLLM())

    try:
        health_module.health_expert(
            {
                "extracted_statements": ["S1"],
                "translated_statements": ["T1"],
            },
            dummy_prompts,
        )
        raise AssertionError("Se esperaba ValueError por salida inválida")
    except ValueError as exc:
        assert "Salida inesperada del detector" in str(exc)


def test_health_expert_raises_value_error_when_detector_missing_keys(
    monkeypatch, health_module, dummy_prompts
):

    class _FakeTool:
        def predict_batch(self, texts):
            return [{"label": "falsa"} for _ in texts]

    class _FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(content="No debería usarse")

    monkeypatch.setattr(health_module, "FakeNewsDetectorTool", _FakeTool)
    monkeypatch.setattr(health_module, "get_health_expert_llm", lambda: _FakeLLM())

    try:
        health_module.health_expert(
            {
                "extracted_statements": ["S1"],
                "translated_statements": ["T1"],
            },
            dummy_prompts,
        )
        raise AssertionError("Se esperaba ValueError por claves faltantes")
    except ValueError as exc:
        assert "Salida inesperada del detector" in str(exc)
