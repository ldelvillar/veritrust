"""
Este módulo define un agente de captura de información que extrae las afirmaciones importantes
de un texto largo para su posterior análisis por parte de un agente experto en salud.
"""

from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field
from src.prompts.main import EXTRACTOR_PROMPT


class MedicalStatements(BaseModel):
    """Estructura de datos que devuelve el LLM."""

    statements: List[str] = Field(
        description=(
            "Lista exacta de afirmaciones médicas, dietéticas o de "
            "salud extraídas del texto que requieren verificación "
            "científica. Deben ser oraciones cortas y claras."
        )
    )


# Configurar el LLM para que devuelva un formato JSON que coincida con la clase Pydantic
llm = ChatOllama(model="llama3", temperature=0)
llm = llm.with_structured_output(MedicalStatements)

# Definir el prompt de sistema
system_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            EXTRACTOR_PROMPT,
        ),
        ("user", "Texto a analizar: {texto}"),
    ]
)

# Crear la cadena
extractor_chain = system_prompt | llm


def extractor(state: dict) -> dict:
    """
    Recibe el estado actual, ejecuta la extracción y devuelve el estado actualizado.
    """
    print("[Agente Extractor] Analizando el texto en busca de afirmaciones médicas...")

    input_text = state.get("input_text", "")

    # Ejecutar la cadena
    result = extractor_chain.invoke({"texto": input_text})

    print(f"[Agente Extractor] Se extrajeron {len(result.statements)} afirmaciones.")

    # Devolver la parte del estado que este agente es responsable de actualizar
    return {"extracted_statements": result.statements}


if __name__ == "__main__":
    TEXT = (
        "Hola a todos en el grupo. Ayer leí en un blog que si tomas agua con limón en ayunas "
        "y una cucharada de aceite de coco, curas la diabetes tipo 2 en un mes. Además, dicen "
        "que las vacunas de la gripe te bajan las defensas. ¿Es esto verdad? Saludos."
    )
    initial_state = {"input_text": TEXT}

    new_state = extractor(initial_state)
    print("\nResultado:")
    for i, statement in enumerate(new_state["extracted_statements"]):
        print(f"{i+1}. {statement}")
