"""Afirmaciones de un análisis: el registro que el pipeline construye una vez y lleva hasta el veredicto."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

# Postura de una fuente sobre una afirmación.
Stance = Literal["supports", "contradicts", "inconclusive"]
# Respuesta del juez por fuente: una postura, o "unrelated" si trata de otro tema.
JudgeStance = Literal["supports", "contradicts", "inconclusive", "unrelated"]
# Hasta dónde llegó la búsqueda de evidencia de una afirmación.
ClaimOutcome = Literal[
    "unsearchable", "unsearched", "unavailable", "unjudged", "judged"
]

# Desenlaces de una afirmación que llegó a buscarse.
_SEARCHED: tuple[ClaimOutcome, ...] = ("unavailable", "unjudged", "judged")


@dataclass(frozen=True)
class EvidenceSearch:
    """Recuento de la búsqueda de literatura con el que se mide la cobertura de evidencia."""

    # Afirmaciones con una consulta utilizable: el denominador de la cobertura.
    total: int
    # Las que se llegaron a buscar; la cota deja fuera el resto.
    searched: int
    # Las que la literatura llegó a tratar.
    covered: int
    # Todas las buscadas toparon con fuentes inalcanzables.
    outage: bool


@dataclass(frozen=True)
class Evidence:
    """Una fuente hallada para una afirmación, con la postura que le dio el juez."""

    title: str
    url: str
    source: str | None = None
    year: str | None = None
    # Solo sirve para juzgar; el informe no lo guarda.
    abstract: str | None = None
    # None mientras el juez no se haya pronunciado.
    stance: Stance | None = None


@dataclass(frozen=True)
class Claim:
    """Una afirmación médica del contenido, con lo necesario para buscar su evidencia y lo que se halló."""

    # Posición en el análisis: la clave con la que fuentes y veredicto enlazan la afirmación.
    index: int
    # Tal como se extrajo, en el idioma del contenido.
    text: str
    # Traducción al inglés clínico; vacía si el traductor la omitió.
    text_en: str = ""
    # Consulta booleana del extractor; vacía si no la dio.
    query: str = ""
    # Fármaco que nombra, o vacío si no trata de uno concreto.
    drug_term: str = ""
    # Hasta dónde llegó su búsqueda; antes de buscarla solo depende de si hay consulta.
    outcome: ClaimOutcome = "unsearched"
    # Fuentes halladas que el juez no descartó, en el orden en que llegaron.
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        """Deja una afirmación aún sin buscar como no buscable si no tiene consulta, y viceversa."""
        if self.outcome in ("unsearched", "unsearchable"):
            outcome = "unsearched" if self.search_query else "unsearchable"
            object.__setattr__(self, "outcome", outcome)

    @property
    def search_query(self) -> str:
        """Consulta de búsqueda: la del extractor si sirve, si no la traducción, o vacía si no hay ninguna."""
        if _usable(self.query):
            return self.query
        return self.text_en if self.text_en.strip() else ""


def with_hits(claim: Claim, hits: Sequence[dict] | None) -> Claim:
    """Anota lo que devolvieron las fuentes buscadas: ``None`` si cayeron todas, o sus resultados."""
    if hits is None:
        return replace(claim, outcome="unavailable")
    evidence = _unique_evidence(hits)
    # Sin evidencia no hay nada que el juez pueda dejar sin juzgar.
    return replace(
        claim, outcome="unjudged" if evidence else "judged", evidence=evidence
    )


def with_stances(claim: Claim, stances: Sequence[JudgeStance] | None) -> Claim:
    """Aplica la respuesta del juez, una postura por fuente; sin respuesta la evidencia queda sin juzgar."""
    if stances is None:
        return claim
    return replace(
        claim,
        outcome="judged",
        evidence=tuple(
            replace(item, stance=stance)
            for item, stance in zip(claim.evidence, stances, strict=True)
            if stance != "unrelated"
        ),
    )


def evidence_search(claims: Sequence[Claim]) -> EvidenceSearch:
    """Cuenta, por el desenlace de cada afirmación, cuántas se podían buscar, se buscaron y halló la literatura."""
    searched = [claim for claim in claims if claim.outcome in _SEARCHED]
    return EvidenceSearch(
        total=sum(claim.outcome != "unsearchable" for claim in claims),
        searched=len(searched),
        covered=sum(bool(claim.evidence) for claim in searched),
        outage=bool(searched)
        and all(claim.outcome == "unavailable" for claim in searched),
    )


def keep_shown_sources(claims: Sequence[Claim], limit: int) -> list[Claim]:
    """Recorta la evidencia de cada afirmación a las ``limit`` primeras fuentes distintas, las que muestra el informe."""
    shown: set[str] = set()
    for item in (item for claim in claims for item in claim.evidence):
        if len(shown) == limit:
            break
        shown.add(item.url)
    return [
        replace(
            claim, evidence=tuple(item for item in claim.evidence if item.url in shown)
        )
        for claim in claims
    ]


def source_records(claims: Sequence[Claim]) -> list[dict]:
    """Fuentes tal y como se guardan: una por URL, enlazada a cada afirmación que la cita con su postura."""
    by_url: dict[str, dict] = {}
    for claim in claims:
        for item in claim.evidence:
            record = by_url.setdefault(
                item.url,
                {
                    "title": item.title,
                    "url": item.url,
                    "source": item.source,
                    "year": item.year,
                    "statements": [],
                },
            )
            if all(link["claim_index"] != claim.index for link in record["statements"]):
                record["statements"].append(
                    {
                        "claim_index": claim.index,
                        "text": claim.text,
                        "stance": item.stance,
                    }
                )
    return list(by_url.values())


def evidence_report(claims: Sequence[Claim]) -> dict:
    """Resultado serializable de una búsqueda de evidencia: cada afirmación buscada con sus fuentes juzgadas."""
    return {
        "claims": [
            {
                "claim_index": claim.index,
                "query": claim.search_query,
                "claim": claim.text_en,
                "original": claim.text,
                "hits": (
                    None
                    if claim.outcome == "unavailable"
                    else [_hit(item) for item in claim.evidence]
                ),
                "judged": claim.outcome == "judged",
            }
            for claim in claims
            if claim.outcome in _SEARCHED
        ],
        "unsearched_claims": sum(claim.outcome == "unsearched" for claim in claims),
    }


def _hit(item: Evidence) -> dict:
    """Una fuente del resultado de búsqueda; sin clave de postura si el juez no se pronunció."""
    hit = {
        "title": item.title,
        "url": item.url,
        "source": item.source,
        "year": item.year,
        "abstract": item.abstract,
    }
    return hit if item.stance is None else {**hit, "stance": item.stance}


def _unique_evidence(hits: Sequence[dict]) -> tuple[Evidence, ...]:
    """Convierte los resultados de las fuentes en evidencia, conservando el primero de cada URL."""
    seen: set[str] = set()
    unique: list[Evidence] = []
    for hit in hits:
        url = hit["url"]
        if url in seen:
            continue
        seen.add(url)
        unique.append(
            Evidence(
                title=hit["title"],
                url=url,
                source=hit.get("source"),
                year=hit.get("year"),
                abstract=hit.get("abstract"),
            )
        )
    return tuple(unique)


def _usable(query: str) -> bool:
    """Una consulta sin caracteres alfanuméricos no recupera nada."""
    return any(char.isalnum() for char in query)
