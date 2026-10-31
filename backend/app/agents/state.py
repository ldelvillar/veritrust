"""Typed LangGraph graph states that the agents read and update."""

from typing import List, Optional, TypedDict

from app.core.claim import Claim, EvidenceSearch
from app.core.verdict import Verdict


class ClaimsState(TypedDict, total=False):
    """Text and claims, the state both graphs share and all the evidence-only graph carries."""

    input_text: str
    claims: List[Claim]


class AgentState(ClaimsState, total=False):
    """State of the full graph, where each node returns only the keys it updates."""

    # Claims trimmed to the Sources the report shows, the only ones the Verdict counts.
    shown_claims: List[Claim]
    sources: List[dict]
    evidence_search: EvidenceSearch
    judge_failures: int
    verdict: Optional[Verdict]
    medical_explanation: str
