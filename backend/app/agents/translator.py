"""
Este módulo define un agente traductor que toma un texto en inglés y lo
traduce al español para que el modelo pueda clasificarlo correctamente.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.prompts.main import TRANSLATOR_PROMPT


def translator(state: dict) -> dict:
    """
    Recibe las afirmaciones en español, las traduce al inglés clínico
    y las devuelve en el estado para que el modelo BERT pueda procesarlas.
    """
    print("[Agente Traductor] Traduciendo afirmaciones al inglés...")

    # Recuperar las afirmaciones en español del estado
    original_statements = state.get("extracted_statements", [])

    # Terminar la ejecución si no hay afirmaciones
    if not original_statements:
        return {"translated_statements": []}

    # Instanciar el LLM
    llm = ChatOllama(model="translategemma", temperature=0)

    # Definir el prompt de sistema
    system_prompt = SystemMessage(content=TRANSLATOR_PROMPT)

    translated_statements = []

    # Iterar sobre cada afirmación para traducirla
    for statement in original_statements:
        # Invocar al LLM
        expert_message = HumanMessage(content=statement)
        answer = llm.invoke([system_prompt, expert_message])

        # Limpiar posibles espacios en blanco y guardar
        translation = answer.content.strip()
        translated_statements.append(translation)

    print("[Agente Traductor] Traducción completada.")

    return {"translated_statements": translated_statements}
