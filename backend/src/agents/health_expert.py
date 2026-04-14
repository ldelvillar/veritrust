"""
Este módulo define un agente experto en salud que interpreta el análisis técnico de un modelo de
IA sobre una afirmación médica y lo explica al paciente utilizando terminología médica rigurosa.
"""

import ast
import sys
from functools import lru_cache
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

# Asegura que, al ejecutar este archivo como script, se use el código local del repositorio.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.model_tool import FakeNewsDetectorTool
from src.prompts.main import HEALTH_EXPERT_PROMPT


@lru_cache(maxsize=8)
def _build_bert_tool(tool_class: type[FakeNewsDetectorTool]) -> FakeNewsDetectorTool:
    """Construye y cachea una instancia de detector por clase concreta."""
    return tool_class()


def _get_bert_tool() -> FakeNewsDetectorTool:
    """Devuelve una instancia reutilizable del detector BERT."""
    return _build_bert_tool(FakeNewsDetectorTool)


def health_expert(state: dict) -> dict:
    """
    Recibe las afirmaciones extraídas, usa el modelo BERT
    para verificarlas y redacta el informe médico con Llama 3.2.
    """
    print("[Agente Experto] Evaluando afirmaciones y redactando informes médicos...")

    # Recuperar la lista de afirmaciones extraídas y traducidas
    extracted_statements = state.get("extracted_statements", [])
    translated_statements = state.get("translated_statements", [])

    # Terminar la ejecución si la lista de afirmaciones está vacía
    if not extracted_statements or not translated_statements:
        return {
            "global_confidence": "Indeterminado",
            "medical_explanation": "No se detectaron afirmaciones médicas para evaluar.",
        }

    # Instanciar el LLM y la herramienta detectora
    llm = ChatOllama(model="llama3.2", temperature=0)
    bert_tool = _get_bert_tool()

    # Definir el prompt de sistema
    system_prompt = SystemMessage(content=HEALTH_EXPERT_PROMPT)

    total_fake_prob = 0.0
    total_statements = len(translated_statements)
    all_statements = ""

    # Iterar sobre cada afirmación para analizarla individualmente
    for original, translated in zip(extracted_statements, translated_statements):
        print("Analizando afirmación con BERT...")

        # Obtener el resultado del modelo
        result = bert_tool.invoke({"text": translated})

        # LangChain puede serializar salidas no-string de herramientas a texto.
        if isinstance(result, str):
            try:
                parsed = ast.literal_eval(result)
                if isinstance(parsed, dict):
                    result = parsed
            except (SyntaxError, ValueError):
                pass

        if (
            not isinstance(result, dict)
            or "label" not in result
            or "confidence" not in result
        ):
            raise ValueError(f"Salida inesperada del detector: {result}")

        print(f"Resultado del modelo para la afirmación: {result}")
        label, confidence = result["label"], result["confidence"]

        # Calcular la probabilidad de que la afirmación sea falsa para el veredicto global
        fake_prob = confidence if label == "falsa" else (1.0 - confidence)
        total_fake_prob += fake_prob

        # Unir todas las afirmaciones para el informe médico
        all_statements += f"- Afirmacion: '{original}'\n"

    # Calcular la media global
    fake_avg = total_fake_prob / total_statements

    # Determinar etiqueta global
    global_label = "falsa" if fake_avg > 0.40 else "verdadera"
    global_confidence = fake_avg if global_label == "falsa" else (1.0 - fake_avg)

    # Construir el prompt para el LLM con todo el contexto
    expert_message = HumanMessage(
        content=(
            f"Veredicto global del detector tecnico: La noticia es {global_label} con una "
            f"seguridad del {global_confidence * 100:.2f}%.\n\n"
            f"Afirmaciones detectadas en el texto original a analizar:\n"
            f"{all_statements}\n"
            f"Redacta un unico informe medico exhaustivo que englobe todas estas afirmaciones "
            f"y justifique el veredicto global."
        )
    )

    print("Generando explicación médica...")

    # Invocar al LLM para generar la explicación médica basada en el resultado del modelo
    medical_explanation = llm.invoke([system_prompt, expert_message]).content

    print("[Agente Experto] Todos los informes generados.")

    return {
        "label": global_label,
        "confidence": global_confidence,
        "medical_explanation": medical_explanation,
    }


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

    explanations = health_expert(simulated_state)

    print("\n" + "=" * 50)
    print("RESULTADOS FINALES:")
    print("=" * 50)
    print(f"Etiqueta global: {explanations['label']}")
    print(f"Confianza global: {explanations['confidence']:.2f}")
    print(f"Explicación médica:\n{explanations['medical_explanation']}")
