"""AEMPS CIMA REST API client that retrieves medicines' summaries of product characteristics."""

import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.utils.evidence import EvidenceRetrievalError, join_label_sections
from app.utils.ssrf import SSRFValidationError, resolve_public_host

logger = logging.getLogger(__name__)

_MEDICAMENTOS_PATH = "/medicamentos"
_DETALLE_URL = "https://cima.aemps.es/cima/publico/detalle.html?nregistro="

# CIMA document type, where 1 is the summary of product characteristics and 2 the package leaflet.
_FICHA_TECNICA_TIPO = 1
# Sections of the summary that serve the judge, indications and safety through overdose.
_SECTION_IDS = ("4.1", "4.3", "4.4", "4.6", "4.8", "4.9")
# Cap on the text of a summary without numbered sections, since the full one is too long.
_ABSTRACT_MAX_CHARS = 2000


def _ficha_tecnica_html_url(result: dict) -> str | None:
    """Return the HTML URL of a medicine's summary of product characteristics, if any."""
    for doc in result.get("docs") or []:
        if doc.get("tipo") == _FICHA_TECNICA_TIPO:
            url = str(doc.get("urlHtml") or "").strip()
            if url:
                return url
    return None


def _estado_year(result: dict) -> str | None:
    """Derive the authorisation year from the ``estado`` timestamp (epoch ms)."""
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


def _is_trusted_cima_url(url: str) -> bool:
    """Confirm that ``url`` lives on CIMA's official host and resolves to a public IP."""
    # urlparse raises ValueError on characters invalid under NFKC, so it is treated as untrusted.
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    cima_host = (urlparse(get_settings().cima_base_url).hostname or "").lower()
    if not cima_host or not (host == cima_host or host.endswith(f".{cima_host}")):
        return False
    # Parser differentials (e.g. a backslash in the authority) fool the host allowlist, so it must also resolve to a public IP.
    try:
        resolve_public_host(url)
    except SSRFValidationError:
        return False
    return True


def _fetch_ficha_tecnica_text(url: str, timeout: int) -> str | None:
    """Download the HTML summary and reduce it to bounded text for the judge, keeping the Source without ``abstract`` on failure."""
    # urlHtml comes from CIMA's response, not the user, and is pinned to the official host without redirects so it never reaches internal addresses.
    if not _is_trusted_cima_url(url):
        logger.warning("[CIMA] urlHtml fuera del host oficial; se omite el texto")
        return None

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"Accept": "text/html"},
            allow_redirects=False,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        logger.warning(
            "[CIMA] No se pudo descargar la ficha técnica; se omite el texto"
        )
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    sections = _key_sections(soup)
    if sections:
        return sections
    text = soup.get_text(separator=" ", strip=True)
    return text[:_ABSTRACT_MAX_CHARS] or None


def _key_sections(soup: BeautifulSoup) -> str | None:
    """Text of the summary's key sections, each with its heading, or ``None`` if it does not number them."""
    sections = []
    for heading in soup.find_all(["h1", "h2"], id=list(_SECTION_IDS)):
        body = []
        for sibling in heading.find_next_siblings():
            if sibling.name in ("h1", "h2"):
                break
            body.append(sibling.get_text(separator=" ", strip=True))
        sections.append(f"{heading.get_text(' ', strip=True)}: {' '.join(body)}")
    return join_label_sections(sections)


def _map_result(result: dict, *, timeout: int) -> dict | None:
    """Map a CIMA medicine to the metadata we persist, where the ``abstract`` is transient and only used to judge relevance."""
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
    """Search CIMA medicines by name or active ingredient (in Spanish), raising ``EvidenceRetrievalError`` on network failures or unparseable responses."""
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
