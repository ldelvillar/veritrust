"""
Este módulo construye el grafo de LangGraph, define los nodos (agentes) y ejecuta
el flujo completo para verificar noticias falsas en el ámbito de la salud.
"""

import sys
from typing import TypedDict, List

from pathlib import Path

# Asegurar que al ejecutar este archivo como script, se use el código local del repositorio.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langgraph.graph import StateGraph, START, END
from app.agents.extractor import extractor
from app.agents.translator import translator
from app.agents.health_expert import health_expert
from app.utils.start_ollama import start_ollama


class AgentState(TypedDict):
    """
    Define el diccionario de estado que utiliza el grafo.
    Cada nodo leerá y actualizará estas variables.
    """

    input_text: str
    extracted_statements: List[str]
    translated_statements: List[str]
    label: str
    confidence: str
    medical_explanation: str


def create_graph() -> StateGraph[AgentState]:
    """Instancia y configura el flujo de trabajo multiagente."""
    # Inicializar el grafo con el estado definido
    workflow = StateGraph(AgentState)

    # Añadir los nodos (los agentes)
    workflow.add_node("extractor", extractor)
    workflow.add_node("translator", translator)
    workflow.add_node("health_expert", health_expert)

    # Definir el flujo lógico (las aristas del grafo)
    workflow.add_edge(START, "extractor")
    workflow.add_edge("extractor", "translator")
    workflow.add_edge("translator", "health_expert")
    workflow.add_edge("health_expert", END)

    # Compilar el grafo
    app = workflow.compile()

    return app


if __name__ == "__main__":
    INPUT_TEXT = (
        "He leído en un foro que el consumo masivo de vitamina C previene cualquier "
        "tipo de infección viral."
    )

    # Arrancar Ollama
    start_ollama()

    # Inicializar el sistema
    verification_system = create_graph()

    # Crear el estado inicial
    initial_state = {
        "input_text": INPUT_TEXT,
        "extracted_statements": [],
        "translated_statements": [],
        "label": "",
        "confidence": "",
        "medical_explanation": "",
    }

    print("[Sistema] Iniciando verificación de noticias falsas...")
    print(f"[Sistema] Texto a analizar: '{INPUT_TEXT}'")

    # Ejecutar el grafo
    result = verification_system.invoke(initial_state)

    # Mostrar los resultados finales
    print("\n" + "=" * 50)
    label, confidence = result.get("label", "desconocida"), result.get(
        "confidence", "indefinida"
    )
    print("\nAnalisis médico:")
    print(result.get("medical_explanation", "No se generó informe."))
