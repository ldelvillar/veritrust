"""Este módulo contiene la función para extraer el texto de una URL."""

import requests
from bs4 import BeautifulSoup


class URLExtractionError(Exception):
    """Excepción lanzada cuando ocurre un error al extraer el texto de la URL."""


def extract_text_from_url(url: str) -> str:
    """Extrae el texto de una página web dada su URL."""
    if not url.startswith(("http://", "https://")):
        raise URLExtractionError("La URL debe comenzar con http:// o https://")

    try:
        # Añadir un User-Agent general
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise URLExtractionError(f"Error al conectar con la URL: {e}") from e

    soup = BeautifulSoup(response.text, "html.parser")

    # Eliminar etiquetas que aportan ruido
    for tag in soup(
        ["script", "style", "noscript", "header", "footer", "nav", "aside", "iframe"]
    ):
        tag.extract()

    text = soup.get_text(separator="\n", strip=True)
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())

    if not text:
        raise URLExtractionError(
            "No se pudo extraer texto relevante de la URL proporcionada."
        )

    return text
