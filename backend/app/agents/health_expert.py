"""
Este módulo define un agente experto en salud que deriva el veredicto de la postura de la
literatura biomédica recuperada y lo explica al paciente con terminología médica rigurosa.
"""

import logging
from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents import sanitize
from app.core.credibility import adjust_confidence_with_evidence
from app.prompts.agents import HealthExpertPrompt, Prompts
from app.utils.llm import build_chat_model

logger = logging.getLogger(__name__)

# Alias interno hacia la neutralización compartida de marcadores.
_neutralize_delimiters = sanitize.neutralize_delimiters

# Punto neutro del score suavizado: por debajo la evidencia apoya, por encima refuta
FAKE_THRESHOLD = 0.50
UNCERTAINTY_MARGIN = 0.05
# Pseudo-cuenta por postura: impide la certeza absoluta con evidencia escasa
STANCE_SMOOTHING = 1.0


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


def _stance_counts_by_claim(sources: list[dict]) -> dict[int, dict[str, int]]:
    """Cuenta, por índice de afirmación, cuántas fuentes la respaldan o la contradicen."""
    counts: dict[int, dict[str, int]] = {}
    for source in sources:
        for statement in source.get("statements") or []:
            claim_index = statement.get("claim_index")
            stance = statement.get("stance")
            if not isinstance(claim_index, int) or stance not in (
                "supports",
                "contradicts",
            ):
                continue
            bucket = counts.setdefault(claim_index, {"supports": 0, "contradicts": 0})
            bucket[stance] += 1
    return counts


@lru_cache(maxsize=1)
def get_health_expert_llm() -> BaseChatModel:
    """Devuelve el LLM del experto en salud configurado y cacheado."""
    return build_chat_model("health_expert")


def _fake_prob_from_stance(counts: dict | None) -> float:
    """Prob. de falsedad de una afirmacion segun la postura de la literatura."""
    supports = counts["supports"] if counts else 0
    contradicts = counts["contradicts"] if counts else 0
    # Suavizado de Laplace: sin evidencia el resultado es 0.5, y unas pocas
    # fuentes en un sentido no bastan para un veredicto con confianza plena.
    return (contradicts + STANCE_SMOOTHING) / (
        supports + contradicts + 2 * STANCE_SMOOTHING
    )


def _has_stance_evidence(counts: dict | None) -> bool:
    """Indica si la literatura recuperada llega a pronunciarse sobre la afirmación."""
    if not counts:
        return False
    return (counts["supports"] + counts["contradicts"]) > 0


def _verdict_from_fake_prob(
    fake_prob: float, has_evidence: bool = True
) -> tuple[str, float]:
    """Traduce una probabilidad de falsedad en etiqueta y confianza."""
    # La ausencia de literatura no es prueba de falsedad: sin postura, es incierta.
    if not has_evidence:
        return "incierta", 1.0 - fake_prob
    if fake_prob > FAKE_THRESHOLD + UNCERTAINTY_MARGIN:
        return "falsa", fake_prob
    if fake_prob < FAKE_THRESHOLD - UNCERTAINTY_MARGIN:
        return "verdadera", 1.0 - fake_prob
    return "incierta", 1.0 - fake_prob


def health_expert(state: dict, prompts: Prompts) -> dict:
    """
    Recibe las afirmaciones extraídas, las verifica contra la postura de la
    literatura recuperada y redacta el informe médico con el LLM configurado.
    """
    logger.info("[Experto] Evaluando afirmaciones y redactando informe médico")

    extracted_statements = state.get("extracted_statements", [])
    translated_statements = state.get("translated_statements", [])

    if not extracted_statements or not translated_statements:
        return {
            "label": "",
            "confidence": 0.0,
            "medical_explanation": "",
            "claims": [],
        }

    # Instanciar el LLM
    llm = get_health_expert_llm()

    # Definir el prompt de sistema
    prompt = prompts.health_expert
    system_prompt = SystemMessage(content=prompt.text)

    evidenced_probs: list[float] = []
    all_statements = ""
    claims: list[dict] = []

    # La postura de la literatura es la unica fuente del veredicto.
    stance_counts = _stance_counts_by_claim(state.get("sources") or [])

    for claim_index, original in enumerate(extracted_statements):
        counts = stance_counts.get(claim_index)
        fake_prob = _fake_prob_from_stance(counts)
        has_evidence = _has_stance_evidence(counts)
        if has_evidence:
            evidenced_probs.append(fake_prob)
        label, confidence = _verdict_from_fake_prob(fake_prob, has_evidence)

        safe_original = _neutralize_delimiters(str(original))
        all_statements += f"- Afirmacion: '{safe_original}'\n"

        # Veredicto por afirmacion para el desglose del informe.
        claims.append({"text": safe_original, "label": label, "confidence": confidence})

    # Solo promedia las afirmaciones sobre las que la literatura se pronuncia.
    fake_avg = sum(evidenced_probs) / len(evidenced_probs) if evidenced_probs else 0.5

    # Determinar etiqueta global
    global_label, global_confidence = _verdict_from_fake_prob(
        fake_avg, bool(evidenced_probs)
    )

    # La confianza se atenúa según cuánta literatura biomédica respalde el análisis.
    evidence_coverage = float(state.get("evidence_coverage", 1.0))
    global_confidence = adjust_confidence_with_evidence(
        global_confidence, evidence_coverage
    )

    evidence_block = _build_evidence_block(prompt, state.get("sources") or [])

    # Un veredicto incierto no debe presentarse como una conclusión firme: el
    # informe debe explicar la ambigüedad, no afirmar que es verdadero o falso.
    if global_label == "incierta":
        verdict_line = prompt.verdict_uncertain
        closing_line = prompt.closing_uncertain
    else:
        verdict_line = prompt.verdict_certain.format(
            label=global_label, confidence=global_confidence * 100
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

    logger.info("[Experto] Generando explicación médica")

    # Invocar al LLM para generar la explicación médica basada en el resultado del modelo
    medical_explanation = llm.invoke([system_prompt, expert_message]).content

    logger.info("[Experto] Informe médico generado")

    return {
        "label": global_label,
        "confidence": global_confidence,
        "medical_explanation": medical_explanation,
        "claims": claims,
    }
