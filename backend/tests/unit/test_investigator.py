"""Tests of the investigator node with the evidence sources mocked."""

import threading
from types import SimpleNamespace

from app.agents import investigator as investigator_module
from app.agents.investigator import (
    EVIDENCE_MAX_STATEMENTS,
    gather_evidence,
    investigator,
)
from app.core.claim import Claim, EvidenceSearch
from app.utils.evidence import EvidenceRetrievalError

_PROMPTS = SimpleNamespace(judge=SimpleNamespace(text="judge-prompt"))
_NOTHING_SEARCHED = EvidenceSearch(total=0, searched=0, covered=0, outage=False)


def _claims(
    translations: list[str],
    *,
    originals: list[str] | None = None,
    queries: list[str] | None = None,
    drug_terms: list[str] | None = None,
) -> list[Claim]:
    """Already translated claims, as the translator leaves them in the state."""
    empty = [""] * len(translations)
    return [
        Claim(index=index, text=text, text_en=text_en, query=query, drug_term=drug)
        for index, (text, text_en, query, drug) in enumerate(
            zip(
                originals if originals is not None else empty,
                translations,
                queries or empty,
                drug_terms or empty,
                strict=True,
            )
        )
    ]


def _search(total: int, covered: int, *, outage: bool = False) -> EvidenceSearch:
    """Expected counts when the cap trims no claim."""
    return EvidenceSearch(total=total, searched=total, covered=covered, outage=outage)


def _patch_sources(monkeypatch, fake):
    """Replace the four sources (Europe PMC, PubMed, openFDA and CIMA) with the double."""
    monkeypatch.setattr(investigator_module, "search_europepmc", fake)
    monkeypatch.setattr(investigator_module, "search_pubmed", fake)
    monkeypatch.setattr(investigator_module, "search_openfda", fake)
    monkeypatch.setattr(investigator_module, "search_cima", fake)


def _patch_judge(monkeypatch, judge):
    """Replace the judge with a double that receives prompt, claim and Evidence."""
    monkeypatch.setattr(investigator_module, "judge_stances", judge)


def _judge_all(stance):
    """Judge that gives every candidate Source the same Stance."""
    return lambda prompt, claim, evidence: (stance,) * len(evidence)


def test_returns_empty_without_claims():
    update = investigator({"claims": []})
    assert update == {
        "claims": [],
        "shown_claims": [],
        "sources": [],
        "evidence_search": _NOTHING_SEARCHED,
        "judge_failures": 0,
    }


