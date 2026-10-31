"""Translator agent that turns Spanish claims into clinical English in a single LLM call."""

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

# The input is numbered and the model sometimes returns the number glued to the translation.
_LEADING_NUMBER = re.compile(r"^\s*\d+\s*[.)-]\s+")


# One field per claim, so the translator cannot merge, drop or add translations.
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
    """Return the translation chain for ``statements`` claims, cached by count."""
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
    """Translate the Spanish claims into clinical English in one LLM call, keeping order and count."""
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
