"""Tests unitarios para la fábrica de modelos de chat de los agentes."""

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_ollama import ChatOllama

from app.utils import llm as llm_module

ROLES = ("extractor", "translator", "judge", "health_expert")


class _FakeSettings:
    """Ajustes mínimos para construir cualquiera de los proveedores."""

    def __init__(self, provider: str, api_key: str | None = None) -> None:
        self.llm_provider = provider
        self.mistral_api_key = api_key
        self.groq_api_key = api_key
        self.google_api_key = api_key
        self.nvidia_api_key = api_key

    ollama_base_url = "http://localhost:11434"
    ollama_request_timeout_seconds = 240
    ollama_extractor_model = "llama3"
    ollama_translator_model = "translategemma"
    ollama_health_expert_model = "llama3.2"
    ollama_judge_model = "llama3.2"
    ollama_extractor_num_ctx = 8192
    ollama_extractor_num_predict = 1024
    ollama_translator_num_ctx = 4096
    ollama_translator_num_predict = 2048
    ollama_health_expert_num_ctx = 8192
    ollama_health_expert_num_predict = 2048
    ollama_judge_num_ctx = 8192
    ollama_judge_num_predict = 512
    mistral_extractor_model = "mistral-small-latest"
    mistral_translator_model = "mistral-small-latest"
    mistral_health_expert_model = "mistral-small-latest"
    mistral_judge_model = "mistral-small-latest"
    mistral_max_tokens = 2048
    mistral_request_timeout_seconds = 60
    groq_extractor_model = "llama-3.3-70b-versatile"
    groq_translator_model = "llama-3.1-8b-instant"
    groq_health_expert_model = "llama-3.3-70b-versatile"
    groq_judge_model = "llama-3.3-70b-versatile"
    groq_max_tokens = 2048
    groq_request_timeout_seconds = 60
    groq_max_retries = 5
    google_extractor_model = "gemini-3.5-flash"
    google_translator_model = "gemini-3.5-flash-lite"
    google_health_expert_model = "gemini-3.5-flash"
    google_judge_model = "gemini-3.5-flash"
    google_max_tokens = 2048
    google_request_timeout_seconds = 60
    google_max_retries = 5
    nvidia_extractor_model = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_translator_model = "minimaxai/minimax-m3"
    nvidia_health_expert_model = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_judge_model = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_max_tokens = 2048
    nvidia_request_timeout_seconds = 60

    def llm_provider_name(self) -> str:
        return self.llm_provider.strip().lower()


def _patch_settings(monkeypatch, settings) -> None:
    monkeypatch.setattr(llm_module, "get_settings", lambda: settings)


@pytest.mark.parametrize("role", ROLES)
def test_build_chat_model_returns_ollama_for_every_role(monkeypatch, role) -> None:
    _patch_settings(monkeypatch, _FakeSettings("ollama"))

    model = llm_module.build_chat_model(role)

    assert isinstance(model, ChatOllama)
    assert model.base_url == "http://localhost:11434"


@pytest.mark.parametrize("role", ROLES)
def test_build_chat_model_returns_mistral_for_every_role(monkeypatch, role) -> None:
    _patch_settings(monkeypatch, _FakeSettings("mistral", "clave-de-prueba"))

    model = llm_module.build_chat_model(role)

    assert isinstance(model, ChatMistralAI)
    assert model.model == "mistral-small-latest"
    assert model.max_tokens == 2048


@pytest.mark.parametrize("role", ROLES)
def test_build_chat_model_returns_groq_for_every_role(monkeypatch, role) -> None:
    _patch_settings(monkeypatch, _FakeSettings("groq", "clave-de-prueba"))

    model = llm_module.build_chat_model(role)

    assert isinstance(model, ChatGroq)
    assert model.max_tokens == 2048


def test_build_chat_model_maps_each_role_to_its_own_groq_model(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("groq", "clave-de-prueba"))

    assert (
        llm_module.build_chat_model("extractor").model_name == "llama-3.3-70b-versatile"
    )
    assert (
        llm_module.build_chat_model("translator").model_name == "llama-3.1-8b-instant"
    )


def test_build_chat_model_rejects_groq_without_api_key(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("groq", "   "))

    with pytest.raises(llm_module.LLMConfigurationError, match="GROQ_API_KEY"):
        llm_module.build_chat_model("extractor")


def test_build_chat_model_maps_each_role_to_its_own_ollama_model(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("ollama"))

    # El prefijo por rol debe resolver el modelo propio de cada agente.
    assert llm_module.build_chat_model("extractor").model == "llama3"
    assert llm_module.build_chat_model("translator").model == "translategemma"


def test_build_chat_model_normalizes_provider_casing(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("  MISTRAL  ", "clave-de-prueba"))

    assert isinstance(llm_module.build_chat_model("judge"), ChatMistralAI)


