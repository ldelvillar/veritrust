"""Cliente del API openFDA para recuperar fichas de medicamentos (drug labels)."""

import logging

import requests

from app.core.config import get_settings
from app.utils.evidence import EvidenceRetrievalError

logger = logging.getLogger(__name__)

_LABEL_PATH = "/drug/label.json"
_DAILYMED_URL = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid="

# Secciones de la ficha que sirven para juzgar la relevancia de la afirmación.
_ABSTRACT_SECTIONS = (
    "purpose",
    "indications_and_usage",
    "warnings",
    "adverse_reactions",
    "contraindications",
)
# Cota del texto que se envía al juez; la ficha completa es demasiado larga.
_ABSTRACT_MAX_CHARS = 1500


def _first(values: object) -> str:
    """Devuelve el primer elemento de un campo openFDA (siempre un array)."""
    if isinstance(values, list) and values:
        return str(values[0]).strip()
    return ""


def _build_abstract(result: dict) -> str | None:
    """Une las secciones clave de la ficha en un resumen acotado para el juez."""
    parts: list[str] = []
    for section in _ABSTRACT_SECTIONS:
        value = result.get(section)
        if isinstance(value, list) and value:
            parts.append(" ".join(str(item).strip() for item in value if item))
    text = " ".join(part for part in parts if part).strip()
    return text[:_ABSTRACT_MAX_CHARS] or None


def _map_result(result: dict) -> dict:
    """Mapea una ficha de openFDA a los metadatos que persistimos.

    El ``abstract`` es transitorio: solo se usa para juzgar la relevancia.
    """
    openfda = result.get("openfda") or {}
    title = _first(openfda.get("brand_name")) or _first(openfda.get("generic_name"))
    set_id = str(result.get("set_id") or "").strip()
    effective = str(result.get("effective_time") or "").strip()
    return {
        "title": title,
        "url": f"{_DAILYMED_URL}{set_id}"
        if set_id
        else "https://dailymed.nlm.nih.gov/",
        "source": "FDA",
        "year": effective[:4] or None,
        "abstract": _build_abstract(result),
    }


def search_evidence(query: str, *, max_results: int) -> list[dict]:
    """Busca fichas de medicamentos en openFDA para ``query`` y devuelve metadatos.

    Lanza ``EvidenceRetrievalError`` ante fallos de red o respuestas no parseables;
    el nodo investigador la captura y degrada con elegancia. Una búsqueda sin
    resultados devuelve 404 en openFDA: se trata como lista vacía, no como error.
    """
    cleaned = query.strip()
    if not cleaned:
        return []

    settings = get_settings()
    params: dict[str, object] = {"search": cleaned, "limit": max_results}
    if settings.openfda_api_key:
        params["api_key"] = settings.openfda_api_key

    try:
        response = requests.get(
            f"{settings.openfda_base_url}{_LABEL_PATH}",
            params=params,
            timeout=settings.openfda_timeout_seconds,
            headers={"Accept": "application/json"},
        )
        # openFDA responde 404 cuando no hay coincidencias: no es un fallo.
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        raise EvidenceRetrievalError(f"Error al consultar openFDA: {e}") from e

    results = payload.get("results") or []
    mapped = [_map_result(item) for item in results]
    return [item for item in mapped if item["title"]][:max_results]
