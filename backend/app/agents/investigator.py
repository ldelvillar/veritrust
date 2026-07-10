"""Agente investigador: recupera evidencia de Europe PMC, PubMed, openFDA y CIMA."""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from app.agents.relevance import judge_evidence
from app.prompts.agents import Prompts
from app.utils.cima import search_evidence as search_cima
from app.utils.europepmc import search_evidence as search_europepmc
from app.utils.evidence import EvidenceRetrievalError
from app.utils.openfda import search_evidence as search_openfda
from app.utils.pubmed import search_evidence as search_pubmed

logger = logging.getLogger(__name__)

# Cotas para acotar latencia y coste del pipeline frente a las fuentes de evidencia.
EVIDENCE_MAX_STATEMENTS = 8
EVIDENCE_RESULTS_PER_STATEMENT = 3
EVIDENCE_MAX_SOURCES = 12


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


def _judge_claim(
    judge_prompt: str | None, query: str, claim: str, hits: list[dict]
) -> list[dict]:
    """Juzga las fuentes de una afirmación; falla en abierto conservándolas todas."""
    if not judge_prompt:
        return hits
    try:
        return judge_evidence(judge_prompt, claim or query, hits)
    except Exception:
        logger.warning(
            "[Investigador] Fallo juzgando la evidencia; se conservan las fuentes"
        )
        return hits


def investigator(state: dict, prompts: Prompts | None = None) -> dict:
    """Recupera literatura biomédica relevante y calcula la cobertura de evidencia."""
    logger.info(
        "[Investigador] Buscando evidencia en Europe PMC, PubMed, openFDA y CIMA"
    )

    translated = state.get("translated_statements", [])
    queries = state.get("search_queries", [])
    originals = state.get("extracted_statements", [])
    drug_terms = state.get("drug_terms", [])

    if not translated:
        return {"sources": [], "evidence_coverage": 0.0}

    quads = [
        (
            (
                queries[i]
                if i < len(queries) and queries[i] and str(queries[i]).strip()
                else translated[i]
            ),
            translated[i] or "",
            originals[i] if i < len(originals) else None,
            str(drug_terms[i]).strip() if i < len(drug_terms) and drug_terms[i] else "",
        )
        for i in range(len(translated))
    ]

    # Descarta consultas vacías (relleno) antes de llamar a las fuentes.
    valid = [
        (str(query), claim, original, drug_term)
        for query, claim, original, drug_term in quads
        if query and str(query).strip()
    ]

    # Denominador de la cobertura: toda afirmación válida, aunque la cota la deje sin buscar.
    total = len(valid)
    if not valid:
        return {"sources": [], "evidence_coverage": 0.0}
    searched = valid[:EVIDENCE_MAX_STATEMENTS]
    if len(searched) < total:
        logger.warning(
            "[Investigador] %d afirmaciones sin buscar por la cota de %d",
            total - len(searched),
            EVIDENCE_MAX_STATEMENTS,
        )

    # Fuentes de literatura: se consultan con la query enfocada en inglés.
    topic_sources = (search_europepmc, search_pubmed, search_openfda)

    # Cada par afirmación×fuente es I/O de red independiente: se lanzan todos en paralelo.
    tasks: list[tuple[int, str, Callable[..., list[dict]]]] = []
    per_claim_attempts = [0] * len(searched)
    for index, (query, _, _, drug_term) in enumerate(searched):
        for search in topic_sources:
            tasks.append((index, query, search))
            per_claim_attempts[index] += 1
        if drug_term:
            # CIMA (medicamentos) solo se consulta cuando la afirmación nombra un fármaco.
            tasks.append((index, drug_term, search_cima))
            per_claim_attempts[index] += 1

    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        outcomes = list(pool.map(lambda task: _search_source(*task), tasks))

    # Reagrupa por afirmación: una falla solo si TODAS sus fuentes consultadas caen.
    per_claim_hits: list[list[dict]] = [[] for _ in searched]
    per_claim_failures = [0] * len(searched)
    for index, hits in outcomes:
        if hits is None:
            per_claim_failures[index] += 1
        else:
            per_claim_hits[index].extend(hits)

    results: list[list[dict] | None] = [
        (
            None
            if per_claim_failures[index] == per_claim_attempts[index]
            else _dedupe_hits(per_claim_hits[index])
        )
        for index in range(len(searched))
    ]

    judge_prompt = prompts.judge.text if prompts else None

    # Afirmaciones con evidencia recuperada; una caída total (hits None) es un error.
    judgeable = [
        (query, claim, original, hits)
        for (query, claim, original, _), hits in zip(searched, results)
        if hits is not None
    ]
    errored = len(searched) - len(judgeable)

    # Se lanzan a la vez y el fallo de una no bloquea a las demás.
    if judge_prompt and judgeable:
        with ThreadPoolExecutor(max_workers=len(judgeable)) as pool:
            judged = list(
                pool.map(
                    lambda item: _judge_claim(judge_prompt, item[0], item[1], item[3]),
                    judgeable,
                )
            )
    else:
        judged = [hits for _, _, _, hits in judgeable]

    # Se reensambla en el orden original de las afirmaciones
    collected: list[tuple[dict, str | None]] = []
    covered = 0
    for (_, _, original, _), relevant in zip(judgeable, judged):
        if relevant:
            covered += 1
            collected.extend((hit, original) for hit in relevant)

    sources = _merge_sources(collected)[:EVIDENCE_MAX_SOURCES]

    if errored == len(searched):
        # Caída total: lo buscado no penaliza (infra nuestra); lo recortado por la cota sí.
        coverage = len(searched) / total
    else:
        coverage = covered / total

    logger.info("[Investigador] %d fuentes (cobertura %.2f)", len(sources), coverage)
    return {"sources": sources, "evidence_coverage": coverage}
