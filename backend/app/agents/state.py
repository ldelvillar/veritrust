"""Estados tipados de los grafos de LangGraph que leen y actualizan los agentes."""

from typing import List, Optional, TypedDict

from app.core.claim import Claim
from app.core.verdict import EvidenceSearch, Verdict


class ClaimsState(TypedDict, total=False):
    """Claves de extracción y traducción que comparten ambos grafos."""

    input_text: str
    claims: List[Claim]


class AgentState(ClaimsState, total=False):
    """Estado del grafo completo; cada nodo devuelve solo las claves que actualiza."""

    sources: List[dict]
    evidence_search: EvidenceSearch
    judge_failures: int
    verdict: Optional[Verdict]
    medical_explanation: str


class EvidenceState(ClaimsState, total=False):
    """Estado del grafo de solo evidencia: extracción, traducción y búsqueda juzgada."""

    valid_claims: int
    claim_evidence: List[dict]
