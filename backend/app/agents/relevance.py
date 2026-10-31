"""Judge the relevance and Stance of the Sources retrieved for each claim."""

import logging
from collections.abc import Sequence
from functools import lru_cache
from itertools import count
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field, ValidationError

from app.agents.numbered_answers import NumberedAnswers
from app.agents.sanitize import neutralize_delimiters
from app.core.claim import Evidence, JudgeStance
from app.core.config import get_settings
from app.utils.llm import build_chat_model

logger = logging.getLogger(__name__)


class SourceJudgment(BaseModel):
    """Juicio de una fuente: su hallazgo va antes que su postura para que el juez lo compare con la afirmación."""

    finding: str = Field(
        description="Qué concluye la fuente, en una frase, escrito sin mirar la afirmación."
    )
    stance: JudgeStance = Field(
        description=(
            "'supports' si el hallazgo respalda la afirmación, 'contradicts' si la refuta, "
            "'inconclusive' si la aborda sin concluir, 'unrelated' si trata de otro tema."
        )
    )


# One field per candidate Source, so the judge cannot give more or fewer Stances than Sources.
EVIDENCE_JUDGMENTS = NumberedAnswers(
    name="EvidenceJudgments",
    field="source",
    answer=SourceJudgment,
    description="Hallazgo y postura de la fuente {n}.",
)


# Groq's daily quota is per model, so the judge rotates to avoid exhausting just one.
_rotation = count()


def _next_judge_model() -> str | None:
    """Next model in the judge rotation, or ``None`` when there is no rotation."""
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
    """Return the judging chain for ``sources`` candidates, cached by count and model."""
    llm = build_chat_model("judge", model)
    structured_llm = llm.with_structured_output(EVIDENCE_JUDGMENTS.schema(sources))

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_text),
            (
                "user",
                "Afirmación:\n<<USER_INPUT>>\n{claim}\n<<END>>\n\n"
                "Fuentes candidatas ({count}):\n<<USER_INPUT>>\n{sources}\n<<END>>",
            ),
        ]
    )
    return prompt | structured_llm


def _format_candidates(evidence: Sequence[Evidence]) -> str:
    """Number each candidate's title and abstract for the prompt."""
    lines = []
    for index, item in enumerate(evidence, start=1):
        title = neutralize_delimiters(item.title).strip()
        abstract = neutralize_delimiters(item.abstract or "").strip()
        body = f"{title}. {abstract}" if abstract else title
        lines.append(f"{index}. {body}")
    return "\n".join(lines)


def _ask_judge(
    prompt_text: str, claim: str, evidence: Sequence[Evidence]
) -> tuple[JudgeStance, ...]:
    """Make one judge call, raising if it fails or its answer does not name each Source once."""
    chain = get_relevance_chain(prompt_text, len(evidence), _next_judge_model())
    answer = chain.invoke(
        {
            "claim": neutralize_delimiters(claim),
            "sources": _format_candidates(evidence),
            # Without knowing how many there are, the judge sometimes skips the last Source.
            "count": len(evidence),
        }
    )
    return tuple(
        judgment.stance
        for judgment in EVIDENCE_JUDGMENTS.in_order(answer, len(evidence))
    )


def judge_stances(
    prompt_text: str, claim: str, evidence: Sequence[Evidence]
) -> tuple[JudgeStance, ...] | None:
    """Ask the judge for one Stance per candidate Source, or ``None`` if it fails or does not name each Source once."""
    if not evidence:
        return ()

    try:
        try:
            return _ask_judge(prompt_text, claim, evidence)
        except (ValidationError, OutputParserException):
            if len(evidence) < 2:
                raise
            # A long answer is the one that comes back incomplete, so each half asks for a shorter one.
            half = len(evidence) // 2
            return _ask_judge(prompt_text, claim, evidence[:half]) + _ask_judge(
                prompt_text, claim, evidence[half:]
            )
    except Exception:
        logger.warning(
            "[Juez] Fallo evaluando la evidencia; se conservan las fuentes",
            exc_info=True,
        )
        return None
