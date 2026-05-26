"""
Este módulo define un agente traductor que toma una lista de afirmaciones en
español y devuelve sus traducciones al inglés clínico en una única llamada al LLM.
"""

from functools import lru_cache
from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from app.prompts.agents import Prompts


class TranslatedStatements(BaseModel):
    """Estructura de datos que devuelve el LLM con las traducciones."""

    translations: List[str] = Field(
        description=(
            "Lista de traducciones al inglés clínico, en el MISMO orden y con "
            "el MISMO número de elementos que la lista de afirmaciones recibida. "
            "No fusiones, omitas ni reordenes elementos."
        )
    )


@lru_cache(maxsize=1)
def get_translator_chain(prompt_text: str):
    """Devuelve la cadena de traducción configurada y cacheada."""
    llm = ChatOllama(model="translategemma", temperature=0)
    llm = llm.with_structured_output(TranslatedStatements)

    system_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_text),
            ("user", "Afirmaciones a traducir (numeradas):\n{statements}"),
        ]
    )
    return system_prompt | llm


def translator(state: dict, prompts: Prompts) -> dict:
    """
    Recibe las afirmaciones en español y las traduce al inglés clínico
    en una única llamada al LLM, preservando orden y cardinalidad.
    """
    print("[Agente Traductor] Traduciendo afirmaciones al inglés...")

    original_statements = state.get("extracted_statements", [])

    if not original_statements:
        return {"translated_statements": []}

    numbered = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(original_statements))

    translator_chain = get_translator_chain(prompts.translator.text)
    result = translator_chain.invoke({"statements": numbered})

    # Si el modelo devuelve menos elementos de los esperados, rellenamos con cadenas vacías
    translations = [t.strip() for t in result.translations]
    if len(translations) < len(original_statements):
        translations.extend([""] * (len(original_statements) - len(translations)))
    elif len(translations) > len(original_statements):
        translations = translations[: len(original_statements)]

    print(
        f"[Agente Traductor] Traducción completada ({len(translations)} afirmaciones)."
    )

    return {"translated_statements": translations}
