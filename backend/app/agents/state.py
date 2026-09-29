"""Estados tipados de los grafos de LangGraph que leen y actualizan los agentes."""

from typing import List, Optional, TypedDict

from app.core.claim import Claim, EvidenceSearch
from app.core.verdict import Verdict


class ClaimsState(TypedDict, total=False):
    """Estado que comparten ambos grafos, el texto y sus afirmaciones; el de solo evidencia no lleva más."""

    input_text: str
    claims: List[Claim]


class AgentState(ClaimsState, total=False):
    """Estado del grafo completo; cada nodo devuelve solo las claves que actualiza."""

    sources: List[dict]
    evidence_search: EvidenceSearch
    judge_failures: int
    verdict: Optional[Verdict]
    medical_explanation: str
