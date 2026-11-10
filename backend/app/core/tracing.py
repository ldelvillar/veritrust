"""Creates the callback handlers for Langfuse tracing."""

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.core.config import get_settings

_settings = get_settings()

langfuse = Langfuse(
    public_key=_settings.langfuse_public_key,
    secret_key=_settings.langfuse_secret_key,
    base_url=_settings.langfuse_base_url,
    environment=_settings.environment,
    tracing_enabled=bool(
        _settings.langfuse_public_key and _settings.langfuse_secret_key
    ),
)

langfuse_handler = CallbackHandler(public_key=_settings.langfuse_public_key)
