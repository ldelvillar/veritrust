"""Factory of the agents' chat models for the configured provider."""

import logging
import random
import time
from typing import Any

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_ollama import ChatOllama
from pydantic import SecretStr

from app.core.config import get_settings
from app.utils.ollama import ensure_ollama_available

logger = logging.getLogger(__name__)


class LLMConfigurationError(RuntimeError):
    """The configured LLM provider is not usable."""


# Prefix of each role's Ollama settings (model, num_ctx and num_predict).
OLLAMA_PREFIX_BY_ROLE = {
    "extractor": "ollama_extractor",
    "translator": "ollama_translator",
    "health_expert": "ollama_health_expert",
    "judge": "ollama_judge",
}

MISTRAL_MODEL_ATTR_BY_ROLE = {
    "extractor": "mistral_extractor_model",
    "translator": "mistral_translator_model",
    "health_expert": "mistral_health_expert_model",
    "judge": "mistral_judge_model",
}

GROQ_MODEL_ATTR_BY_ROLE = {
    "extractor": "groq_extractor_model",
    "translator": "groq_translator_model",
    "health_expert": "groq_health_expert_model",
    "judge": "groq_judge_model",
}


GOOGLE_MODEL_ATTR_BY_ROLE = {
    "extractor": "google_extractor_model",
    "translator": "google_translator_model",
    "health_expert": "google_health_expert_model",
    "judge": "google_judge_model",
}


MISTRAL_RETRY_MAX_WAIT_SECONDS = 16


def _is_transient(exc: httpx.HTTPStatusError) -> bool:
    """Tell whether an HTTP error is transient, a rate limit or a server failure."""
    status = exc.response.status_code
    return status == 429 or status >= 500


class _RetryingChatMistralAI(ChatMistralAI):
    """ChatMistralAI that also retries 429 and 5xx, since the library only retries network failures."""

    def completion_with_retry(
        self, run_manager: CallbackManagerForLLMRun | None = None, **kwargs: Any
    ) -> Any:
        """Call the API with exponential backoff and jitter on transient HTTP errors."""
        attempt = 0
        while True:
            try:
                return super().completion_with_retry(run_manager=run_manager, **kwargs)
            except httpx.HTTPStatusError as exc:
                if not _is_transient(exc) or attempt == self.max_retries:
                    raise
                # Jitter keeps the judge's parallel calls from retrying at the same time.
                wait = min(MISTRAL_RETRY_MAX_WAIT_SECONDS, 2**attempt) + random.random()
                attempt += 1
                logger.warning(
                    "Mistral respondió %s; reintento %d/%d en %.1f s",
                    exc.response.status_code,
                    attempt,
                    self.max_retries,
                    wait,
                )
                time.sleep(wait)


# Nemotron reasons by default, with far more latency and tokens for the same output.
NVIDIA_THINKING_OFF = {"chat_template_kwargs": {"enable_thinking": False}}

NVIDIA_MODEL_ATTR_BY_ROLE = {
    "extractor": "nvidia_extractor_model",
    "translator": "nvidia_translator_model",
    "health_expert": "nvidia_health_expert_model",
    "judge": "nvidia_judge_model",
}

MODEL_ATTR_BY_PROVIDER = {
    "ollama": {
        role: f"{prefix}_model" for role, prefix in OLLAMA_PREFIX_BY_ROLE.items()
    },
    "mistral": MISTRAL_MODEL_ATTR_BY_ROLE,
    "groq": GROQ_MODEL_ATTR_BY_ROLE,
    "google": GOOGLE_MODEL_ATTR_BY_ROLE,
    "nvidia": NVIDIA_MODEL_ATTR_BY_ROLE,
}


def _mistral_api_key() -> str:
    """Return the Mistral api_key or fail with an actionable message."""
    api_key = (get_settings().mistral_api_key or "").strip()
    if not api_key:
        raise LLMConfigurationError(
            "MISTRAL_API_KEY no está configurada y LLM_PROVIDER=mistral la exige."
        )
    return api_key


def _groq_api_key() -> str:
    """Return the Groq api_key or fail with an actionable message."""
    api_key = (get_settings().groq_api_key or "").strip()
    if not api_key:
        raise LLMConfigurationError(
            "GROQ_API_KEY no está configurada y LLM_PROVIDER=groq la exige."
        )
    return api_key


def _google_api_key() -> str:
    """Return the Google api_key or fail with an actionable message."""
    api_key = (get_settings().google_api_key or "").strip()
    if not api_key:
        raise LLMConfigurationError(
            "GOOGLE_API_KEY no está configurada y LLM_PROVIDER=google la exige."
        )
    return api_key


