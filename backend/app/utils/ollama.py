"""Check that the Ollama server is up."""

import http.client
import json
import logging
import time
import urllib.request

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OllamaStartupError(RuntimeError):
    """Ollama server startup error."""


def _missing_models(url: str) -> list[str]:
    """Return the configured models the Ollama server has not downloaded."""
    settings = get_settings()
    wanted = {
        settings.ollama_extractor_model,
        settings.ollama_translator_model,
        settings.ollama_health_expert_model,
        settings.ollama_judge_model,
    }
    with urllib.request.urlopen(f"{url.rstrip('/')}/api/tags", timeout=5) as response:
        payload = json.load(response)
    available = {str(model.get("name", "")) for model in payload.get("models", [])}
    # "llama3" in Settings must match "llama3:latest" on the server.
    base_names = {name.split(":", 1)[0] for name in available}
    return sorted(m for m in wanted if m not in available and m not in base_names)


def ensure_ollama_available(url: str | None = None) -> None:
    """Check that Ollama answers at the URL, defaulting to ``Settings.ollama_base_url``, retrying 20 times (10 s) before raising OllamaStartupError."""
    if url is None:
        url = get_settings().ollama_base_url

    # OSError covers URLError and a hung server's TimeoutError, and HTTPException covers corrupt responses.
    for _ in range(20):
        try:
            with urllib.request.urlopen(url, timeout=2):
                break
        except (OSError, http.client.HTTPException):
            time.sleep(0.5)
    else:
        raise OllamaStartupError(
            f"Ollama no está disponible en {url}. Verifica que el servicio esté activo."
        )

    try:
        missing = _missing_models(url)
    except (OSError, ValueError, http.client.HTTPException):
        # The model check is secondary, so a failing /api/tags does not block startup.
        return

    # A loud warning without killing the process, since analyses will fail per row with retry.
    if missing:
        logger.error(
            "Faltan modelos en Ollama (%s): %s. Descárgalos con 'ollama pull <modelo>'.",
            url,
            ", ".join(missing),
        )
