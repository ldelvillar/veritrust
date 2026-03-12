"""
Este módulo construye el grafo de LangGraph, define los nodos (agentes) y ejecuta
el flujo completo para verificar noticias falsas en el ámbito de la salud.
"""

from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from src.agents.extractor import extractor
from src.agents.translator import translator
from src.agents.health_expert import health_expert
from src.utils.start_ollama import start_ollama


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
        "tipo de infección viral, y que las mascarillas causan hipoxia severa."
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
    print(f"La noticia es {label} con una confianza del {confidence * 100:.2f}%.")
    print("\nAnalisis médico:")
    print(result.get("medical_explanation", "No se generó informe."))
