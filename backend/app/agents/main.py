"""Build the LangGraph graph and its agent nodes that fact-check health misinformation."""

import logging
import time
from collections.abc import Callable
from dataclasses import fields
from typing import Protocol, TypeVar

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.extractor import extractor
from app.agents.health_expert import health_expert
from app.agents.investigator import gather_evidence, investigator
from app.agents.state import AgentState, ClaimsState
from app.agents.translator import translator
from app.core.config import get_settings
from app.prompts.agents import Prompts
from app.utils.llm import configured_models

logger = logging.getLogger(__name__)

StateT = TypeVar("StateT", bound=ClaimsState)


class _Node(Protocol[StateT]):
    """Graph node with the signature LangGraph's add_node requires."""

    def __call__(self, state: StateT) -> StateT: ...


def _timed_node(
    name: str, node: Callable[[StateT, Prompts], StateT], prompts: Prompts
) -> _Node[StateT]:
    """Wrap a graph node and log how long it takes to finish."""

    def run(state: StateT) -> StateT:
        start = time.perf_counter()
        try:
            return node(state, prompts)
        finally:
            logger.info("[%s] completado en %.2fs", name, time.perf_counter() - start)

    return run


# Canonical order of the graph's nodes, which the worker uses to report the active stage.
PIPELINE_STAGES: tuple[str, ...] = (
    "extractor",
    "translator",
    "investigator",
    "health_expert",
)


def describe_pipeline(prompts: Prompts) -> dict:
    """Identify the configuration that produces a Verdict, from provider, per-role models and prompt versions."""
    return {
        "provider": get_settings().llm_provider_name(),
        "models": configured_models(),
        "prompts": {f.name: getattr(prompts, f.name).version for f in fields(prompts)},
    }


def create_graph(prompts: Prompts) -> CompiledStateGraph:
    """Build and wire the multi-agent workflow."""
    workflow = StateGraph(AgentState)

    workflow.add_node("extractor", _timed_node("extractor", extractor, prompts))
    workflow.add_node("translator", _timed_node("translator", translator, prompts))
    workflow.add_node(
        "investigator", _timed_node("investigator", investigator, prompts)
    )
    workflow.add_node(
        "health_expert", _timed_node("health_expert", health_expert, prompts)
    )

    workflow.add_edge(START, "extractor")
    workflow.add_edge("extractor", "translator")
    workflow.add_edge("translator", "investigator")
    workflow.add_edge("investigator", "health_expert")
    workflow.add_edge("health_expert", END)

    app = workflow.compile()

    return app


def _evidence_node(state: ClaimsState, prompts: Prompts) -> ClaimsState:
    """Evidence graph node that searches and judges each claim's Sources."""
    return {"claims": gather_evidence(state.get("claims", []), prompts)}


def create_evidence_graph(prompts: Prompts) -> CompiledStateGraph:
    """Build the evidence-only workflow, with no Verdict or explanation."""
    workflow = StateGraph(ClaimsState)

    workflow.add_node("extractor", _timed_node("extractor", extractor, prompts))
    workflow.add_node("translator", _timed_node("translator", translator, prompts))
    workflow.add_node("evidence", _timed_node("evidence", _evidence_node, prompts))

    workflow.add_edge(START, "extractor")
    workflow.add_edge("extractor", "translator")
    workflow.add_edge("translator", "evidence")
    workflow.add_edge("evidence", END)

    return workflow.compile()
