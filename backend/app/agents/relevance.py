"""Filtra las fuentes recuperadas dejando solo las relevantes para cada afirmación."""

import logging
from functools import lru_cache
from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RelevanceVerdicts(BaseModel):
    """Relevancia de cada fuente candidata, en el mismo orden que la entrada."""

    relevant: List[bool] = Field(
        description=(
            "Un booleano por fuente candidata, en el MISMO orden y número: true si "
            "el resumen aborda la afirmación (a favor o en contra), false si no."
        )
    )


@lru_cache(maxsize=1)
def get_relevance_chain(prompt_text: str):
    """Devuelve la cadena de juicio de relevancia configurada y cacheada."""
    settings = get_settings()
    llm = ChatOllama(
        model=settings.ollama_judge_model,
        temperature=0,
        base_url=settings.ollama_base_url,
    )
    structured_llm = llm.with_structured_output(RelevanceVerdicts)

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


def keep_relevant(prompt_text: str, claim: str, hits: list[dict]) -> list[dict]:
    """Devuelve solo las fuentes cuyo resumen es relevante para la afirmación.

    Falla en abierto: ante cualquier error del juez conserva todas las fuentes,
    para no descartar evidencia por un fallo de infraestructura.
    """
    if not hits:
        return hits

    chain = get_relevance_chain(prompt_text)
    try:
        verdict = chain.invoke({"claim": claim, "sources": _format_candidates(hits)})
    except Exception:
        logger.warning("[Juez] Fallo evaluando relevancia; se conservan las fuentes")
        return hits

    flags = list(verdict.relevant)
    # Ante desajuste de cardinalidad, conserva las fuentes no juzgadas.
    if len(flags) < len(hits):
        flags.extend([True] * (len(hits) - len(flags)))
    return [hit for hit, keep in zip(hits, flags) if keep]
