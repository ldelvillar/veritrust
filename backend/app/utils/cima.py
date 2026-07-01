"""Cliente del API REST de AEMPS CIMA para recuperar fichas técnicas de medicamentos."""

import logging
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.utils.evidence import EvidenceRetrievalError

logger = logging.getLogger(__name__)

_MEDICAMENTOS_PATH = "/medicamentos"
_DETALLE_URL = "https://cima.aemps.es/cima/publico/detalle.html?nregistro="

# Tipo de documento en CIMA: 1 = ficha técnica, 2 = prospecto.
_FICHA_TECNICA_TIPO = 1
# Cota del texto que se envía al juez; la ficha técnica completa es demasiado larga.
_ABSTRACT_MAX_CHARS = 2000


def _ficha_tecnica_html_url(result: dict) -> str | None:
    """Devuelve la URL HTML de la ficha técnica de un medicamento, si existe."""
    for doc in result.get("docs") or []:
        if doc.get("tipo") == _FICHA_TECNICA_TIPO:
            url = str(doc.get("urlHtml") or "").strip()
            if url:
                return url
    return None


def _estado_year(result: dict) -> str | None:
    """Deriva el año de autorización desde el timestamp (epoch ms) de ``estado``."""
    estado = result.get("estado")
    if not isinstance(estado, dict):
        return None
    for key in ("aut", "rev"):
        raw = estado.get(key)
        if isinstance(raw, int):
            try:
                return str(datetime.fromtimestamp(raw / 1000, tz=timezone.utc).year)
            except (ValueError, OSError, OverflowError):
                return None
    return None


def _fetch_ficha_tecnica_text(url: str, timeout: int) -> str | None:
    """Descarga la ficha técnica HTML y la reduce a texto acotado para el juez.

    Un fallo aquí no es crítico: la fuente se conserva sin ``abstract``.
    """
    try:
        response = requests.get(url, timeout=timeout, headers={"Accept": "text/html"})
        response.raise_for_status()
    except requests.exceptions.RequestException:
        logger.warning(
            "[CIMA] No se pudo descargar la ficha técnica; se omite el texto"
        )
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    text = soup.get_text(separator=" ", strip=True)
    return text[:_ABSTRACT_MAX_CHARS] or None


def _map_result(result: dict, *, timeout: int) -> dict | None:
    """Mapea un medicamento de CIMA a los metadatos que persistimos.

    El ``abstract`` es transitorio: solo se usa para juzgar la relevancia.
    """
    title = str(result.get("nombre") or "").strip()
    if not title:
        return None

    nregistro = str(result.get("nregistro") or "").strip()
    ft_url = _ficha_tecnica_html_url(result)
    url = ft_url or (
        f"{_DETALLE_URL}{nregistro}" if nregistro else "https://cima.aemps.es/"
    )
    abstract = _fetch_ficha_tecnica_text(ft_url, timeout) if ft_url else None
    return {
        "title": title,
        "url": url,
        "source": "AEMPS",
        "year": _estado_year(result),
        "abstract": abstract,
    }


def search_evidence(query: str, *, max_results: int) -> list[dict]:
    """Busca medicamentos en CIMA por nombre y devuelve metadatos con su ficha técnica.

    ``query`` es el nombre del medicamento o principio activo (en español). Lanza
    ``EvidenceRetrievalError`` ante fallos de red o respuestas no parseables en la
    búsqueda; el nodo investigador la captura y degrada con elegancia.
    """
    cleaned = query.strip()
    if not cleaned:
        return []

    settings = get_settings()
    timeout = settings.cima_timeout_seconds

    try:
        response = requests.get(
            f"{settings.cima_base_url}{_MEDICAMENTOS_PATH}",
            params={"nombre": cleaned},
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        raise EvidenceRetrievalError(f"Error al consultar CIMA: {e}") from e

    results = payload.get("resultados") or []
    mapped = [_map_result(item, timeout=timeout) for item in results[:max_results]]
    return [item for item in mapped if item is not None]
