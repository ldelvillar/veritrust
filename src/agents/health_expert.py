"""
Este módulo define un agente experto en salud que interpreta el análisis técnico de un modelo de
IA sobre una afirmación médica y lo explica al paciente utilizando terminología clínica rigurosa.
"""

import sys
import os
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.tools.model_tool import FakeNewsDetectorTool


def health_expert(state: dict) -> dict:
    """
    Recibe las afirmaciones extraídas, usa BERT para verificarlas
    y Llama 3.2 para redactar el informe clínico.
    """
    print("[Agente Experto] Evaluando afirmaciones y redactando informes clínicos...")

    # Recuperar la lista de afirmaciones extraídas y traducidas
    extracted_statements = state.get("extracted_statements", [])
    translated_statements = state.get("translated_statements", [])

    # Terminar la ejecución si la lista de afirmaciones está vacía
    if not extracted_statements or not translated_statements:
        return {
            "clinical_explanations": [
                "No se detectaron afirmaciones médicas para evaluar."
            ]
        }

    # Instanciar el LLM y la herramienta detectora
    llm = ChatOllama(model="llama3", temperature=0)
    bert_tool = FakeNewsDetectorTool()

    # Definir el prompt de sistema
    system_prompt = SystemMessage(
        content=(
            "Eres un 'Agente Experto en Salud Pública y Epidemiología'. Tu labor es interpretar "
            "el análisis técnico de un modelo de IA sobre una afirmación médica "
            "y explicárselo al paciente. Instrucciones OBLIGATORIAS: "
            "Comienza indicando el veredicto del análisis técnico de forma clara. "
            "Explica médicamente por qué la afirmación original carece o tiene evidencia, "
            "usando terminología clínica rigurosa (ej. toxicidad, patógenos, profilaxis). "
            "Concluye SIEMPRE con este descargo exacto: '*Nota: Este análisis es generado "
            "por un sistema de IA y no sustituye el consejo de un profesional médico.*'"
        )
    )

    clinical_explanations = []

    # Iterar sobre cada afirmación para analizarla individualmente
    for original, translated in zip(extracted_statements, translated_statements):
        print("Analizando afirmación con BERT...")

        # Obtener el resultado del modelo
        model_output = bert_tool.invoke({"text": translated})

        expert_message = HumanMessage(
            content=(
                f"Afirmación del usuario a evaluar: '{original}'\n\n"
                f"Resultado inamovible de nuestro detector de Fake News (BERT): {model_output}\n\n"
                f"Redacta el informe clínico final basándote estrictamente en este resultado."
            )
        )

        print("Generando explicación clínica...")

        # Invocar al LLM para generar la explicación clínica basada en el resultado del modelo
        answer = llm.invoke([system_prompt, expert_message])

        # Guardar el resultado combinando la afirmación original y su explicación clínica
        result = f"**Afirmación:** {original}\n**Análisis:**\n{answer.content}"
        clinical_explanations.append(result)

    print("[Agente Experto] Todos los informes generados.")

    # Devolver el estado actualizado con los informes clínicos generados
    return {"clinical_explanations": clinical_explanations}


if __name__ == "__main__":
    # Simular el estado que pasaría el agente extractor
    simulated_state = {
        "extracted_statements": [
            "La lejía cura el COVID de forma instantánea según estudios.",
            "Comer manzanas previene las caries.",
        ],
        "translated_statements": [
            "Bleach cures COVID instantly according to studies.",
            "Eating apples prevents cavities.",
        ],
    }

    # Pasar el estado simulado al nodo para verificar su funcionamiento
    explanations = health_expert(simulated_state)

    print("\n" + "=" * 50)
    print("RESULTADOS FINALES:")
    print("=" * 50)
    for explanation in explanations["clinical_explanations"]:
        print(f"{explanation}\n{'-'*50}")
