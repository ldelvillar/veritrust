"""Run the pipeline on a text, the one way a graph is reached from outside the agents."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

from app.agents.errors import ainvoke_graph
from app.agents.sanitize import neutralize_delimiters
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
    """Run the full graph on a text, raising AgentError when our services could not check it."""
    initial: dict[str, object] = {
        "input_text": neutralize_delimiters(text),
        "claims": [],
        "sources": [],
        "medical_explanation": "",
    }
    final = cast(AgentState, await ainvoke_graph(graph, initial, on_stage))
    return Checked(
        verdict=final.get("verdict"),
        claims=final.get("claims") or [],
        sources=final.get("sources") or [],
        explanation=final.get("medical_explanation") or "",
        judge_failures=final.get("judge_failures") or 0,
    )


async def find_evidence(graph: Any, text: str) -> list[Claim]:
    """Run the evidence-only graph on a text and return its Claims with their Evidence, raising AgentError like check_text."""
    initial: dict[str, object] = {
        "input_text": neutralize_delimiters(text),
        "claims": [],
    }
    final = cast(ClaimsState, await ainvoke_graph(graph, initial))
    return final.get("claims") or []
