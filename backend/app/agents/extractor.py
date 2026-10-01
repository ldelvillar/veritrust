"""
Este módulo define un agente de captura de información que extrae las afirmaciones importantes
de un texto largo para su posterior análisis por parte de un agente experto en salud.
"""

import logging
from functools import lru_cache
from typing import Any, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.agents.state import ClaimsState
from app.core.claim import Claim
from app.prompts.agents import Prompts
from app.utils.llm import build_chat_model

logger = logging.getLogger(__name__)


class ExtractedClaim(BaseModel):
    """Una afirmación extraída con todo lo que el modelo aporta para buscar su evidencia."""

    statement: str = Field(
        description=(
            "Afirmación médica, dietética o de salud del texto que requiere "
            "verificación científica, como oración corta y clara."
        )
    )
    search_query: str = Field(
        description=(
            "Consulta de búsqueda en inglés para esta afirmación, con los términos "
            "clínicos clave unidos por operadores booleanos, sin comillas de ningún "
            "tipo. Ej.: (vitamin C OR ascorbic acid) AND (common cold)."
        )
    )
    drug_term: str = Field(
        description=(
            "Nombre del medicamento o principio activo que menciona esta afirmación "
            "(en español), o cadena vacía si no trata de un fármaco concreto. "
            "Ej.: 'ibuprofeno', ''."
        )
    )


class MedicalStatements(BaseModel):
    """Estructura de datos que devuelve el LLM."""

    claims: List[ExtractedClaim] = Field(
        description=(
            "Afirmaciones médicas, dietéticas o de salud extraídas del texto que "
            "requieren verificación científica."
        )
    )


@lru_cache(maxsize=1)
def get_extractor_chain(prompt_text: str) -> Runnable[dict[str, Any], Any]:
    """Devuelve la cadena de extracción configurada y cacheada."""
    llm = build_chat_model("extractor")
    structured_llm = llm.with_structured_output(MedicalStatements)

    system_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_text),
            ("user", "Texto a analizar:\n<<USER_INPUT>>\n{texto}\n<<END>>"),
        ]
    )
    return system_prompt | structured_llm


def extractor(state: ClaimsState, prompts: Prompts) -> ClaimsState:
    """
    Recibe el estado actual, ejecuta la extracción y devuelve el estado actualizado.
    """
    logger.info("[Extractor] Analizando el texto en busca de afirmaciones médicas")

    input_text = state.get("input_text", "")

    # Ejecutar la cadena
    extractor_chain = get_extractor_chain(prompts.extractor.text)
    result = extractor_chain.invoke({"texto": input_text})

    claims = [
        Claim(
            index=index,
            text=item.statement,
            query=item.search_query,
            drug_term=item.drug_term.strip(),
        )
        for index, item in enumerate(result.claims)
    ]

    logger.info("[Extractor] Se extrajeron %d afirmaciones", len(claims))

    # Devolver la parte del estado que este agente es responsable de actualizar
    return {"claims": claims}
