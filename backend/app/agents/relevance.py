"""Juzga la relevancia y la postura de las fuentes recuperadas para cada afirmación."""

import logging
from collections.abc import Sequence
from functools import lru_cache
from itertools import count
from typing import Any, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.agents.sanitize import neutralize_delimiters
from app.core.claim import Evidence, JudgeStance
from app.core.config import get_settings
from app.utils.llm import build_chat_model

logger = logging.getLogger(__name__)


class EvidenceJudgments(BaseModel):
    """Postura de cada fuente candidata, en el mismo orden que la entrada."""

    stances: List[JudgeStance] = Field(
        description=(
            "Una postura por fuente candidata, en el MISMO orden y número: "
            "'supports' si el resumen respalda la afirmación, 'contradicts' si la "
            "refuta, 'inconclusive' si la aborda sin concluir, 'unrelated' si trata "
            "de otro tema."
        )
    )


# La cuota diaria de Groq es por modelo: el juez alterna para no agotar uno solo.
_rotation = count()


def _next_judge_model() -> str | None:
    """Siguiente modelo de la rotación del juez, o ``None`` si no se rota."""
    settings = get_settings()
    if settings.llm_provider_name() != "groq":
        return None
    models = settings.groq_judge_models()
    if not models:
        return None
    return models[next(_rotation) % len(models)]


@lru_cache(maxsize=8)
def get_relevance_chain(
    prompt_text: str, model: str | None = None
) -> Runnable[dict[str, Any], Any]:
    """Devuelve la cadena de juicio de evidencia configurada y cacheada por modelo."""
    llm = build_chat_model("judge", model)
    structured_llm = llm.with_structured_output(EvidenceJudgments)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_text),
            (
                "user",
                "Afirmación:\n<<USER_INPUT>>\n{claim}\n<<END>>\n\n"
                "Fuentes candidatas:\n<<USER_INPUT>>\n{sources}\n<<END>>",
            ),
        ]
    )
    return prompt | structured_llm


def _format_candidates(evidence: Sequence[Evidence]) -> str:
    """Numera el título y el resumen de cada candidata para el prompt."""
    lines = []
    for index, item in enumerate(evidence, start=1):
        title = neutralize_delimiters(item.title).strip()
        abstract = neutralize_delimiters(item.abstract or "").strip()
        body = f"{title}. {abstract}" if abstract else title
        lines.append(f"{index}. {body}")
    return "\n".join(lines)


def judge_stances(
    prompt_text: str, claim: str, evidence: Sequence[Evidence]
) -> tuple[JudgeStance, ...] | None:
    """Pide al juez una postura por fuente candidata; ``None`` si falla o no da exactamente una por fuente."""
    if not evidence:
        return ()

    try:
        chain = get_relevance_chain(prompt_text, _next_judge_model())
        verdict = chain.invoke(
            {
                "claim": neutralize_delimiters(claim),
                "sources": _format_candidates(evidence),
            }
        )
    except Exception:
        logger.warning(
            "[Juez] Fallo evaluando la evidencia; se conservan las fuentes",
            exc_info=True,
        )
        return None

    stances = tuple(verdict.stances)
    # Sin una postura por fuente no se sabe a cuál corresponde cada una.
    if len(stances) != len(evidence):
        logger.warning(
            "[Juez] %d posturas para %d fuentes; se conservan las fuentes",
            len(stances),
            len(evidence),
        )
        return None
    return stances
