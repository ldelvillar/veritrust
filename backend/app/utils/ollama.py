"""Utilidad para verificar que el servidor de Ollama está activo."""

import time
import urllib.error
import urllib.request

from app.core.config import get_settings


class OllamaStartupError(RuntimeError):
    """Error de inicialización del servidor de Ollama."""


def ensure_ollama_available(url: str | None = None) -> None:
    """
    Verifica que Ollama responde en la URL indicada.
    Reintenta hasta 20 veces (10 s) antes de lanzar OllamaStartupError.
    Si no se pasa una URL, se usa ``Settings.ollama_base_url``.
    """
    if url is None:
        url = get_settings().ollama_base_url

    for _ in range(20):
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except urllib.error.URLError:
            time.sleep(0.5)

    raise OllamaStartupError(
        f"Ollama no está disponible en {url}. Verifica que el servicio esté activo."
    )
