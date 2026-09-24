"""
Este módulo define un agente experto en salud que obtiene el veredicto de la postura de la
literatura biomédica recuperada y lo explica al paciente con terminología médica rigurosa.
"""

import logging
from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents import sanitize
from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.verdict import decide
from app.prompts.agents import HealthExpertPrompt, Prompts
from app.utils.llm import build_chat_model

logger = logging.getLogger(__name__)

# Alias interno hacia la neutralización compartida de marcadores.
_neutralize_delimiters = sanitize.neutralize_delimiters


def _build_evidence_block(prompt: HealthExpertPrompt, sources: list[dict]) -> str:
    """Formatea las fuentes recuperadas como DATOS para fundamentar el informe."""
    if not sources:
        return prompt.evidence_missing

    lines = []
    for source in sources:
        title = _neutralize_delimiters(str(source.get("title", ""))).strip()
        if not title:
            continue
        journal = _neutralize_delimiters(str(source.get("source") or "")).strip()
        year = str(source.get("year") or "").strip()
        meta = ", ".join(part for part in (journal, year) if part)
        lines.append(f"- {title}" + (f" ({meta})" if meta else ""))

    return prompt.evidence_sources.format(listing="\n".join(lines))


@lru_cache(maxsize=1)
def get_health_expert_llm() -> BaseChatModel:
    """Devuelve el LLM del experto en salud configurado y cacheado."""
    return build_chat_model("health_expert")


def health_expert(state: AgentState, prompts: Prompts) -> AgentState:
    """
    Recibe las afirmaciones extraídas, las verifica contra la postura de la
    literatura recuperada y redacta el informe médico con el LLM configurado.
    """
    logger.info("[Experto] Evaluando afirmaciones y redactando informe médico")

    extracted_statements = state.get("extracted_statements", [])
    translated_statements = state.get("translated_statements", [])

    if not extracted_statements or not translated_statements:
        return {"verdict": None, "medical_explanation": ""}

    # Instanciar el LLM
    llm = get_health_expert_llm()

    # Definir el prompt de sistema
    prompt = prompts.health_expert
    system_prompt = SystemMessage(content=prompt.text)

    claims = [
        _neutralize_delimiters(str(original)) for original in extracted_statements
    ]
    all_statements = "".join(f"- Afirmacion: '{claim}'\n" for claim in claims)

    # La postura de la literatura es la unica fuente del veredicto.
    verdict = decide(claims, state.get("sources") or [], state["evidence_search"])

    evidence_block = _build_evidence_block(prompt, state.get("sources") or [])

    # Un veredicto incierto no debe presentarse como una conclusión firme: el
    # informe debe explicar la ambigüedad, no afirmar que es verdadero o falso.
    if verdict.kind == "uncertain":
        verdict_line = prompt.verdict_uncertain
        closing_line = prompt.closing_uncertain
    else:
        verdict_line = prompt.verdict_certain.format(
            label=verdict.label, confidence=verdict.confidence * 100
        )
        closing_line = prompt.closing_certain

    # Construir el prompt para el LLM con todo el contexto.
    expert_message = HumanMessage(
        content=prompt.user_message.format(
            verdict_line=verdict_line,
            statements=all_statements,
            evidence_block=evidence_block,
            closing_line=closing_line,
        )
    )

    # El informe no decide la etiqueta: al evaluar se omite para no gastar tokens.
    if get_settings().health_expert_explanation_enabled:
        logger.info("[Experto] Generando explicación médica")
        medical_explanation = str(llm.invoke([system_prompt, expert_message]).content)
        logger.info("[Experto] Informe médico generado")
    else:
        logger.info("[Experto] Explicación desactivada; solo se calcula el veredicto")
        medical_explanation = ""

    return {"verdict": verdict, "medical_explanation": medical_explanation}
