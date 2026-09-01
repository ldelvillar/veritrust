"""
Este módulo construye el grafo de LangGraph, define los nodos (agentes) y ejecuta
el flujo completo para verificar noticias falsas en el ámbito de la salud.
"""

import logging
import time
from collections.abc import Callable
from typing import List, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.extractor import extractor
from app.agents.health_expert import health_expert
from app.agents.investigator import investigator
from app.agents.translator import translator

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """
    Define el diccionario de estado que utiliza el grafo.
    Cada nodo leerá y actualizará estas variables.
    """

    input_text: str
    extracted_statements: List[str]
    search_queries: List[str]
    drug_terms: List[str]
    translated_statements: List[str]
    sources: List[dict]
    evidence_coverage: float
    label: str
    confidence: float
    medical_explanation: str
    claims: List[dict]


def _timed_run(name: str, fn: Callable[[], dict]) -> dict:
    """Ejecuta un nodo del grafo registrando cuánto tarda en completarse."""
    start = time.perf_counter()
    try:
        return fn()
    finally:
        logger.info("[%s] completado en %.2fs", name, time.perf_counter() - start)


# Orden canónico de los nodos del grafo; el worker lo usa para reportar la etapa activa.
PIPELINE_STAGES: tuple[str, ...] = (
    "extractor",
    "translator",
    "investigator",
    "health_expert",
)


def create_graph(prompts) -> CompiledStateGraph:
    """Instancia y configura el flujo de trabajo multiagente."""
    # Inicializar el grafo con el estado definido
    workflow = StateGraph(AgentState)

    # Añadir los nodos (los agentes), instrumentados con su duración
    workflow.add_node(
        "extractor",
        lambda state: _timed_run("extractor", lambda: extractor(state, prompts)),
    )
    workflow.add_node(
        "translator",
        lambda state: _timed_run("translator", lambda: translator(state, prompts)),
    )
    workflow.add_node(
        "investigator",
        lambda state: _timed_run("investigator", lambda: investigator(state, prompts)),
    )
    workflow.add_node(
        "health_expert",
        lambda state: _timed_run(
            "health_expert", lambda: health_expert(state, prompts)
        ),
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
