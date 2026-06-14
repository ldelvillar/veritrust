"""Agente investigador: recupera evidencia biomédica de Europe PMC y PubMed."""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from app.agents.relevance import judge_evidence
from app.prompts.agents import Prompts
from app.utils.europepmc import search_evidence as search_europepmc
from app.utils.evidence import EvidenceRetrievalError
from app.utils.pubmed import search_evidence as search_pubmed

logger = logging.getLogger(__name__)

# Cotas para acotar latencia y coste del pipeline frente a las fuentes de evidencia.
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
            # Excluye abstract/stance: el abstract solo sirve para juzgar y la
            # postura se guarda por afirmación dentro de "statements".
            source = {k: v for k, v in hit.items() if k not in ("abstract", "stance")}
            source["statements"] = []
            by_url[url] = source
        if statement and all(s["text"] != statement for s in source["statements"]):
            source["statements"].append(
                {"text": statement, "stance": hit.get("stance")}
            )
    return list(by_url.values())


def _dedupe_hits(hits: list[dict]) -> list[dict]:
    """Funde duplicados entre fuentes por URL, conservando el primero visto."""
    seen: set[str] = set()
    unique: list[dict] = []
    for hit in hits:
        url = hit.get("url")
        if url in seen:
            continue
        if url:
            seen.add(url)
        unique.append(hit)
    return unique


def _search_source(
    index: int, query: str, search: Callable[..., list[dict]]
) -> tuple[int, list[dict] | None]:
    """Consulta una fuente para una afirmación; ``None`` en sus hits si falla."""
    try:
        return index, search(query, max_results=EVIDENCE_RESULTS_PER_STATEMENT)
    except EvidenceRetrievalError:
        logger.warning("[Investigador] Fallo recuperando evidencia; se continúa")
        return index, None


def investigator(state: dict, prompts: Prompts | None = None) -> dict:
    """Recupera literatura biomédica relevante y calcula la cobertura de evidencia."""
    logger.info("[Investigador] Buscando evidencia en Europe PMC y PubMed")

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
    # Descarta consultas vacías (relleno) antes de llamar a las fuentes.
    valid = [
        (str(query), claim, original)
        for query, claim, original in triples
        if query and str(query).strip()
    ]
    attempted = len(valid)
    if not valid:
        return {"sources": [], "evidence_coverage": 0.0}

    # Se resuelven en cada llamada (no a nivel de módulo) para poder sustituirlas.
    evidence_sources = (search_europepmc, search_pubmed)

    # Cada par afirmación×fuente es I/O de red independiente: se lanzan todos en
    # paralelo para que la latencia total sea ~una llamada, no la suma de todas.
    tasks = [
        (index, query, search)
        for index, (query, _, _) in enumerate(valid)
        for search in evidence_sources
    ]
    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        outcomes = list(pool.map(lambda task: _search_source(*task), tasks))

    # Reagrupa por afirmación: una falla solo si TODAS sus fuentes caen.
    per_claim_hits: list[list[dict]] = [[] for _ in valid]
    per_claim_failures = [0] * len(valid)
    for index, hits in outcomes:
        if hits is None:
            per_claim_failures[index] += 1
        else:
            per_claim_hits[index].extend(hits)

    results: list[list[dict] | None] = [
        None
        if per_claim_failures[index] == len(evidence_sources)
        else _dedupe_hits(per_claim_hits[index])
        for index in range(len(valid))
    ]

    judge_prompt = prompts.judge.text if prompts else None

    collected: list[tuple[dict, str | None]] = []
    errored = 0
    covered = 0
    for (query, claim, original), hits in zip(valid, results):
        if hits is None:
            errored += 1
            continue
        # Juzga la evidencia (relevancia + postura); sin prompt se conservan todas.
        relevant = (
            judge_evidence(judge_prompt, claim or query, hits) if judge_prompt else hits
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
