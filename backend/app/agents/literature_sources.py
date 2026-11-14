"""The Literature sources the pipeline searches, passed in where a graph is built."""

from dataclasses import dataclass
from typing import Protocol

from app.utils.cima import search_evidence as search_cima
from app.utils.europepmc import search_evidence as search_europepmc
from app.utils.openfda import search_evidence as search_openfda
from app.utils.pubmed import search_evidence as search_pubmed


class Search(Protocol):
    """Search one Literature source, raising EvidenceRetrievalError when it cannot be reached."""

    def __call__(self, query: str, *, max_results: int) -> list[dict]: ...


@dataclass(frozen=True)
class LiteratureSources:
    """The four Literature sources, where CIMA takes the Spanish drug term and the others the English query."""

    europepmc: Search
    pubmed: Search
    openfda: Search
    cima: Search


def live_literature_sources() -> LiteratureSources:
    """Return the Literature sources that query the real services."""
    return LiteratureSources(
        europepmc=search_europepmc,
        pubmed=search_pubmed,
        openfda=search_openfda,
        cima=search_cima,
    )
