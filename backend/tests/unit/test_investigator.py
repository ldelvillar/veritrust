"""Tests del nodo investigador con Europe PMC mockeado."""

from app.agents import investigator as investigator_module
from app.agents.investigator import investigator
from app.utils.europepmc import EvidenceRetrievalError


def test_returns_empty_without_translated_statements():
    update = investigator({"translated_statements": []})
    assert update == {"sources": [], "evidence_coverage": 0.0}


def test_collects_sources_and_full_coverage(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": f"hit for {query}", "url": f"https://x/{query}"}]

    monkeypatch.setattr(investigator_module, "search_evidence", fake_search)

    update = investigator(
        {"translated_statements": ["A", "B"], "extracted_statements": ["a", "b"]}
    )

    assert set(update.keys()) == {"sources", "evidence_coverage"}
    assert update["evidence_coverage"] == 1.0
    assert len(update["sources"]) == 2
    # La afirmación original se adjunta para contexto en la UI.
    assert update["sources"][0]["statement"] == "a"


def test_partial_coverage_when_some_statements_have_no_hits(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": "hit", "url": "https://x/1"}] if query == "A" else []

    monkeypatch.setattr(investigator_module, "search_evidence", fake_search)

    update = investigator({"translated_statements": ["A", "B"]})

    assert update["evidence_coverage"] == 0.5


def test_dedupes_sources_by_url(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": "same", "url": "https://x/dup"}]

    monkeypatch.setattr(investigator_module, "search_evidence", fake_search)

    update = investigator({"translated_statements": ["A", "B"]})

    assert len(update["sources"]) == 1


def test_total_outage_does_not_penalize_confidence(monkeypatch):
    def fake_search(query, *, max_results):
        raise EvidenceRetrievalError("down")

    monkeypatch.setattr(investigator_module, "search_evidence", fake_search)

    update = investigator({"translated_statements": ["A", "B"]})

    # Caída total del servicio: cobertura 1.0 (no se castiga el veredicto) y sin fuentes.
    assert update["sources"] == []
    assert update["evidence_coverage"] == 1.0
