"""Utilidad para arrancar el servidor local de Ollama si no está activo."""

import sys
import time
import subprocess
import urllib
import urllib.request
import urllib.error


def start_ollama() -> None:
    """
    Comprueba si el servidor local de Ollama está activo.
    Si no lo está, lo arranca en segundo plano.
    """
    url = "http://localhost:11434/"
    try:
        # Intentar conectar al puerto por defecto de Ollama
        with urllib.request.urlopen(url, timeout=2):
            pass
    except urllib.error.URLError:
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(3)
        except FileNotFoundError:
            print(
                "Error: No se encuentra 'Ollama' en el sistema. Asegúrate de tenerlo instalado."
            )
            sys.exit(1)


if __name__ == "__main__":
    start_ollama()
    print("Servidor de Ollama arrancado.")
