"""NCBI E-utilities (PubMed) client that retrieves biomedical literature."""

import logging
import threading
from time import monotonic, sleep
from xml.etree import ElementTree

import requests

from app.core.config import get_settings
from app.utils.evidence import EvidenceRetrievalError, failure_cause

logger = logging.getLogger(__name__)

_ESEARCH_PATH = "/esearch.fcgi"
_EFETCH_PATH = "/efetch.fcgi"

# Below NCBI's 10 requests per second with an api_key and 3 without, leaving a margin for network jitter.
_REQUESTS_PER_SECOND_WITH_KEY = 8.0
_REQUESTS_PER_SECOND_WITHOUT_KEY = 2.5

# Earliest instant the next request may start, shared by every thread of the process.
_next_slot = 0.0
_slot_lock = threading.Lock()


def _wait_for_slot(api_key: str | None) -> None:
    """Wait until NCBI's per-second limit lets the next request start."""
    global _next_slot
    rate = (
        _REQUESTS_PER_SECOND_WITH_KEY if api_key else _REQUESTS_PER_SECOND_WITHOUT_KEY
    )
    with _slot_lock:
        now = monotonic()
        slot = max(now, _next_slot)
        _next_slot = slot + 1 / rate
    # Sleeps outside the lock, so the other threads can book the following slots.
    sleep(slot - now)


def _extract_pmids(payload: dict, max_results: int) -> list[str]:
    """Read the PMID list of the esearch result."""
    ids = ((payload.get("esearchresult") or {}).get("idlist")) or []
    return [str(pmid).strip() for pmid in ids if str(pmid).strip()][:max_results]


def _article_url(pmid: str, doi: str) -> str:
    """Build a stable URL, the DOI if any and otherwise the PubMed record."""
    if doi:
        return f"https://doi.org/{doi}"
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    return "https://pubmed.ncbi.nlm.nih.gov/"


def _node_text(node: ElementTree.Element | None) -> str:
    """Concatenate the text of a node and its children into one string."""
    return " ".join(node.itertext()).strip() if node is not None else ""


def _map_article(article: ElementTree.Element) -> dict | None:
    """Map a <PubmedArticle> to the metadata we persist, where the ``abstract`` is transient and only used to judge relevance."""
    citation = article.find("MedlineCitation")
    art = citation.find("Article") if citation is not None else None
    if citation is None or art is None:
        return None

    title = _node_text(art.find("ArticleTitle"))
    if not title:
        return None

    abstract = " ".join(
        _node_text(node) for node in art.findall("Abstract/AbstractText")
    ).strip()
    journal = _node_text(art.find("Journal/Title"))
    year = _node_text(art.find("Journal/JournalIssue/PubDate/Year"))

    doi = ""
    for article_id in article.findall("PubmedData/ArticleIdList/ArticleId"):
        if article_id.get("IdType") == "doi" and article_id.text:
            doi = article_id.text.strip()
            break

    pmid = _node_text(citation.find("PMID"))
    return {
        "title": title,
        "url": _article_url(pmid, doi),
        "source": journal or None,
        "year": year or None,
        "abstract": abstract or None,
    }


def search_evidence(query: str, *, max_results: int) -> list[dict]:
    """Search PubMed articles for ``query``, raising ``EvidenceRetrievalError`` on network failures or unparseable responses."""
    cleaned = query.strip()
    if not cleaned:
        return []

    settings = get_settings()
    base = settings.pubmed_base_url
    api_key = settings.pubmed_api_key

    search_params: dict[str, str | int] = {
        "db": "pubmed",
        "retmode": "json",
        "term": cleaned,
        "retmax": max_results,
        "sort": "relevance",
    }
    if api_key:
        search_params["api_key"] = api_key

    try:
        _wait_for_slot(api_key)
        search_response = requests.get(
            f"{base}{_ESEARCH_PATH}",
            params=search_params,
            timeout=settings.pubmed_timeout_seconds,
            headers={"Accept": "application/json"},
        )
        search_response.raise_for_status()
        pmids = _extract_pmids(search_response.json(), max_results)
        if not pmids:
            return []

        fetch_params = {"db": "pubmed", "retmode": "xml", "id": ",".join(pmids)}
        if api_key:
            fetch_params["api_key"] = api_key
        _wait_for_slot(api_key)
        fetch_response = requests.get(
            f"{base}{_EFETCH_PATH}",
            params=fetch_params,
            timeout=settings.pubmed_timeout_seconds,
        )
        fetch_response.raise_for_status()
        root = ElementTree.fromstring(fetch_response.content)
    except (
        requests.exceptions.RequestException,
        ValueError,
        ElementTree.ParseError,
    ) as e:
        # Not chained, since the requests error carries the URL with the query and the api_key.
        raise EvidenceRetrievalError(
            f"Error al consultar PubMed: {failure_cause(e)}"
        ) from None

    mapped = [_map_article(article) for article in root.findall("PubmedArticle")]
    return [item for item in mapped if item][:max_results]
