"""Utilidad para verificar que el servidor local de Ollama está activo."""

import time
import urllib.error
import urllib.request


class OllamaStartupError(RuntimeError):
    """Error de inicialización del servidor local de Ollama."""


def ensure_ollama_available(url: str = "http://localhost:11434/") -> None:
    """
    Verifica que Ollama responde en la URL indicada.
    Reintenta hasta 20 veces (10 s) antes de lanzar OllamaStartupError.
    Ollama debe ser gestionado externamente (systemd, Docker, etc.).
    """
    for _ in range(20):
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except urllib.error.URLError:
            time.sleep(0.5)

    raise OllamaStartupError(
        "Ollama no está disponible en localhost:11434. "
        "Verifica que el servicio esté activo: systemctl status ollama"
    )
