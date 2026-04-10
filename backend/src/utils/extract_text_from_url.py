"""Este módulo contiene la función para extraer el texto de una URL."""

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class URLExtractionError(Exception):
    """Excepción lanzada cuando ocurre un error al extraer el texto de la URL."""


def _is_public_ip(ip_str: str) -> bool:
    """Devuelve True si la IP es pública y apta para conexiones salientes."""
    ip = ipaddress.ip_address(ip_str)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validate_public_url(url: str) -> None:
    """Valida que la URL no apunte a destinos locales o redes internas."""
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise URLExtractionError("La URL debe comenzar con http:// o https://")

    if not parsed.hostname:
        raise URLExtractionError("La URL no contiene un host válido")

    host = parsed.hostname.strip().lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise URLExtractionError(
            "No se permite extraer contenido desde URLs locales o de red interna"
        )

    try:
        addrinfo = socket.getaddrinfo(host, parsed.port or 80, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise URLExtractionError(f"No se pudo resolver el host de la URL: {e}") from e

    resolved_ips = {
        str(entry[4][0]) for entry in addrinfo if isinstance(entry[4][0], str)
    }
    if not resolved_ips:
        raise URLExtractionError("No se pudo resolver ninguna IP para el host indicado")

    if not all(_is_public_ip(ip) for ip in resolved_ips):
        raise URLExtractionError(
            "No se permite extraer contenido desde URLs locales o de red interna"
        )


def extract_text_from_url(url: str) -> str:
    """Extrae el texto de una página web dada su URL."""
    _validate_public_url(url)

    try:
        # Añadir un User-Agent general
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        current_url = url
        max_redirects = 5

        for _ in range(max_redirects + 1):
            _validate_public_url(current_url)
            response = requests.get(
                current_url,
                headers=headers,
                timeout=10,
                allow_redirects=False,
            )

            if 300 <= response.status_code < 400:
                location = response.headers.get("Location")
                if not location:
                    raise URLExtractionError(
                        "La URL devolvió una redirección inválida sin cabecera Location"
                    )
                current_url = urljoin(current_url, location)
                continue

            response.raise_for_status()
            break
        else:
            raise URLExtractionError(
                "Demasiadas redirecciones al intentar acceder a la URL"
            )
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
