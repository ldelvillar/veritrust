"""Agente investigador: recupera evidencia biomédica de Europe PMC."""

import logging
from concurrent.futures import ThreadPoolExecutor

from app.agents.relevance import keep_relevant
from app.prompts.agents import Prompts
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
            # Excluye el abstract: solo sirve para juzgar relevancia, no se persiste.
            source = {key: value for key, value in hit.items() if key != "abstract"}
            source["statements"] = []
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


def investigator(state: dict, prompts: Prompts | None = None) -> dict:
    """Recupera literatura biomédica relevante y calcula la cobertura de evidencia."""
    logger.info("[Investigador] Buscando evidencia en Europe PMC")

    translated = state.get("translated_statements", [])
    queries = state.get("search_queries", [])
    originals = state.get("extracted_statements", [])

    if not translated:
        return {"sources": [], "evidence_coverage": 0.0}

    # Por afirmación: consulta enfocada (con respaldo en la traducción), texto en
    # inglés para juzgar la relevancia y original en español para enlazar la fuente.
    triples = [
        (
            queries[i]
            if i < len(queries) and queries[i] and str(queries[i]).strip()
            else translated[i],
            translated[i] or "",
            originals[i] if i < len(originals) else None,
        )
        for i in range(len(translated))
    ][:EVIDENCE_MAX_STATEMENTS]
    # Descarta consultas vacías (relleno) antes de llamar a Europe PMC.
    valid = [
        (str(query), claim, original)
        for query, claim, original in triples
        if query and str(query).strip()
    ]
    attempted = len(valid)
    if not valid:
        return {"sources": [], "evidence_coverage": 0.0}

    # Las consultas son I/O de red independiente: se lanzan en paralelo para que
    # la latencia total sea ~una llamada en vez de la suma de todas.
    with ThreadPoolExecutor(max_workers=len(valid)) as pool:
        results = list(pool.map(_search_one, [query for query, _, _ in valid]))

    judge_prompt = prompts.judge.text if prompts else None

    collected: list[tuple[dict, str | None]] = []
    errored = 0
    covered = 0
    for (query, claim, original), hits in zip(valid, results):
        if hits is None:
            errored += 1
            continue
        # Filtra las fuentes irrelevantes con el juez; sin prompt se conservan todas.
        relevant = (
            keep_relevant(judge_prompt, claim or query, hits) if judge_prompt else hits
        )
        if relevant:
            covered += 1
            collected.extend((hit, original) for hit in relevant)

    sources = _merge_sources(collected)[:EVIDENCE_MAX_SOURCES]

    if errored == attempted:
        # Caída total del servicio: no penalizamos el veredicto por nuestra
        # infraestructura, solo por la ausencia real de literatura.
        coverage = 1.0
    else:
        coverage = covered / attempted

    logger.info("[Investigador] %d fuentes (cobertura %.2f)", len(sources), coverage)
    return {"sources": sources, "evidence_coverage": coverage}