def _nvidia_api_key() -> str:
    """Return the NVIDIA api_key or fail with an actionable message."""
    api_key = (get_settings().nvidia_api_key or "").strip()
    if not api_key:
        raise LLMConfigurationError(
            "NVIDIA_API_KEY no está configurada y LLM_PROVIDER=nvidia la exige."
        )
    return api_key


def build_chat_model(role: str, model: str | None = None) -> BaseChatModel:
    """Build the chat model of the given role for the configured provider."""
    if role not in OLLAMA_PREFIX_BY_ROLE:
        raise LLMConfigurationError(f"Rol de LLM desconocido: {role}")

    settings = get_settings()
    provider = settings.llm_provider_name()

    def _model_for(attr_by_role: dict[str, str]) -> str:
        # The override allows rotating models without touching the role's configuration.
        return model or str(getattr(settings, attr_by_role[role]))

    if provider == "mistral":
        return _RetryingChatMistralAI(
            model_name=_model_for(MISTRAL_MODEL_ATTR_BY_ROLE),
            temperature=0,
            api_key=SecretStr(_mistral_api_key()),
            max_tokens=settings.mistral_max_tokens,
            timeout=settings.mistral_request_timeout_seconds,
            max_retries=settings.mistral_max_retries,
        )

    if provider == "groq":
        return ChatGroq(
            model=_model_for(GROQ_MODEL_ATTR_BY_ROLE),
            temperature=0,
            api_key=SecretStr(_groq_api_key()),
            max_tokens=settings.groq_max_tokens,
            timeout=settings.groq_request_timeout_seconds,
            max_retries=settings.groq_max_retries,
        )

    if provider == "google":
        return ChatGoogleGenerativeAI(
            model=_model_for(GOOGLE_MODEL_ATTR_BY_ROLE),
            temperature=0,
            api_key=SecretStr(_google_api_key()),
            max_tokens=settings.google_max_tokens,
            request_timeout=settings.google_request_timeout_seconds,
            retries=settings.google_max_retries,
        )

    if provider == "nvidia":
        return ChatNVIDIA(
            model=_model_for(NVIDIA_MODEL_ATTR_BY_ROLE),
            temperature=0,
            api_key=_nvidia_api_key(),
            max_completion_tokens=settings.nvidia_max_tokens,
            timeout=settings.nvidia_request_timeout_seconds,
            model_kwargs=NVIDIA_THINKING_OFF,
        )

    if provider != "ollama":
        raise LLMConfigurationError(
            f"LLM_PROVIDER no reconocido: '{settings.llm_provider}'. "
            "Usa 'ollama', 'mistral', 'groq', 'google' o 'nvidia'."
        )

    prefix = OLLAMA_PREFIX_BY_ROLE[role]
    return ChatOllama(
        model=model or str(getattr(settings, f"{prefix}_model")),
        temperature=0,
        base_url=settings.ollama_base_url,
        num_ctx=getattr(settings, f"{prefix}_num_ctx"),
        num_predict=getattr(settings, f"{prefix}_num_predict"),
        client_kwargs={"timeout": settings.ollama_request_timeout_seconds},
    )


def configured_models() -> dict[str, str]:
    """Return the configured model for each role of the active provider."""
    settings = get_settings()
    attrs = MODEL_ATTR_BY_PROVIDER.get(settings.llm_provider_name())
    if attrs is None:
        raise LLMConfigurationError(
            f"LLM_PROVIDER no reconocido: '{settings.llm_provider}'."
        )
    models = {role: str(getattr(settings, attr)) for role, attr in attrs.items()}
    # With rotation, Groq's judge alternates between several models, so they are all recorded.
    if settings.llm_provider_name() == "groq" and settings.groq_judge_models():
        models["judge"] = ",".join(settings.groq_judge_models())
    return models


def ensure_llm_available() -> None:
    """Verify that the configured LLM provider can serve requests."""
    settings = get_settings()
    provider = settings.llm_provider_name()

    if provider == "mistral":
        _mistral_api_key()
        logger.info("Proveedor de LLM: Mistral (%s)", settings.mistral_extractor_model)
        return

    if provider == "groq":
        _groq_api_key()
        logger.info("Proveedor de LLM: Groq (%s)", settings.groq_extractor_model)
        return

    if provider == "google":
        _google_api_key()
        logger.info("Proveedor de LLM: Google (%s)", settings.google_extractor_model)
        return

    if provider == "nvidia":
        _nvidia_api_key()
        logger.info("Proveedor de LLM: NVIDIA (%s)", settings.nvidia_extractor_model)
        return

    ensure_ollama_available()