def test_build_chat_model_rejects_mistral_without_api_key(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("mistral", "   "))

    with pytest.raises(llm_module.LLMConfigurationError, match="MISTRAL_API_KEY"):
        llm_module.build_chat_model("extractor")


def test_build_chat_model_rejects_unknown_provider(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("anthropic"))

    with pytest.raises(llm_module.LLMConfigurationError, match="LLM_PROVIDER"):
        llm_module.build_chat_model("extractor")


def test_build_chat_model_rejects_unknown_role(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("ollama"))

    with pytest.raises(llm_module.LLMConfigurationError, match="Rol de LLM"):
        llm_module.build_chat_model("investigador")


def test_ensure_llm_available_delegates_to_ollama(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("ollama"))
    calls: list[str] = []
    monkeypatch.setattr(
        llm_module, "ensure_ollama_available", lambda: calls.append("ollama")
    )

    llm_module.ensure_llm_available()

    assert calls == ["ollama"]


def test_ensure_llm_available_skips_ollama_for_mistral(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("mistral", "clave-de-prueba"))
    monkeypatch.setattr(
        llm_module,
        "ensure_ollama_available",
        lambda: pytest.fail("no debe consultarse Ollama con LLM_PROVIDER=mistral"),
    )

    llm_module.ensure_llm_available()


def test_ensure_llm_available_fails_fast_without_api_key(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("mistral", None))

    with pytest.raises(llm_module.LLMConfigurationError, match="MISTRAL_API_KEY"):
        llm_module.ensure_llm_available()


def test_ensure_llm_available_skips_ollama_for_groq(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("groq", "clave-de-prueba"))
    monkeypatch.setattr(
        llm_module,
        "ensure_ollama_available",
        lambda: pytest.fail("no debe consultarse Ollama con LLM_PROVIDER=groq"),
    )

    llm_module.ensure_llm_available()


def test_ensure_llm_available_fails_fast_without_groq_api_key(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("groq", None))

    with pytest.raises(llm_module.LLMConfigurationError, match="GROQ_API_KEY"):
        llm_module.ensure_llm_available()


@pytest.mark.parametrize("role", ROLES)
def test_build_chat_model_returns_google_for_every_role(monkeypatch, role) -> None:
    _patch_settings(monkeypatch, _FakeSettings("google", "clave-de-prueba"))

    model = llm_module.build_chat_model(role)

    assert isinstance(model, ChatGoogleGenerativeAI)
    assert model.max_output_tokens == 2048


def test_build_chat_model_maps_each_role_to_its_own_google_model(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("google", "clave-de-prueba"))

    assert llm_module.build_chat_model("extractor").model == "gemini-3.5-flash"
    assert llm_module.build_chat_model("translator").model == "gemini-3.5-flash-lite"


def test_build_chat_model_rejects_google_without_api_key(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("google", "   "))

    with pytest.raises(llm_module.LLMConfigurationError, match="GOOGLE_API_KEY"):
        llm_module.build_chat_model("extractor")


def test_ensure_llm_available_skips_ollama_for_google(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("google", "clave-de-prueba"))
    monkeypatch.setattr(
        llm_module,
        "ensure_ollama_available",
        lambda: pytest.fail("no debe consultarse Ollama con LLM_PROVIDER=google"),
    )

    llm_module.ensure_llm_available()


def test_ensure_llm_available_fails_fast_without_google_api_key(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("google", None))

    with pytest.raises(llm_module.LLMConfigurationError, match="GOOGLE_API_KEY"):
        llm_module.ensure_llm_available()


@pytest.mark.parametrize("role", ROLES)
def test_build_chat_model_returns_nvidia_for_every_role(monkeypatch, role) -> None:
    _patch_settings(monkeypatch, _FakeSettings("nvidia", "clave-de-prueba"))

    model = llm_module.build_chat_model(role)

    assert isinstance(model, ChatNVIDIA)
    assert model.model_kwargs == {"chat_template_kwargs": {"enable_thinking": False}}


def test_build_chat_model_maps_each_role_to_its_own_nvidia_model(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("nvidia", "clave-de-prueba"))

    assert (
        llm_module.build_chat_model("extractor").model
        == "nvidia/nemotron-3-super-120b-a12b"
    )
    assert llm_module.build_chat_model("translator").model == "minimaxai/minimax-m3"


def test_build_chat_model_rejects_nvidia_without_api_key(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("nvidia", "   "))

    with pytest.raises(llm_module.LLMConfigurationError, match="NVIDIA_API_KEY"):
        llm_module.build_chat_model("extractor")


def test_ensure_llm_available_fails_fast_without_nvidia_api_key(monkeypatch) -> None:
    _patch_settings(monkeypatch, _FakeSettings("nvidia", None))

    with pytest.raises(llm_module.LLMConfigurationError, match="NVIDIA_API_KEY"):
        llm_module.ensure_llm_available()
