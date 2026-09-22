"""
Este módulo construye el grafo de LangGraph, define los nodos (agentes) y ejecuta
el flujo completo para verificar noticias falsas en el ámbito de la salud.
"""

import logging
import time
from collections.abc import Callable
from typing import Protocol, TypeVar

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.extractor import extractor
from app.agents.health_expert import health_expert
from app.agents.investigator import gather_evidence, investigator
from app.agents.state import AgentState, ClaimsState, EvidenceState
from app.agents.translator import translator
from app.prompts.agents import Prompts

logger = logging.getLogger(__name__)

StateT = TypeVar("StateT", bound=ClaimsState)


class _Node(Protocol[StateT]):
    """Nodo del grafo con la firma que exige LangGraph en add_node."""

    def __call__(self, state: StateT) -> StateT: ...


def _timed_node(
    name: str, node: Callable[[StateT, Prompts], StateT], prompts: Prompts
) -> _Node[StateT]:
    """Envuelve un nodo del grafo registrando cuánto tarda en completarse."""

    def run(state: StateT) -> StateT:
        start = time.perf_counter()
        try:
            return node(state, prompts)
        finally:
            logger.info("[%s] completado en %.2fs", name, time.perf_counter() - start)

    return run


# Orden canónico de los nodos del grafo; el worker lo usa para reportar la etapa activa.
PIPELINE_STAGES: tuple[str, ...] = (
    "extractor",
    "translator",
    "investigator",
    "health_expert",
)


def create_graph(prompts: Prompts) -> CompiledStateGraph:
    """Instancia y configura el flujo de trabajo multiagente."""
    # Inicializar el grafo con el estado definido
    workflow = StateGraph(AgentState)

    # Añadir los nodos (los agentes), instrumentados con su duración
    workflow.add_node("extractor", _timed_node("extractor", extractor, prompts))
    workflow.add_node("translator", _timed_node("translator", translator, prompts))
    workflow.add_node(
        "investigator", _timed_node("investigator", investigator, prompts)
    )
    workflow.add_node(
        "health_expert", _timed_node("health_expert", health_expert, prompts)
    )

    # Definir el flujo lógico (las aristas del grafo)
    workflow.add_edge(START, "extractor")
    workflow.add_edge("extractor", "translator")
    workflow.add_edge("translator", "investigator")
    workflow.add_edge("investigator", "health_expert")
    workflow.add_edge("health_expert", END)

    # Compilar el grafo
    app = workflow.compile()

    return app


def _evidence_node(state: EvidenceState, prompts: Prompts) -> EvidenceState:
    """Nodo del grafo de evidencia: busca y juzga las fuentes de cada afirmación."""
    total, claims = gather_evidence(state, prompts)
    return {"valid_claims": total, "claim_evidence": claims}


def create_evidence_graph(prompts: Prompts) -> CompiledStateGraph:
    """Instancia el flujo de solo evidencia, sin veredicto ni explicación."""
    workflow = StateGraph(EvidenceState)

    workflow.add_node("extractor", _timed_node("extractor", extractor, prompts))
    workflow.add_node("translator", _timed_node("translator", translator, prompts))
    workflow.add_node("evidence", _timed_node("evidence", _evidence_node, prompts))

    workflow.add_edge(START, "extractor")
    workflow.add_edge("extractor", "translator")
    workflow.add_edge("translator", "evidence")
    workflow.add_edge("evidence", END)

    return workflow.compile()
