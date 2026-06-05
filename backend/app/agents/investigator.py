"""Agente investigador: recupera evidencia biomédica de Europe PMC."""

import logging
from concurrent.futures import ThreadPoolExecutor

from app.utils.europepmc import EvidenceRetrievalError, search_evidence

logger = logging.getLogger(__name__)

# Cotas para acotar latencia y coste del pipeline frente a Europe PMC.
EVIDENCE_MAX_STATEMENTS = 5
EVIDENCE_RESULTS_PER_STATEMENT = 3
EVIDENCE_MAX_SOURCES = 8


def _merge_sources(hits: list[tuple[dict, str | None]]) -> list[dict]:
    """Funde fuentes repetidas por URL, acumulando las afirmaciones que respaldan."""
    by_url: dict[str, dict] = {}
    for hit, statement in hits:
        url = hit["url"]
        source = by_url.get(url)
        if source is None:
            source = {**hit, "statements": []}
            by_url[url] = source
        if statement and statement not in source["statements"]:
            source["statements"].append(statement)
    return list(by_url.values())


def _search_one(query: str) -> list[dict] | None:
    """Busca evidencia para una afirmación; devuelve ``None`` si Europe PMC falla."""
    try:
        return search_evidence(query, max_results=EVIDENCE_RESULTS_PER_STATEMENT)
    except EvidenceRetrievalError:
        logger.warning("[Investigador] Fallo recuperando evidencia; se continúa")
        return None


def investigator(state: dict) -> dict:
    """Recupera literatura biomédica para las afirmaciones y calcula su cobertura."""
    logger.info("[Investigador] Buscando evidencia en Europe PMC")

    translated = state.get("translated_statements", [])
    originals = state.get("extracted_statements", [])

    if not translated:
        return {"sources": [], "evidence_coverage": 0.0}

    pairs = list(zip(translated, originals + [None] * len(translated)))[
        :EVIDENCE_MAX_STATEMENTS
    ]
    # Descarta traducciones vacías (relleno) antes de consultar Europe PMC.
    valid_pairs = [
        (str(query), original)
        for query, original in pairs
        if query and str(query).strip()
    ]
    attempted = len(valid_pairs)
    if not valid_pairs:
        return {"sources": [], "evidence_coverage": 0.0}

    # Las consultas son I/O de red independiente: se lanzan en paralelo para que
    # la latencia total sea ~una llamada en vez de la suma de todas.
    with ThreadPoolExecutor(max_workers=len(valid_pairs)) as pool:
        results = list(pool.map(_search_one, [query for query, _ in valid_pairs]))

    collected: list[tuple[dict, str | None]] = []
    errored = 0
    covered = 0
    for (_, original), hits in zip(valid_pairs, results):
        if hits is None:
            errored += 1
            continue
        if hits:
            covered += 1
            collected.extend((hit, original) for hit in hits)

    sources = _merge_sources(collected)[:EVIDENCE_MAX_SOURCES]

    if errored == attempted:
        # Caída total del servicio: no penalizamos el veredicto por nuestra
        # infraestructura, solo por la ausencia real de literatura.
        coverage = 1.0
    else:
        coverage = covered / attempted

    logger.info("[Investigador] %d fuentes (cobertura %.2f)", len(sources), coverage)
    return {"sources": sources, "evidence_coverage": coverage}
