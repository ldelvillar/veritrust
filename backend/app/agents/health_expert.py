"""
Este módulo define un agente experto en salud que obtiene el veredicto de la postura de la
literatura biomédica recuperada y lo explica a quien verifica el contenido con terminología
médica rigurosa.
"""

import logging
from collections.abc import Sequence
from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents import sanitize
from app.agents.state import AgentState
from app.core.claim import Claim
from app.core.config import get_settings
from app.core.verdict import decide
from app.prompts.agents import HealthExpertPrompt, Prompts
from app.utils.llm import build_chat_model

logger = logging.getLogger(__name__)

# Alias interno hacia la neutralización compartida de marcadores.
_neutralize_delimiters = sanitize.neutralize_delimiters

# Postura del juez tal como la lee el experto.
_STANCE_LABEL = {
    "supports": "respalda",
    "contradicts": "contradice",
    "inconclusive": "no es concluyente sobre",
}


def _build_evidence_block(prompt: HealthExpertPrompt, claims: Sequence[Claim]) -> str:
    """Formatea cada fuente mostrada con su postura y su resumen como DATOS para fundamentar el informe."""
    lines = []
    for claim in claims:
        statement = _neutralize_delimiters(claim.text)
        for item in claim.evidence:
            title = _neutralize_delimiters(item.title).strip()
            if not title:
                continue
            meta = ", ".join(
                part.strip()
                for part in (_neutralize_delimiters(item.source or ""), item.year or "")
                if part.strip()
            )
            stance = _STANCE_LABEL.get(item.stance or "", "no se juzgó frente a")
            abstract = _neutralize_delimiters(item.abstract or "").strip()
            lines.append(
                f"- Fuente: {title}"
                + (f" ({meta})" if meta else "")
                + f"\n  Postura: {stance} la afirmación '{statement}'"
                + f"\n  Resumen: {abstract or 'no disponible'}"
            )

    if not lines:
        return prompt.evidence_missing
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

    claims = state.get("shown_claims", [])

    if not claims:
        return {"verdict": None, "medical_explanation": ""}

    # Instanciar el LLM
    llm = get_health_expert_llm()

    # Definir el prompt de sistema
    prompt = prompts.health_expert
    system_prompt = SystemMessage(content=prompt.text)

    # La postura de la literatura es la unica fuente del veredicto.
    verdict = decide(claims, state["evidence_search"])

    # Cada afirmación con su veredicto: el informe debe decir cuáles son falsas.
    all_statements = "".join(
        f"- Afirmacion: '{_neutralize_delimiters(claim.text)}' (veredicto: {claim.label})\n"
        for claim in verdict.claims
    )

    evidence_block = _build_evidence_block(prompt, claims)

    # Un veredicto incierto no debe presentarse como una conclusión firme: el
    # informe debe explicar la ambigüedad, no afirmar que es verdadero o falso.
    if verdict.kind == "uncertain":
        verdict_line = prompt.verdict_uncertain
        closing_line = prompt.closing_uncertain
    else:
        verdict_line = prompt.verdict_certain.format(
            label=verdict.label, confidence=verdict.confidence * 100
        )
        closing_line = (
            prompt.closing_mixed if verdict.kind == "mixed" else prompt.closing_certain
        )

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
