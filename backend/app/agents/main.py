"""
Este módulo construye el grafo de LangGraph, define los nodos (agentes) y ejecuta
el flujo completo para verificar noticias falsas en el ámbito de la salud.
"""

import sys
from pathlib import Path
from typing import List, TypedDict

# Asegurar que al ejecutar este archivo como script, se use el código local del repositorio.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.extractor import extractor
from app.agents.health_expert import health_expert
from app.agents.translator import translator


class AgentState(TypedDict):
    """
    Define el diccionario de estado que utiliza el grafo.
    Cada nodo leerá y actualizará estas variables.
    """

    input_text: str
    extracted_statements: List[str]
    translated_statements: List[str]
    label: str
    confidence: float
    medical_explanation: str


def create_graph(prompts) -> CompiledStateGraph:
    """Instancia y configura el flujo de trabajo multiagente."""
    # Inicializar el grafo con el estado definido
    workflow = StateGraph(AgentState)

    # Añadir los nodos (los agentes)
    workflow.add_node("extractor", lambda state: extractor(state, prompts))
    workflow.add_node("translator", lambda state: translator(state, prompts))
    workflow.add_node("health_expert", lambda state: health_expert(state, prompts))

    # Definir el flujo lógico (las aristas del grafo)
    workflow.add_edge(START, "extractor")
    workflow.add_edge("extractor", "translator")
    workflow.add_edge("translator", "health_expert")
    workflow.add_edge("health_expert", END)

    # Compilar el grafo
    app = workflow.compile()

    return app
