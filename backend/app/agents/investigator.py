"""Agente investigador: recupera evidencia biomédica de Europe PMC."""

import logging

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

    collected: list[tuple[dict, str | None]] = []
    attempted = 0
    errored = 0
    covered = 0
    for query, original in pairs:
        if not query or not str(query).strip():
            continue
        attempted += 1
        try:
            hits = search_evidence(
                str(query), max_results=EVIDENCE_RESULTS_PER_STATEMENT
            )
        except EvidenceRetrievalError:
            logger.warning("[Investigador] Fallo recuperando evidencia; se continúa")
            errored += 1
            continue
        if hits:
            covered += 1
            for hit in hits:
                collected.append((hit, original))

    sources = _merge_sources(collected)[:EVIDENCE_MAX_SOURCES]

    if attempted and errored == attempted:
        # Caída total del servicio: no penalizamos el veredicto por nuestra
        # infraestructura, solo por la ausencia real de literatura.
        coverage = 1.0
    elif attempted:
        coverage = covered / attempted
    else:
        coverage = 0.0

    logger.info("[Investigador] %d fuentes (cobertura %.2f)", len(sources), coverage)
    return {"sources": sources, "evidence_coverage": coverage}
