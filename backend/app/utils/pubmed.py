"""Cliente de NCBI E-utilities (PubMed) para recuperar literatura biomédica."""

import logging
from xml.etree import ElementTree

import requests

from app.core.config import get_settings
from app.utils.evidence import EvidenceRetrievalError

logger = logging.getLogger(__name__)

_ESEARCH_PATH = "/esearch.fcgi"
_EFETCH_PATH = "/efetch.fcgi"


def _extract_pmids(payload: dict, max_results: int) -> list[str]:
    """Lee la lista de PMIDs del resultado de esearch."""
    ids = ((payload.get("esearchresult") or {}).get("idlist")) or []
    return [str(pmid).strip() for pmid in ids if str(pmid).strip()][:max_results]


def _article_url(pmid: str, doi: str) -> str:
    """Construye una URL estable: DOI si existe, si no la ficha de PubMed."""
    if doi:
        return f"https://doi.org/{doi}"
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    return "https://pubmed.ncbi.nlm.nih.gov/"


def _node_text(node: ElementTree.Element | None) -> str:
    """Concatena el texto de un nodo (y sus hijos) en una sola cadena."""
    return " ".join(node.itertext()).strip() if node is not None else ""


def _map_article(article: ElementTree.Element) -> dict | None:
    """Mapea un <PubmedArticle> a los metadatos que persistimos.

    El ``abstract`` es transitorio: solo se usa para juzgar la relevancia.
    """
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
    """Busca artículos en PubMed para ``query`` y devuelve metadatos saneados.

    Lanza ``EvidenceRetrievalError`` ante fallos de red o respuestas no parseables;
    el nodo investigador la captura y degrada con elegancia.
    """
    cleaned = query.strip()
    if not cleaned:
        return []

    settings = get_settings()
    base = settings.pubmed_base_url
    api_key = settings.pubmed_api_key

    search_params = {
        "db": "pubmed",
        "retmode": "json",
        "term": cleaned,
        "retmax": max_results,
        "sort": "relevance",
    }
    if api_key:
        search_params["api_key"] = api_key

    try:
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
        raise EvidenceRetrievalError(f"Error al consultar PubMed: {e}") from e

    mapped = [_map_article(article) for article in root.findall("PubmedArticle")]
    return [item for item in mapped if item][:max_results]
