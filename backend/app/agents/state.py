"""Estados tipados de los grafos de LangGraph que leen y actualizan los agentes."""

from typing import List, TypedDict


class ClaimsState(TypedDict, total=False):
    """Claves de extracción y traducción que comparten ambos grafos."""

    input_text: str
    extracted_statements: List[str]
    search_queries: List[str]
    drug_terms: List[str]
    translated_statements: List[str]


class AgentState(ClaimsState, total=False):
    """Estado del grafo completo; cada nodo devuelve solo las claves que actualiza."""

    sources: List[dict]
    evidence_coverage: float
    judge_failures: int
    label: str
    confidence: float
    medical_explanation: str
    claims: List[dict]


class EvidenceState(ClaimsState, total=False):
    """Estado del grafo de solo evidencia: extracción, traducción y búsqueda juzgada."""

    valid_claims: int
    claim_evidence: List[dict]
