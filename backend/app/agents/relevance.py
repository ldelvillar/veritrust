"""Juzga la relevancia y la postura de las fuentes recuperadas para cada afirmación."""

import logging
from functools import lru_cache
from itertools import count
from typing import List, Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.utils.llm import build_chat_model

logger = logging.getLogger(__name__)

# "unrelated" descarta la fuente; las demás se conservan con su postura.
JudgeStance = Literal["supports", "contradicts", "inconclusive", "unrelated"]


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
def get_relevance_chain(prompt_text: str, model: str | None = None):
    """Devuelve la cadena de juicio de evidencia configurada y cacheada por modelo."""
    llm = build_chat_model("judge", model)
    structured_llm = llm.with_structured_output(EvidenceJudgments)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_text),
            ("user", "Afirmación:\n{claim}\n\nFuentes candidatas:\n{sources}"),
        ]
    )
    return prompt | structured_llm


def _format_candidates(hits: list[dict]) -> str:
    """Numera el título y el resumen de cada candidata para el prompt."""
    lines = []
    for index, hit in enumerate(hits, start=1):
        title = str(hit.get("title", "")).strip()
        abstract = str(hit.get("abstract") or "").strip()
        body = f"{title}. {abstract}" if abstract else title
        lines.append(f"{index}. {body}")
    return "\n".join(lines)


def judge_evidence(prompt_text: str, claim: str, hits: list[dict]) -> list[dict]:
    """Devuelve las fuentes relevantes, cada una anotada con su ``stance``.

    Descarta las marcadas como ``unrelated``. Falla en abierto: ante cualquier
    error del juez conserva todas las fuentes (sin postura), para no descartar
    evidencia por un fallo de infraestructura.
    """
    if not hits:
        return hits

    chain = get_relevance_chain(prompt_text, _next_judge_model())
    try:
        verdict = chain.invoke({"claim": claim, "sources": _format_candidates(hits)})
    except Exception:
        logger.warning(
            "[Juez] Fallo evaluando la evidencia; se conservan las fuentes",
            exc_info=True,
        )
        return hits

    stances = list(verdict.stances)
    # Ante desajuste de cardinalidad, conserva las fuentes no juzgadas.
    if len(stances) < len(hits):
        stances.extend(["inconclusive"] * (len(hits) - len(stances)))
    return [
        {**hit, "stance": stance}
        for hit, stance in zip(hits, stances)
        if stance != "unrelated"
    ]
