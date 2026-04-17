"""Utilidad para arrancar el servidor local de Ollama si no está activo."""

import time
import subprocess
import urllib.error
import urllib.request


class OllamaStartupError(RuntimeError):
    """Error de inicialización del servidor local de Ollama."""


def _is_ollama_available(url: str, *, timeout: float = 2) -> bool:
    """Comprueba si Ollama responde en el endpoint indicado."""
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except urllib.error.URLError:
        return False


def start_ollama() -> None:
    """
    Comprueba si el servidor local de Ollama está activo.
    Si no lo está, lo arranca en segundo plano.
    """
    url = "http://localhost:11434/"
    if _is_ollama_available(url):
        return

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as exc:
        raise OllamaStartupError(
            "No se encuentra 'Ollama' en el sistema. Asegúrate de tenerlo instalado."
        ) from exc

    time.sleep(3)

    if not _is_ollama_available(url):
        raise OllamaStartupError(
            "Ollama no respondió tras el arranque automático en localhost:11434."
        )
