"""Tests of the live Literature sources the worker and the evaluation search."""

from app.agents.literature_sources import live_literature_sources
from app.utils import cima, europepmc, openfda, pubmed


def test_each_live_literature_source_searches_its_own_database():
    live = live_literature_sources()

    # A swapped pair would send CIMA the English query, or openFDA the Spanish drug term.
    assert live.europepmc is europepmc.search_evidence
    assert live.pubmed is pubmed.search_evidence
    assert live.openfda is openfda.search_evidence
    assert live.cima is cima.search_evidence
