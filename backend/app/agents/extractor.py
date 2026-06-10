"""
Este módulo define un agente de captura de información que extrae las afirmaciones importantes
de un texto largo para su posterior análisis por parte de un agente experto en salud.
"""

import logging
from functools import lru_cache
from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.prompts.agents import Prompts

logger = logging.getLogger(__name__)


class MedicalStatements(BaseModel):
    """Estructura de datos que devuelve el LLM."""

    statements: List[str] = Field(
        description=(
            "Lista exacta de afirmaciones médicas, dietéticas o de "
            "salud extraídas del texto que requieren verificación "
            "científica. Deben ser oraciones cortas y claras."
        )
    )


@lru_cache(maxsize=1)
def get_extractor_chain(prompt_text: str):
    """Devuelve la cadena de extracción configurada y cacheada."""
    settings = get_settings()
    llm = ChatOllama(
        model=settings.ollama_extractor_model,
        temperature=0,
        base_url=settings.ollama_base_url,
    )
    structured_llm = llm.with_structured_output(MedicalStatements)

    system_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_text),
            ("user", "Texto a analizar:\n<<USER_INPUT>>\n{texto}\n<<END>>"),
        ]
    )
    return system_prompt | structured_llm


def extractor(state: dict, prompts: Prompts) -> dict:
    """
    Recibe el estado actual, ejecuta la extracción y devuelve el estado actualizado.
    """
    logger.info("[Extractor] Analizando el texto en busca de afirmaciones médicas")

    input_text = state.get("input_text", "")

    # Ejecutar la cadena
    extractor_chain = get_extractor_chain(prompts.extractor.text)
    result = extractor_chain.invoke({"texto": input_text})

    logger.info("[Extractor] Se extrajeron %d afirmaciones", len(result.statements))

    # Devolver la parte del estado que este agente es responsable de actualizar
    return {"extracted_statements": result.statements}
