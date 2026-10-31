"""Claims of an Analysis, the record the pipeline builds once and carries to the Verdict."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

Stance = Literal["supports", "contradicts", "inconclusive"]
# Judge answer per Source, a Stance or "unrelated" when it is about another topic.
JudgeStance = Literal["supports", "contradicts", "inconclusive", "unrelated"]
# How far a claim's Evidence search got.
ClaimOutcome = Literal[
    "unsearchable", "unsearched", "unavailable", "unjudged", "judged"
]

_SEARCHED: tuple[ClaimOutcome, ...] = ("unavailable", "unjudged", "judged")


@dataclass(frozen=True)
class EvidenceSearch:
    """Literature search counts that measure Evidence coverage."""

    # Claims with a usable query, the coverage denominator.
    total: int
    # The ones that got searched, since the cap leaves the rest out.
    searched: int
    # The ones the literature spoke to.
    covered: int
    # Every searched claim hit unreachable sources.
    outage: bool


@dataclass(frozen=True)
class Evidence:
    """A Source found for a claim, with the Stance the judge gave it."""

    title: str
    url: str
    source: str | None = None
    year: str | None = None
    # Only used for judging, the report does not store it.
    abstract: str | None = None
    # None until the judge has ruled.
    stance: Stance | None = None


@dataclass(frozen=True)
class Claim:
    """A medical claim of the content, with what its Evidence search needs and what it found."""

    # Position in the Analysis, the key that links Sources and Verdict to the claim.
    index: int
    # As extracted, in the content's language.
    text: str
    # Clinical English translation, empty if the translator dropped it.
    text_en: str = ""
    # Boolean query from the extractor, empty if it gave none.
    query: str = ""
    # Drug it names, or empty if it is not about a specific one.
    drug_term: str = ""
    # How far its search got, which before searching only depends on having a query.
    outcome: ClaimOutcome = "unsearched"
    # Found Sources the judge did not discard, in arrival order.
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        """Mark a still unsearched claim as unsearchable if it has no query, and vice versa."""
        if self.outcome in ("unsearched", "unsearchable"):
            outcome = "unsearched" if self.search_query else "unsearchable"
            object.__setattr__(self, "outcome", outcome)

    @property
    def search_query(self) -> str:
        """Search query, the extractor's if usable, otherwise the translation, or empty if neither."""
        if _usable(self.query):
            return self.query
        return self.text_en if self.text_en.strip() else ""


def with_hits(claim: Claim, hits: Sequence[dict] | None) -> Claim:
    """Record what the searched sources returned, ``None`` if they all failed, or their results."""
    if hits is None:
        return replace(claim, outcome="unavailable")
    evidence = _unique_evidence(hits)
    # Without Evidence there is nothing the judge could leave unjudged.
    return replace(
        claim, outcome="unjudged" if evidence else "judged", evidence=evidence
    )


def with_stances(claim: Claim, stances: Sequence[JudgeStance] | None) -> Claim:
    """Apply the judge's answer, one Stance per Source, leaving the Evidence unjudged without an answer."""
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
    """Count, by each claim's outcome, how many could be searched, were searched and were found by the literature."""
    searched = [claim for claim in claims if claim.outcome in _SEARCHED]
    return EvidenceSearch(
        total=sum(claim.outcome != "unsearchable" for claim in claims),
        searched=len(searched),
        covered=sum(bool(claim.evidence) for claim in searched),
        outage=bool(searched)
        and all(claim.outcome == "unavailable" for claim in searched),
    )


def keep_shown_sources(claims: Sequence[Claim], limit: int) -> list[Claim]:
    """Trim each claim's Evidence to the first ``limit`` distinct Sources, the ones the report shows."""
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
    """Sources as stored, one per URL, linked to each claim that cites it with its Stance."""
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
    """Serialisable result of an Evidence search, each searched claim with its judged Sources."""
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
    """One Source of the search result, without a Stance key if the judge did not rule."""
    hit = {
        "title": item.title,
        "url": item.url,
        "source": item.source,
        "year": item.year,
        "abstract": item.abstract,
    }
    return hit if item.stance is None else {**hit, "stance": item.stance}


def _unique_evidence(hits: Sequence[dict]) -> tuple[Evidence, ...]:
    """Turn the source results into Evidence, keeping the first of each URL."""
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
    """A query without alphanumeric characters retrieves nothing."""
    return any(char.isalnum() for char in query)
