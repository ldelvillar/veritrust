"""Tests of running the pipeline on a text, the way the worker and the evaluation harness reach a graph."""

from app.agents.pipeline import Checked, check_text, find_evidence
from app.core.claim import Claim
from app.core.verdict import ClaimVerdict, Verdict
from tests.support.graph import graph_ending_in

VERDICT = Verdict(
    kind="fake",
    confidence=0.92,
    falsehood=0.92,
    evidence_coverage=0.5,
    claims=(ClaimVerdict(text="La lejía cura", kind="fake", confidence=0.9),),
)


async def test_check_text_returns_what_the_graph_found() -> None:
    claims = [Claim(index=0, text="La lejía cura")]
    sources = [{"title": "Estudio", "url": "https://doi.org/10.1/x"}]
    graph = graph_ending_in(
        {
            "verdict": VERDICT,
            "claims": claims,
            "sources": sources,
            "medical_explanation": "No hay evidencia clínica sólida.",
            "judge_failures": 1,
        }
    )

    checked = await check_text(graph, "La lejía cura el COVID")

    assert graph.seen == [{"input_text": "La lejía cura el COVID"}]
    assert checked == Checked(
        verdict=VERDICT,
        claims=claims,
        sources=sources,
        explanation="No hay evidencia clínica sólida.",
        judge_failures=1,
    )


async def test_check_text_of_a_graph_that_found_nothing_has_no_verdict() -> None:
    checked = await check_text(graph_ending_in({}), "Hola")

    assert checked == Checked(
        verdict=None, claims=[], sources=[], explanation="", judge_failures=0
    )


async def test_find_evidence_returns_the_claims_the_graph_found() -> None:
    claims = [Claim(index=0, text="A", query='"a"')]
    graph = graph_ending_in({"claims": claims})

    found = await find_evidence(graph, "La vitamina C cura")

    assert graph.seen == [{"input_text": "La vitamina C cura"}]
    assert found == claims
