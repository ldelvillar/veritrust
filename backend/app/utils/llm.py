"""Fábrica de los modelos de chat de los agentes según el proveedor configurado."""

import logging

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
    """El proveedor de LLM configurado no es utilizable."""


# Prefijo de los ajustes de Ollama de cada rol (modelo, num_ctx y num_predict).
OLLAMA_PREFIX_BY_ROLE = {
    "extractor": "ollama_extractor",
    "translator": "ollama_translator",
    "health_expert": "ollama_health_expert",
    "judge": "ollama_judge",
}

# Ajuste de Settings con el modelo de Mistral de cada rol.
MISTRAL_MODEL_ATTR_BY_ROLE = {
    "extractor": "mistral_extractor_model",
    "translator": "mistral_translator_model",
    "health_expert": "mistral_health_expert_model",
    "judge": "mistral_judge_model",
}

# Ajuste de Settings con el modelo de Groq de cada rol.
GROQ_MODEL_ATTR_BY_ROLE = {
    "extractor": "groq_extractor_model",
    "translator": "groq_translator_model",
    "health_expert": "groq_health_expert_model",
    "judge": "groq_judge_model",
}


# Ajuste de Settings con el modelo de Google de cada rol.
GOOGLE_MODEL_ATTR_BY_ROLE = {
    "extractor": "google_extractor_model",
    "translator": "google_translator_model",
    "health_expert": "google_health_expert_model",
    "judge": "google_judge_model",
}


# Nemotron razona por defecto: mucha más latencia y tokens para la misma salida.
NVIDIA_THINKING_OFF = {"chat_template_kwargs": {"enable_thinking": False}}

# Ajuste de Settings con el modelo de NVIDIA de cada rol.
NVIDIA_MODEL_ATTR_BY_ROLE = {
    "extractor": "nvidia_extractor_model",
    "translator": "nvidia_translator_model",
    "health_expert": "nvidia_health_expert_model",
    "judge": "nvidia_judge_model",
}


def _mistral_api_key() -> str:
    """Devuelve la api_key de Mistral o falla con un mensaje accionable."""
    api_key = (get_settings().mistral_api_key or "").strip()
    if not api_key:
        raise LLMConfigurationError(
            "MISTRAL_API_KEY no está configurada y LLM_PROVIDER=mistral la exige."
        )
    return api_key


def _groq_api_key() -> str:
    """Devuelve la api_key de Groq o falla con un mensaje accionable."""
    api_key = (get_settings().groq_api_key or "").strip()
    if not api_key:
        raise LLMConfigurationError(
            "GROQ_API_KEY no está configurada y LLM_PROVIDER=groq la exige."
        )
    return api_key


def _google_api_key() -> str:
    """Devuelve la api_key de Google o falla con un mensaje accionable."""
    api_key = (get_settings().google_api_key or "").strip()
    if not api_key:
        raise LLMConfigurationError(
            "GOOGLE_API_KEY no está configurada y LLM_PROVIDER=google la exige."
        )
    return api_key


def _nvidia_api_key() -> str:
    """Devuelve la api_key de NVIDIA o falla con un mensaje accionable."""
    api_key = (get_settings().nvidia_api_key or "").strip()
    if not api_key:
        raise LLMConfigurationError(
            "NVIDIA_API_KEY no está configurada y LLM_PROVIDER=nvidia la exige."
        )
    return api_key


def build_chat_model(role: str, model: str | None = None) -> BaseChatModel:
    """Construye el modelo de chat del rol indicado para el proveedor configurado."""
    if role not in OLLAMA_PREFIX_BY_ROLE:
        raise LLMConfigurationError(f"Rol de LLM desconocido: {role}")

    settings = get_settings()
    provider = settings.llm_provider_name()

    def _model_for(attr_by_role: dict[str, str]) -> str:
        # El override permite rotar de modelo sin tocar la configuración del rol.
        return model or str(getattr(settings, attr_by_role[role]))

    if provider == "mistral":
        return ChatMistralAI(
            model_name=_model_for(MISTRAL_MODEL_ATTR_BY_ROLE),
            temperature=0,
            api_key=SecretStr(_mistral_api_key()),
            max_tokens=settings.mistral_max_tokens,
            timeout=settings.mistral_request_timeout_seconds,
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


def ensure_llm_available() -> None:
    """Verifica que el proveedor de LLM configurado puede atender peticiones."""
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
