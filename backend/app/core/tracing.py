"""Creates the Langfuse client and the callback handler that trace the pipeline."""

from typing import Any

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.core.config import get_settings

_settings = get_settings()

tracing_enabled = bool(_settings.langfuse_public_key and _settings.langfuse_secret_key)

# A placeholder key registers a disabled client, so @observe reuses it instead of building one per call.
_public_key = _settings.langfuse_public_key if tracing_enabled else "tracing-disabled"
_secret_key = _settings.langfuse_secret_key if tracing_enabled else "tracing-disabled"


def _redact(*, data: Any, **kwargs: Any) -> Any:
    """Replace a span's content with a placeholder, keeping its timings, tokens and errors."""
    return None if data is None else "<redacted>"


langfuse = Langfuse(
    public_key=_public_key,
    secret_key=_secret_key,
    base_url=_settings.langfuse_base_url,
    environment=_settings.environment,
    tracing_enabled=tracing_enabled,
    mask=_redact if _settings.langfuse_mask_content else None,
)

langfuse_handler = CallbackHandler(public_key=_public_key)
