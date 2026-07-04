"""Este módulo contiene la función para extraer el texto de una URL."""

from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.schemas.analysis import MAX_INPUT_TEXT_LENGTH
from app.utils.ssrf import (
    SSRFValidationError,
    build_pinned_session,
    resolve_public_host,
)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)

MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024  # 5 MB de HTML bruto


class URLExtractionError(Exception):
    """Excepción lanzada cuando ocurre un error al extraer el texto de la URL."""


def _resolve_public_host(url: str) -> tuple[str, str]:
    """Valida la URL vía la comprobación SSRF y traduce el fallo al error del dominio."""
    try:
        return resolve_public_host(url)
    except SSRFValidationError as e:
        raise URLExtractionError(str(e)) from e


def _read_capped_body(response: requests.Response) -> bytes:
    """Lee el cuerpo en streaming hasta ``MAX_DOWNLOAD_BYTES`` y trunca el resto."""
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=8192):
        if not chunk:
            continue
        chunks.append(chunk)
        total += len(chunk)
        if total >= MAX_DOWNLOAD_BYTES:
            break
    return b"".join(chunks)[:MAX_DOWNLOAD_BYTES]


def extract_text_from_url(url: str) -> str:
    """Extrae el texto de una página web dada su URL."""
    current_url = url
    max_redirects = 5
    raw_body = b""

    try:
        for _ in range(max_redirects + 1):
            # Validar y resolver en el mismo paso; la conexión se fija a esta IP.
            host, pinned_ip = _resolve_public_host(current_url)
            parsed = urlparse(current_url)
            host_header = f"{host}:{parsed.port}" if parsed.port else host

            # stream=True: el cuerpo se lee acotado dentro de la sesión viva.
            with build_pinned_session(host, pinned_ip) as session:
                response = session.get(
                    current_url,
                    headers={"User-Agent": _USER_AGENT, "Host": host_header},
                    timeout=10,
                    allow_redirects=False,
                    stream=True,
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
                raw_body = _read_capped_body(response)
            break
        else:
            raise URLExtractionError(
                "Demasiadas redirecciones al intentar acceder a la URL"
            )
    except requests.exceptions.RequestException as e:
        raise URLExtractionError(f"Error al conectar con la URL: {e}") from e

    soup = BeautifulSoup(raw_body, "html.parser")

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

    # Acota el texto al mismo presupuesto que la entrada directa: una página
    # enorme no puede convertirse en un prompt sin límite para el pipeline LLM.
    return text[:MAX_INPUT_TEXT_LENGTH]
