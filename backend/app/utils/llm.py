"""Fábrica de los modelos de chat de los agentes según el proveedor configurado."""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_mistralai import ChatMistralAI
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


def _mistral_api_key() -> str:
    """Devuelve la api_key de Mistral o falla con un mensaje accionable."""
    api_key = (get_settings().mistral_api_key or "").strip()
    if not api_key:
        raise LLMConfigurationError(
            "MISTRAL_API_KEY no está configurada y LLM_PROVIDER=mistral la exige."
        )
    return api_key


def build_chat_model(role: str) -> BaseChatModel:
    """Construye el modelo de chat del rol indicado para el proveedor configurado."""
    if role not in OLLAMA_PREFIX_BY_ROLE:
        raise LLMConfigurationError(f"Rol de LLM desconocido: {role}")

    settings = get_settings()
    provider = settings.llm_provider_name()

    if provider == "mistral":
        return ChatMistralAI(
            model_name=getattr(settings, MISTRAL_MODEL_ATTR_BY_ROLE[role]),
            temperature=0,
            api_key=SecretStr(_mistral_api_key()),
            max_tokens=settings.mistral_max_tokens,
            timeout=settings.mistral_request_timeout_seconds,
        )

    if provider != "ollama":
        raise LLMConfigurationError(
            f"LLM_PROVIDER no reconocido: '{settings.llm_provider}'. Usa 'ollama' o 'mistral'."
        )

    prefix = OLLAMA_PREFIX_BY_ROLE[role]
    return ChatOllama(
        model=getattr(settings, f"{prefix}_model"),
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

    ensure_ollama_available()
