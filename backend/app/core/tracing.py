"""Creates the Langfuse client and the callback handler that trace the pipeline."""

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.core.config import get_settings

_settings = get_settings()

tracing_enabled = _settings.langfuse_enabled()

# A placeholder key registers a disabled client, so @observe reuses it instead of building one per call.
_public_key = (
    _settings.langfuse_public_key.strip() if tracing_enabled else "tracing-disabled"
)
_secret_key = (
    _settings.langfuse_secret_key.strip() if tracing_enabled else "tracing-disabled"
)

langfuse = Langfuse(
    public_key=_public_key,
    secret_key=_secret_key,
    base_url=_settings.langfuse_base_url,
    environment=_settings.environment,
    tracing_enabled=tracing_enabled,
)

langfuse_handler = CallbackHandler(public_key=_public_key)
