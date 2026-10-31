"""Europe PMC REST API client that retrieves biomedical literature."""

import logging

import requests

from app.core.config import get_settings
from app.utils.evidence import EvidenceRetrievalError

logger = logging.getLogger(__name__)

_SEARCH_PATH = "/search"


def _build_article_url(result: dict) -> str:
    """Build a stable article URL, the DOI if any and otherwise Europe PMC."""
    doi = (result.get("doi") or "").strip()
    if doi:
        return f"https://doi.org/{doi}"

    source = (result.get("source") or "").strip()
    article_id = (result.get("id") or "").strip()
    if source and article_id:
        return f"https://europepmc.org/article/{source}/{article_id}"

    return "https://europepmc.org/"


def _map_result(result: dict) -> dict:
    """Map a Europe PMC result to the metadata we persist, where the ``abstract`` is transient and dropped before persisting the Source."""
    journal = (result.get("journalTitle") or "").strip()
    year = str(result.get("pubYear")).strip() if result.get("pubYear") else None
    return {
        "title": (result.get("title") or "").strip(),
        "url": _build_article_url(result),
        "source": journal or None,
        "year": year,
        "abstract": (result.get("abstractText") or "").strip() or None,
    }


def search_evidence(query: str, *, max_results: int) -> list[dict]:
    """Search Europe PMC articles for ``query``, raising ``EvidenceRetrievalError`` on network failures or unparseable responses."""
    cleaned = query.strip()
    if not cleaned:
        return []

    settings = get_settings()
    params: dict[str, str | int] = {
        "query": cleaned,
        "format": "json",
        "pageSize": max_results,
        # "core" includes the abstract, needed to judge relevance.
        "resultType": "core",
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
