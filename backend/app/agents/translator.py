"""
Este módulo define un agente traductor que toma una lista de afirmaciones en
español y devuelve sus traducciones al inglés clínico en una única llamada al LLM.
"""

import logging
import re
from dataclasses import replace
from functools import lru_cache
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.agents.numbered_answers import NumberedAnswers
from app.agents.sanitize import neutralize_delimiters
from app.agents.state import ClaimsState
from app.prompts.agents import Prompts
from app.utils.llm import build_chat_model

logger = logging.getLogger(__name__)

# La entrada va numerada y el modelo a veces devuelve el número pegado a la traducción.
_LEADING_NUMBER = re.compile(r"^\s*\d+\s*[.)-]\s+")


# Un campo por afirmación: el traductor no puede fusionar, omitir ni añadir traducciones.
TRANSLATIONS = NumberedAnswers(
    name="TranslatedStatements",
    field="translation",
    answer=str,
    description="Traducción al inglés clínico de la afirmación {n}.",
)


@lru_cache(maxsize=16)
def get_translator_chain(
    prompt_text: str, statements: int
) -> Runnable[dict[str, Any], Any]:
    """Devuelve la cadena de traducción para ``statements`` afirmaciones, cacheada por número."""
    llm = build_chat_model("translator")
    structured_llm = llm.with_structured_output(TRANSLATIONS.schema(statements))

    system_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_text),
            (
                "user",
                "Afirmaciones a traducir (numeradas):\n"
                "<<USER_INPUT>>\n{statements}\n<<END>>",
            ),
        ]
    )
    return system_prompt | structured_llm


def translator(state: ClaimsState, prompts: Prompts) -> ClaimsState:
    """
    Recibe las afirmaciones en español y las traduce al inglés clínico
    en una única llamada al LLM, preservando orden y cardinalidad.
    """
    logger.info("[Traductor] Traduciendo afirmaciones al inglés")

    claims = state.get("claims", [])

    if not claims:
        return {"claims": []}

    numbered = "\n".join(
        f"{i + 1}. {neutralize_delimiters(claim.text)}"
        for i, claim in enumerate(claims)
    )

    translator_chain = get_translator_chain(prompts.translator.text, len(claims))
    result = translator_chain.invoke({"statements": numbered})

    translated = [
        replace(claim, text_en=_LEADING_NUMBER.sub("", text_en).strip())
        for claim, text_en in zip(
            claims, TRANSLATIONS.in_order(result, len(claims)), strict=True
        )
    ]

    logger.info("[Traductor] Traducción completada (%d afirmaciones)", len(translated))

    return {"claims": translated}