def test_collects_sources_and_full_coverage(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": f"hit for {query}", "url": f"https://x/{query}"}]

    _patch_sources(monkeypatch, fake_search)

    update = investigator({"claims": _claims(["A", "B"], originals=["a", "b"])})

    assert set(update.keys()) == {
        "claims",
        "shown_claims",
        "sources",
        "evidence_search",
        "judge_failures",
    }
    assert update["evidence_search"] == _search(2, covered=2)
    # The four sources return the same URL per claim, deduplicated to one.
    assert len(update["sources"]) == 2
    assert update["sources"][0]["statements"] == [
        {"claim_index": 0, "text": "a", "stance": None}
    ]


def test_merges_distinct_hits_from_both_sources(monkeypatch):
    def fake_europepmc(query, *, max_results):
        return [{"title": "pmc", "url": "https://pmc/1"}]

    def fake_pubmed(query, *, max_results):
        return [{"title": "pubmed", "url": "https://pubmed/1"}]

    def fake_empty(query, *, max_results):
        return []

    monkeypatch.setattr(investigator_module, "search_europepmc", fake_europepmc)
    monkeypatch.setattr(investigator_module, "search_pubmed", fake_pubmed)
    monkeypatch.setattr(investigator_module, "search_openfda", fake_empty)
    monkeypatch.setattr(investigator_module, "search_cima", fake_empty)

    update = investigator({"claims": _claims(["A"], originals=["a"])})

    # Different results from each source are both kept for the same claim.
    assert update["evidence_search"] == _search(1, covered=1)
    assert {source["url"] for source in update["sources"]} == {
        "https://pmc/1",
        "https://pubmed/1",
    }


def test_cap_drops_extra_statements_and_counts_them_uncovered(monkeypatch):
    queried: set[str] = set()

    def fake_search(query, *, max_results):
        queried.add(query)
        return [{"title": query, "url": f"https://x/{query}"}]

    _patch_sources(monkeypatch, fake_search)

    total = EVIDENCE_MAX_STATEMENTS + 2
    statements = [f"S{i}" for i in range(total)]
    update = investigator({"claims": _claims(statements)})

    # Only the first N claims are searched, and the trimmed ones count as uncovered.
    assert queried == set(statements[:EVIDENCE_MAX_STATEMENTS])
    assert update["evidence_search"] == EvidenceSearch(
        total=total,
        searched=EVIDENCE_MAX_STATEMENTS,
        covered=EVIDENCE_MAX_STATEMENTS,
        outage=False,
    )
    assert len(update["sources"]) == EVIDENCE_MAX_STATEMENTS


def test_total_outage_is_reported_as_an_outage(monkeypatch):
    def fake_search(query, *, max_results):
        raise EvidenceRetrievalError("down")

    _patch_sources(monkeypatch, fake_search)

    update = investigator({"claims": _claims(["A", "B"])})

    # Total service outage, reported as an outage and not as missing literature.
    assert update["sources"] == []
    assert update["evidence_search"] == _search(2, covered=0, outage=True)


def test_one_source_down_still_uses_the_other(monkeypatch):
    def fake_europepmc(query, *, max_results):
        raise EvidenceRetrievalError("pmc down")

    def fake_pubmed(query, *, max_results):
        return [{"title": "pubmed", "url": "https://pubmed/1"}]

    def fake_empty(query, *, max_results):
        return []

    monkeypatch.setattr(investigator_module, "search_europepmc", fake_europepmc)
    monkeypatch.setattr(investigator_module, "search_pubmed", fake_pubmed)
    monkeypatch.setattr(investigator_module, "search_openfda", fake_empty)
    monkeypatch.setattr(investigator_module, "search_cima", fake_empty)

    update = investigator({"claims": _claims(["A"])})

    # One down source does not invalidate the claim, since the others do bring Evidence.
    assert update["evidence_search"] == _search(1, covered=1)
    assert [source["url"] for source in update["sources"]] == ["https://pubmed/1"]


def test_blank_translations_skip_lookups(monkeypatch):
    called = False

    def fake_search(query, *, max_results):
        nonlocal called
        called = True
        return []

    _patch_sources(monkeypatch, fake_search)

    # Blank (padding) translations leave nothing to query.
    claims = gather_evidence(_claims(["", "  "]))

    assert [claim.outcome for claim in claims] == ["unsearchable", "unsearchable"]
    assert called is False


def test_runs_lookups_concurrently(monkeypatch):
    # The barrier only releases if all 9 searches (3 claims by 3 literature sources, no CIMA without a drug) overlap, so a sequential run would time out.
    barrier = threading.Barrier(9, timeout=5)

    def fake_search(query, *, max_results):
        barrier.wait()
        return [{"title": query, "url": f"https://x/{query}"}]

    _patch_sources(monkeypatch, fake_search)

    update = investigator({"claims": _claims(["A", "B", "C"])})

    assert update["evidence_search"] == _search(3, covered=3)
    assert len(update["sources"]) == 3


def test_cima_queried_with_drug_term_not_english_query(monkeypatch):
    topic_queried: list[str] = []
    cima_queried: list[str] = []

    def fake_topic(query, *, max_results):
        topic_queried.append(query)
        return []

    def fake_cima(query, *, max_results):
        cima_queried.append(query)
        return [{"title": "ficha", "url": "https://cima/1"}]

    monkeypatch.setattr(investigator_module, "search_europepmc", fake_topic)
    monkeypatch.setattr(investigator_module, "search_pubmed", fake_topic)
    monkeypatch.setattr(investigator_module, "search_openfda", fake_topic)
    monkeypatch.setattr(investigator_module, "search_cima", fake_cima)

    update = investigator(
        {
            "claims": _claims(
                ["ibuprofen cures cancer"],
                originals=["el ibuprofeno cura el cáncer"],
                queries=['"ibuprofen" AND "cancer"'],
                drug_terms=["ibuprofeno"],
            )
        }
    )

    # CIMA uses the Spanish term and the literature the focused English query.
    assert cima_queried == ["ibuprofeno"]
    assert set(topic_queried) == {'"ibuprofen" AND "cancer"'}
    assert [source["url"] for source in update["sources"]] == ["https://cima/1"]


def test_cima_skipped_when_no_drug_term(monkeypatch):
    cima_called = False

    def fake_topic(query, *, max_results):
        return []

    def fake_cima(query, *, max_results):
        nonlocal cima_called
        cima_called = True
        return []

    monkeypatch.setattr(investigator_module, "search_europepmc", fake_topic)
    monkeypatch.setattr(investigator_module, "search_pubmed", fake_topic)
    monkeypatch.setattr(investigator_module, "search_openfda", fake_topic)
    monkeypatch.setattr(investigator_module, "search_cima", fake_cima)

    investigator(
        {
            "claims": _claims(
                ["a diet claim"],
                originals=["una dieta sana"],
                queries=['"diet"'],
                drug_terms=[""],
            )
        }
    )

    # Without a named drug, CIMA is not queried.
    assert cima_called is False


def test_judge_receives_the_english_claim_or_its_query(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": query, "url": f"https://x/{query}"}]

    _patch_sources(monkeypatch, fake_search)
    judged: list[str] = []

    def fake_judge(prompt, claim, evidence):
        judged.append(claim)
        return ("supports",) * len(evidence)

    _patch_judge(monkeypatch, fake_judge)

    gather_evidence(
        _claims(["A-en", ""], originals=["a", "b"], queries=['"qa"', '"qb"']),
        _PROMPTS,
    )

    # Without a translation the judge gets the query as a fallback.
    assert sorted(judged) == ['"qb"', "A-en"]


def test_judge_runs_concurrently(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": query, "url": f"https://x/{query}", "abstract": "abs"}]

    _patch_sources(monkeypatch, fake_search)

    # The barrier only releases if the 3 judgments overlap, so a sequential run would time out.
    barrier = threading.Barrier(3, timeout=5)

    def fake_judge(prompt, claim, evidence):
        barrier.wait()
        return ("supports",) * len(evidence)

    _patch_judge(monkeypatch, fake_judge)

    update = investigator(
        {"claims": _claims(["A", "B", "C"], originals=["a", "b", "c"])}, _PROMPTS
    )

    assert update["evidence_search"] == _search(3, covered=3)
    assert len(update["sources"]) == 3


def test_parallel_judge_isolates_one_failure(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": query, "url": f"https://x/{query}", "abstract": "abs"}]

    _patch_sources(monkeypatch, fake_search)

    # The judge fails for a single claim and in parallel must not drag the rest down.
    def fake_judge(prompt, claim, evidence):
        return None if claim == "B-en" else ("supports",) * len(evidence)

    _patch_judge(monkeypatch, fake_judge)

    update = investigator(
        {"claims": _claims(["A-en", "B-en"], originals=["a", "b"])}, _PROMPTS
    )

    # The claim whose judge failed keeps its Evidence (fails open) and the healthy one is judged normally, both counting for coverage.
    assert update["evidence_search"] == _search(2, covered=2)
    assert [claim.outcome for claim in update["claims"]] == ["judged", "unjudged"]
    by_url = {source["url"]: source for source in update["sources"]}
    assert by_url["https://x/A-en"]["statements"] == [
        {"claim_index": 0, "text": "a", "stance": "supports"}
    ]
    assert by_url["https://x/B-en"]["statements"] == [
        {"claim_index": 1, "text": "b", "stance": None}
    ]


def test_reports_judge_failures_when_sources_go_unjudged(monkeypatch):
    """The judge fails open, so the Sources without a Stance must be counted."""

    def fake_search(query, max_results):
        return [{"url": "u1", "title": "T1", "abstract": "A1"}]

    _patch_sources(monkeypatch, fake_search)
    _patch_judge(monkeypatch, lambda prompt, claim, evidence: None)

    update = investigator(
        {"claims": _claims(["Claim in English"], originals=["Afirmación"])}, _PROMPTS
    )

    assert update["judge_failures"] == 1


def test_no_judge_failures_when_every_source_is_judged(monkeypatch):
    def fake_search(query, max_results):
        return [{"url": "u1", "title": "T1", "abstract": "A1"}]

    _patch_sources(monkeypatch, fake_search)
    _patch_judge(monkeypatch, _judge_all("supports"))

    update = investigator(
        {"claims": _claims(["Claim in English"], originals=["Afirmación"])}, _PROMPTS
    )

    assert update["judge_failures"] == 0


def test_gather_evidence_marks_unjudged_and_unavailable_claims(monkeypatch):
    def fake_search(query, *, max_results):
        if query == "B-en":
            raise EvidenceRetrievalError("down")
        return [{"title": "t", "url": "https://x/a"}]

    _patch_sources(monkeypatch, fake_search)
    _patch_judge(monkeypatch, lambda prompt, claim, evidence: None)

    claims = gather_evidence(_claims(["A-en", "B-en"], originals=["a", "b"]), _PROMPTS)

    # Every source failed for the second claim, so no Evidence is available.
    assert [claim.outcome for claim in claims] == ["unjudged", "unavailable"]
    assert [item.url for item in claims[0].evidence] == ["https://x/a"]
    assert claims[1].evidence == ()


def test_gather_evidence_leaves_claims_beyond_the_cap_unsearched(monkeypatch):
    _patch_sources(monkeypatch, lambda query, *, max_results: [])

    statements = [f"S{i}" for i in range(EVIDENCE_MAX_STATEMENTS + 2)]
    claims = gather_evidence(_claims(statements))

    # With no Sources to judge, the searched claim counts as judged.
    assert [claim.outcome for claim in claims] == [
        "judged"
    ] * EVIDENCE_MAX_STATEMENTS + [
        "unsearched",
        "unsearched",
    ]


def test_gather_evidence_is_empty_without_claims():
    assert gather_evidence([]) == []
