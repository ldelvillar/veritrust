"""Investigator agent that retrieves Evidence from Europe PMC, PubMed, openFDA and CIMA."""

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

# Caps that bound the pipeline's latency and cost against the evidence sources.
EVIDENCE_MAX_STATEMENTS = 8
EVIDENCE_RESULTS_PER_STATEMENT = 3
EVIDENCE_MAX_SOURCES = 12


def _search_source(
    index: int, query: str, search: Callable[..., list[dict]]
) -> tuple[int, list[dict] | None]:
    """Query one source for a claim, with ``None`` in its hits if it fails."""
    try:
        return index, search(query, max_results=EVIDENCE_RESULTS_PER_STATEMENT)
    except EvidenceRetrievalError:
        logger.warning("[Investigador] Fallo recuperando evidencia; se continúa")
        return index, None


def _search_all(claims: Sequence[Claim]) -> list[Claim]:
    """Search every claim in all its sources at once and record what they returned."""
    # Literature sources are queried with the focused English query.
    topic_sources = (search_europepmc, search_pubmed, search_openfda)

    # Each claim and source pair is independent network I/O, so they all run in parallel.
    tasks: list[tuple[int, str, Callable[..., list[dict]]]] = []
    per_claim_attempts = [0] * len(claims)
    for position, claim in enumerate(claims):
        for search in topic_sources:
            tasks.append((position, claim.search_query, search))
            per_claim_attempts[position] += 1
        if claim.drug_term:
            tasks.append((position, claim.drug_term, search_cima))
            per_claim_attempts[position] += 1

    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        outcomes = list(pool.map(lambda task: _search_source(*task), tasks))

    # Regroup by claim, which only fails when ALL its queried sources fail.
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
    """Judge every claim's Evidence at once, where one failure does not block the others."""
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
    """Search and judge the claims' Evidence and return them all with their search outcome."""
    # An unusable query would silently degrade the search, so it is logged.
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
        # Raw to relevant per claim, keeping a search failure apart from the judge's filtering.
        if after.outcome != "unavailable":
            logger.info(
                "[Investigador] '%s': %d brutas -> %d relevantes (%s)",
                (after.text or after.search_query)[:60],
                len(before.evidence),
                len(after.evidence),
                Counter(str(item.stance) for item in after.evidence).most_common(),
            )

    result = list(claims)
    for position, claim in zip(positions, investigated):
        result[position] = claim
    return result


def investigator(state: AgentState, prompts: Prompts | None = None) -> AgentState:
    """Retrieve relevant biomedical literature and count how many claims it reaches."""
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

    # The report shows a bounded number of Sources and the Verdict only counts those.
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
        "claims": claims,
        "shown_claims": shown,
        "sources": sources,
        "evidence_search": search,
        "judge_failures": judge_failures,
    }
