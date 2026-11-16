"""Run the pipeline on a text, the way the worker and the evaluation harness reach a graph."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

from app.agents.errors import ainvoke_graph
from app.agents.state import AgentState, ClaimsState
from app.core.claim import Claim
from app.core.verdict import Verdict


@dataclass(frozen=True)
class Checked:
    """What the pipeline found in a text, with no Verdict when it holds no medical Claims."""

    verdict: Verdict | None
    claims: list[Claim]
    sources: list[dict]
    explanation: str
    judge_failures: int


async def check_text(
    graph: Any,
    text: str,
    on_stage: Callable[[str], Awaitable[None]] | None = None,
) -> Checked:
    """Run the full graph on a text, raising OllamaConnectionError or EvidenceUnavailable when our services could not check it."""
    final = cast(AgentState, await ainvoke_graph(graph, {"input_text": text}, on_stage))
    return Checked(
        verdict=final.get("verdict"),
        claims=final.get("claims") or [],
        sources=final.get("sources") or [],
        explanation=final.get("medical_explanation") or "",
        judge_failures=final.get("judge_failures") or 0,
    )


async def find_evidence(graph: Any, text: str) -> list[Claim]:
    """Run the evidence-only graph on a text and return its Claims with their Evidence, raising OllamaConnectionError when the LLM cannot be reached."""
    final = cast(ClaimsState, await ainvoke_graph(graph, {"input_text": text}))
    return final.get("claims") or []
