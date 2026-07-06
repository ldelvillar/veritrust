"""Utilidad para verificar que el servidor de Ollama está activo."""

import http.client
import json
import logging
import time
import urllib.request

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OllamaStartupError(RuntimeError):
    """Error de inicialización del servidor de Ollama."""


def _missing_models(url: str) -> list[str]:
    """Devuelve los modelos configurados que el servidor de Ollama no tiene descargados."""
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
    # "llama3" en Settings debe casar con "llama3:latest" en el servidor.
    base_names = {name.split(":", 1)[0] for name in available}
    return sorted(m for m in wanted if m not in available and m not in base_names)


def ensure_ollama_available(url: str | None = None) -> None:
    """
    Verifica que Ollama responde en la URL indicada y avisa si faltan modelos.
    Reintenta hasta 20 veces (10 s) antes de lanzar OllamaStartupError.
    Si no se pasa una URL, se usa ``Settings.ollama_base_url``.
    """
    if url is None:
        url = get_settings().ollama_base_url

    # OSError cubre URLError y el TimeoutError de un servidor colgado; HTTPException, respuestas corruptas.
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
        # El check de modelos es secundario: si /api/tags falla, no bloquea el arranque.
        return

    # Aviso ruidoso sin tumbar el proceso: los análisis fallarán por fila, con retry.
    if missing:
        logger.error(
            "Faltan modelos en Ollama (%s): %s. Descárgalos con 'ollama pull <modelo>'.",
            url,
            ", ".join(missing),
        )
