"""Agente investigador: recupera evidencia de Europe PMC, PubMed, openFDA y CIMA."""

import logging
from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor

from app.agents.relevance import judge_stances
from app.agents.state import AgentState
from app.core.claim import (
    Claim,
    evidence_search,
    keep_shown_sources,
    source_records,
    with_hits,
    with_stances,
)
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


def _search_source(
    index: int, query: str, search: Callable[..., list[dict]]
) -> tuple[int, list[dict] | None]:
    """Consulta una fuente para una afirmación; ``None`` en sus hits si falla."""
    try:
        return index, search(query, max_results=EVIDENCE_RESULTS_PER_STATEMENT)
    except EvidenceRetrievalError:
        logger.warning("[Investigador] Fallo recuperando evidencia; se continúa")
        return index, None


def _search_all(claims: Sequence[Claim]) -> list[Claim]:
    """Busca cada afirmación en todas sus fuentes a la vez y anota lo que devolvieron."""
    # Fuentes de literatura: se consultan con la query enfocada en inglés.
    topic_sources = (search_europepmc, search_pubmed, search_openfda)

    # Cada par afirmación×fuente es I/O de red independiente: se lanzan todos en paralelo.
    tasks: list[tuple[int, str, Callable[..., list[dict]]]] = []
    per_claim_attempts = [0] * len(claims)
    for position, claim in enumerate(claims):
        for search in topic_sources:
            tasks.append((position, claim.search_query, search))
            per_claim_attempts[position] += 1
        if claim.drug_term:
            # CIMA (medicamentos) solo se consulta cuando la afirmación nombra un fármaco.
            tasks.append((position, claim.drug_term, search_cima))
            per_claim_attempts[position] += 1

    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        outcomes = list(pool.map(lambda task: _search_source(*task), tasks))

    # Reagrupa por afirmación: una falla solo si TODAS sus fuentes consultadas caen.
    per_claim_hits: list[list[dict]] = [[] for _ in claims]
    per_claim_failures = [0] * len(claims)
    for position, hits in outcomes:
        if hits is None:
            per_claim_failures[position] += 1
        else:
            per_claim_hits[position].extend(hits)

    return [
        with_hits(
            claim,
            (
                None
                if per_claim_failures[position] == per_claim_attempts[position]
                else per_claim_hits[position]
            ),
        )
        for position, claim in enumerate(claims)
    ]


def _judge_all(claims: Sequence[Claim], judge_prompt: str) -> list[Claim]:
    """Juzga a la vez la evidencia de cada afirmación; el fallo de una no bloquea a las demás."""
    judged = list(claims)
    pending = [p for p, claim in enumerate(claims) if claim.outcome == "unjudged"]
    if not pending:
        return judged
    with ThreadPoolExecutor(max_workers=len(pending)) as pool:
        answers = list(
            pool.map(
                lambda p: judge_stances(
                    judge_prompt,
                    claims[p].text_en or claims[p].search_query,
                    claims[p].evidence,
                ),
                pending,
            )
        )
    for position, answer in zip(pending, answers):
        judged[position] = with_stances(judged[position], answer)
    return judged


def gather_evidence(
    claims: Sequence[Claim], prompts: Prompts | None = None
) -> list[Claim]:
    """Busca y juzga la evidencia de las afirmaciones; las devuelve todas con el desenlace de su búsqueda."""
    # Una consulta inservible degradaría la búsqueda en silencio: se avisa.
    degenerate = sum(
        1 for claim in claims if claim.query and claim.search_query != claim.query
    )
    if degenerate:
        logger.warning(
            "[Investigador] %d consultas inservibles; se busca con el texto traducido",
            degenerate,
        )

    searchable = [p for p, claim in enumerate(claims) if claim.outcome == "unsearched"]
    positions = searchable[:EVIDENCE_MAX_STATEMENTS]
    if len(positions) < len(searchable):
        logger.warning(
            "[Investigador] %d afirmaciones sin buscar por la cota de %d",
            len(searchable) - len(positions),
            EVIDENCE_MAX_STATEMENTS,
        )
    if not positions:
        return list(claims)

    found = _search_all([claims[p] for p in positions])
    investigated = _judge_all(found, prompts.judge.text) if prompts else found

    for before, after in zip(found, investigated):
        # Bruto -> relevante por afirmación: separa fallo de búsqueda de filtrado del juez.
        if after.outcome != "unavailable":
            logger.info(
                "[Investigador] '%s': %d brutas -> %d relevantes (%s)",
                (after.text or after.search_query)[:60],
                len(before.evidence),
                len(after.evidence),
                Counter(str(item.stance) for item in after.evidence).most_common(),
            )

    # Se reensambla en el orden original de las afirmaciones.
    result = list(claims)
    for position, claim in zip(positions, investigated):
        result[position] = claim
    return result


def investigator(state: AgentState, prompts: Prompts | None = None) -> AgentState:
    """Recupera literatura biomédica relevante y cuenta a cuántas afirmaciones llega."""
    logger.info(
        "[Investigador] Buscando evidencia en Europe PMC, PubMed, openFDA y CIMA"
    )

    claims = gather_evidence(state.get("claims", []), prompts)
    search = evidence_search(claims)

    judge_failures = sum(1 for claim in claims if claim.outcome == "unjudged")
    if judge_failures:
        logger.warning(
            "[Investigador] %d afirmaciones con evidencia sin juzgar",
            judge_failures,
        )

    # El informe muestra un número acotado de fuentes y el veredicto solo cuenta esas.
    shown = keep_shown_sources(claims, EVIDENCE_MAX_SOURCES)
    sources = source_records(shown)

    logger.info(
        "[Investigador] %d fuentes para %d/%d afirmaciones%s",
        len(sources),
        search.covered,
        search.total,
        " (fuentes caídas)" if search.outage else "",
    )
    return {
        "claims": shown,
        "sources": sources,
        "evidence_search": search,
        "judge_failures": judge_failures,
    }
