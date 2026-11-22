"""Creates the Langfuse client and the callback handler that trace the pipeline."""

from functools import cache

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.core.config import get_settings

_DISABLED_KEY = "tracing-disabled"


def tracing_enabled() -> bool:
    """Return whether the settings turn Langfuse tracing on."""
    return get_settings().langfuse_enabled()


@cache
def _public_key() -> str:
    # A placeholder key registers a disabled client, so @observe reuses it instead of building one per call.
    return get_settings().langfuse_public_key if tracing_enabled() else _DISABLED_KEY


@cache
def get_langfuse() -> Langfuse:
    """Build the Langfuse client from the settings on first use."""
    settings = get_settings()
    enabled = tracing_enabled()
    return Langfuse(
        public_key=_public_key(),
        secret_key=settings.langfuse_secret_key if enabled else _DISABLED_KEY,
        base_url=settings.langfuse_base_url,
        environment=settings.environment,
        tracing_enabled=enabled,
    )


@cache
def get_langfuse_handler() -> CallbackHandler:
    """Build the LangChain callback handler bound to the Langfuse client."""
    # The handler finds its client by the same cached public key, so the client is registered first.
    get_langfuse()
    return CallbackHandler(public_key=_public_key())
