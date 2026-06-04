"""Cliente del API REST de Europe PMC para recuperar literatura biomédica."""

import logging

import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_SEARCH_PATH = "/search"


class EvidenceRetrievalError(Exception):
    """Excepción lanzada cuando falla la consulta a Europe PMC."""


def _build_article_url(result: dict) -> str:
    """Construye una URL estable al artículo: DOI si existe, si no Europe PMC."""
    doi = (result.get("doi") or "").strip()
    if doi:
        return f"https://doi.org/{doi}"

    source = (result.get("source") or "").strip()
    article_id = (result.get("id") or "").strip()
    if source and article_id:
        return f"https://europepmc.org/article/{source}/{article_id}"

    return "https://europepmc.org/"


def _map_result(result: dict) -> dict:
    """Mapea un resultado de Europe PMC a los metadatos que persistimos."""
    journal = (result.get("journalTitle") or "").strip()
    year = str(result.get("pubYear")).strip() if result.get("pubYear") else None
    return {
        "title": (result.get("title") or "").strip(),
        "url": _build_article_url(result),
        "source": journal or None,
        "year": year,
    }


def search_evidence(query: str, *, max_results: int) -> list[dict]:
    """Busca artículos en Europe PMC para ``query`` y devuelve metadatos saneados.

    Lanza ``EvidenceRetrievalError`` ante fallos de red o respuestas no parseables;
    el nodo investigador la captura y degrada con elegancia.
    """
    cleaned = query.strip()
    if not cleaned:
        return []

    settings = get_settings()
    params = {
        "query": cleaned,
        "format": "json",
        "pageSize": max_results,
        "resultType": "lite",
    }

    try:
        response = requests.get(
            f"{settings.europepmc_base_url}{_SEARCH_PATH}",
            params=params,
            timeout=settings.europepmc_timeout_seconds,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        raise EvidenceRetrievalError(f"Error al consultar Europe PMC: {e}") from e

    results = (payload.get("resultList") or {}).get("result") or []
    mapped = [_map_result(item) for item in results]
    return [item for item in mapped if item["title"]][:max_results]
