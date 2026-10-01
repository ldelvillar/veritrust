"""Juzga la relevancia y la postura de las fuentes recuperadas para cada afirmación."""

import logging
from collections.abc import Sequence
from functools import lru_cache
from itertools import count
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.agents.numbered_answers import NumberedAnswers
from app.agents.sanitize import neutralize_delimiters
from app.core.claim import Evidence, JudgeStance
from app.core.config import get_settings
from app.utils.llm import build_chat_model

logger = logging.getLogger(__name__)

# Un campo por fuente candidata: el juez no puede dar más posturas ni menos que fuentes.
EVIDENCE_JUDGMENTS = NumberedAnswers(
    name="EvidenceJudgments",
    field="source",
    answer=JudgeStance,
    description=(
        "Postura de la fuente {n}: 'supports' si su resumen respalda la afirmación, "
        "'contradicts' si la refuta, 'inconclusive' si la aborda sin concluir, "
        "'unrelated' si trata de otro tema."
    ),
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


@lru_cache(maxsize=64)
def get_relevance_chain(
    prompt_text: str, sources: int, model: str | None = None
) -> Runnable[dict[str, Any], Any]:
    """Devuelve la cadena de juicio para ``sources`` candidatas, cacheada por número y modelo."""
    llm = build_chat_model("judge", model)
    structured_llm = llm.with_structured_output(EVIDENCE_JUDGMENTS.schema(sources))

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
    """Pide al juez una postura por fuente candidata; ``None`` si falla o su respuesta no nombra cada fuente una vez."""
    if not evidence:
        return ()

    try:
        chain = get_relevance_chain(prompt_text, len(evidence), _next_judge_model())
        answer = chain.invoke(
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
    return EVIDENCE_JUDGMENTS.in_order(answer, len(evidence))
