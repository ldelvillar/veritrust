"""Tests del nodo investigador con las fuentes de evidencia mockeadas."""

import threading
from types import SimpleNamespace

from app.agents import investigator as investigator_module
from app.agents.investigator import investigator
from app.utils.evidence import EvidenceRetrievalError

_PROMPTS = SimpleNamespace(judge=SimpleNamespace(text="judge-prompt"))


def _patch_sources(monkeypatch, fake):
    """Sustituye las cuatro fuentes (Europe PMC, PubMed, openFDA y CIMA) por el doble."""
    monkeypatch.setattr(investigator_module, "search_europepmc", fake)
    monkeypatch.setattr(investigator_module, "search_pubmed", fake)
    monkeypatch.setattr(investigator_module, "search_openfda", fake)
    monkeypatch.setattr(investigator_module, "search_cima", fake)


def test_returns_empty_without_translated_statements():
    update = investigator({"translated_statements": []})
    assert update == {"sources": [], "evidence_coverage": 0.0}


def test_collects_sources_and_full_coverage(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": f"hit for {query}", "url": f"https://x/{query}"}]

    _patch_sources(monkeypatch, fake_search)

    update = investigator(
        {"translated_statements": ["A", "B"], "extracted_statements": ["a", "b"]}
    )

    assert set(update.keys()) == {"sources", "evidence_coverage"}
    assert update["evidence_coverage"] == 1.0
    # Ambas fuentes devuelven la misma URL por afirmación: se deduplica a una.
    assert len(update["sources"]) == 2
    # La afirmación original se adjunta para enlazar la fuente con su afirmación.
    assert update["sources"][0]["statements"] == [{"text": "a", "stance": None}]


def test_merges_distinct_hits_from_both_sources(monkeypatch):
    def fake_europepmc(query, *, max_results):
        return [{"title": "pmc", "url": "https://pmc/1"}]

    def fake_pubmed(query, *, max_results):
        return [{"title": "pubmed", "url": "https://pubmed/1"}]

    def fake_empty(query, *, max_results):
        return []

    monkeypatch.setattr(investigator_module, "search_europepmc", fake_europepmc)
    monkeypatch.setattr(investigator_module, "search_pubmed", fake_pubmed)
    monkeypatch.setattr(investigator_module, "search_openfda", fake_empty)
    monkeypatch.setattr(investigator_module, "search_cima", fake_empty)

    update = investigator(
        {"translated_statements": ["A"], "extracted_statements": ["a"]}
    )

    # Resultados distintos de cada fuente se conservan ambos para la misma afirmación.
    assert update["evidence_coverage"] == 1.0
    assert {source["url"] for source in update["sources"]} == {
        "https://pmc/1",
        "https://pubmed/1",
    }


def test_partial_coverage_when_some_statements_have_no_hits(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": "hit", "url": "https://x/1"}] if query == "A" else []

    _patch_sources(monkeypatch, fake_search)

    update = investigator({"translated_statements": ["A", "B"]})

    assert update["evidence_coverage"] == 0.5


def test_merges_statements_for_shared_url(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": "same", "url": "https://x/dup"}]

    _patch_sources(monkeypatch, fake_search)

    update = investigator(
        {"translated_statements": ["A", "B"], "extracted_statements": ["a", "b"]}
    )

    # Una misma fuente recuperada para dos afirmaciones queda enlazada a ambas.
    assert len(update["sources"]) == 1
    assert update["sources"][0]["statements"] == [
        {"text": "a", "stance": None},
        {"text": "b", "stance": None},
    ]


def test_total_outage_does_not_penalize_confidence(monkeypatch):
    def fake_search(query, *, max_results):
        raise EvidenceRetrievalError("down")

    _patch_sources(monkeypatch, fake_search)

    update = investigator({"translated_statements": ["A", "B"]})

    # Caída total del servicio: cobertura 1.0 (no se castiga el veredicto) y sin fuentes.
    assert update["sources"] == []
    assert update["evidence_coverage"] == 1.0


def test_one_source_down_still_uses_the_other(monkeypatch):
    def fake_europepmc(query, *, max_results):
        raise EvidenceRetrievalError("pmc down")

    def fake_pubmed(query, *, max_results):
        return [{"title": "pubmed", "url": "https://pubmed/1"}]

    def fake_empty(query, *, max_results):
        return []

    monkeypatch.setattr(investigator_module, "search_europepmc", fake_europepmc)
    monkeypatch.setattr(investigator_module, "search_pubmed", fake_pubmed)
    monkeypatch.setattr(investigator_module, "search_openfda", fake_empty)
    monkeypatch.setattr(investigator_module, "search_cima", fake_empty)

    update = investigator({"translated_statements": ["A"]})

    # Una fuente caída no invalida la afirmación: las demás sí aportan evidencia.
    assert update["evidence_coverage"] == 1.0
    assert [source["url"] for source in update["sources"]] == ["https://pubmed/1"]


def test_blank_translations_skip_lookups(monkeypatch):
    called = False

    def fake_search(query, *, max_results):
        nonlocal called
        called = True
        return []

    _patch_sources(monkeypatch, fake_search)

    # Traducciones en blanco (relleno): no hay nada que consultar.
    update = investigator({"translated_statements": ["", "  "]})

    assert update == {"sources": [], "evidence_coverage": 0.0}
    assert called is False


def test_uses_focused_search_query_over_translation(monkeypatch):
    queried: list[str] = []

    def fake_search(query, *, max_results):
        queried.append(query)
        return [{"title": "hit", "url": f"https://x/{query}"}]

    _patch_sources(monkeypatch, fake_search)

    investigator(
        {
            "translated_statements": ["full translated sentence"],
            "search_queries": ['"vitamin C" AND "common cold"'],
            "extracted_statements": ["vitamina C y resfriado"],
        }
    )

    # Se consulta con la query enfocada, no con la frase completa (en ambas fuentes).
    assert set(queried) == {'"vitamin C" AND "common cold"'}


def test_falls_back_to_translation_when_query_blank(monkeypatch):
    queried: list[str] = []

    def fake_search(query, *, max_results):
        queried.append(query)
        return [{"title": "hit", "url": f"https://x/{query}"}]

    _patch_sources(monkeypatch, fake_search)

    # Query en blanco (relleno del extractor): se recurre a la traducción completa.
    investigator(
        {
            "translated_statements": ["A-en", "B-en"],
            "search_queries": ['"focused"', "  "],
        }
    )

    assert set(queried) == {'"focused"', "B-en"}


def test_evidence_gate_filters_sources_and_records_stance(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": "t", "url": f"https://x/{query}", "abstract": "abs"}]

    _patch_sources(monkeypatch, fake_search)

    # El juez solo conserva la evidencia de la afirmación A, con su postura.
    def fake_judge(prompt_text, claim, hits):
        return [{**h, "stance": "contradicts"} for h in hits] if claim == "A-en" else []

    monkeypatch.setattr(investigator_module, "judge_evidence", fake_judge)

    update = investigator(
        {
            "translated_statements": ["A-en", "B-en"],
            "extracted_statements": ["a", "b"],
        },
        _PROMPTS,
    )

    # Solo cuenta la afirmación con evidencia relevante; el abstract no se persiste
    # y la postura se guarda dentro de la afirmación enlazada.
    assert update["evidence_coverage"] == 0.5
    assert len(update["sources"]) == 1
    assert update["sources"][0]["statements"] == [
        {"text": "a", "stance": "contradicts"}
    ]
    assert "abstract" not in update["sources"][0]
    assert "stance" not in update["sources"][0]


def test_runs_lookups_concurrently(monkeypatch):
    # La barrera solo se libera si las 9 búsquedas (3 afirmaciones × 3 fuentes de
    # literatura; sin fármaco no se consulta CIMA) coinciden en el tiempo; en
    # ejecución secuencial la primera espera agotaría el timeout y la rompería.
    barrier = threading.Barrier(9, timeout=5)

    def fake_search(query, *, max_results):
        barrier.wait()
        return [{"title": query, "url": f"https://x/{query}"}]

    _patch_sources(monkeypatch, fake_search)

    update = investigator({"translated_statements": ["A", "B", "C"]})

    assert update["evidence_coverage"] == 1.0
    assert len(update["sources"]) == 3


def test_cima_queried_with_drug_term_not_english_query(monkeypatch):
    topic_queried: list[str] = []
    cima_queried: list[str] = []

    def fake_topic(query, *, max_results):
        topic_queried.append(query)
        return []

    def fake_cima(query, *, max_results):
        cima_queried.append(query)
        return [{"title": "ficha", "url": "https://cima/1"}]

    monkeypatch.setattr(investigator_module, "search_europepmc", fake_topic)
    monkeypatch.setattr(investigator_module, "search_pubmed", fake_topic)
    monkeypatch.setattr(investigator_module, "search_openfda", fake_topic)
    monkeypatch.setattr(investigator_module, "search_cima", fake_cima)

    update = investigator(
        {
            "translated_statements": ["ibuprofen cures cancer"],
            "search_queries": ['"ibuprofen" AND "cancer"'],
            "extracted_statements": ["el ibuprofeno cura el cáncer"],
            "drug_terms": ["ibuprofeno"],
        }
    )

    # CIMA usa el término en español; la literatura, la query enfocada en inglés.
    assert cima_queried == ["ibuprofeno"]
    assert set(topic_queried) == {'"ibuprofen" AND "cancer"'}
    assert [source["url"] for source in update["sources"]] == ["https://cima/1"]


def test_cima_skipped_when_no_drug_term(monkeypatch):
    cima_called = False

    def fake_topic(query, *, max_results):
        return []

    def fake_cima(query, *, max_results):
        nonlocal cima_called
        cima_called = True
        return []

    monkeypatch.setattr(investigator_module, "search_europepmc", fake_topic)
    monkeypatch.setattr(investigator_module, "search_pubmed", fake_topic)
    monkeypatch.setattr(investigator_module, "search_openfda", fake_topic)
    monkeypatch.setattr(investigator_module, "search_cima", fake_cima)

    investigator(
        {
            "translated_statements": ["a diet claim"],
            "search_queries": ['"diet"'],
            "extracted_statements": ["una dieta sana"],
            "drug_terms": [""],
        }
    )

    # Sin fármaco nombrado, CIMA no se consulta.
    assert cima_called is False


def test_judge_runs_concurrently(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": query, "url": f"https://x/{query}", "abstract": "abs"}]

    _patch_sources(monkeypatch, fake_search)

    # La barrera solo se libera si los 3 juicios coinciden en el tiempo; en ejecución
    # secuencial el primero agotaría el timeout de la barrera y rompería la prueba.
    barrier = threading.Barrier(3, timeout=5)

    def fake_judge(prompt_text, claim, hits):
        barrier.wait()
        return [{**h, "stance": "supports"} for h in hits]

    monkeypatch.setattr(investigator_module, "judge_evidence", fake_judge)

    update = investigator(
        {
            "translated_statements": ["A", "B", "C"],
            "extracted_statements": ["a", "b", "c"],
        },
        _PROMPTS,
    )

    assert update["evidence_coverage"] == 1.0
    assert len(update["sources"]) == 3


def test_parallel_judge_isolates_one_failure(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": query, "url": f"https://x/{query}", "abstract": "abs"}]

    _patch_sources(monkeypatch, fake_search)

    # El juez casca para una sola afirmación; en paralelo no debe arrastrar al resto.
    def fake_judge(prompt_text, claim, hits):
        if claim == "B-en":
            raise RuntimeError("judge down")
        return [{**h, "stance": "supports"} for h in hits]

    monkeypatch.setattr(investigator_module, "judge_evidence", fake_judge)

    update = investigator(
        {
            "translated_statements": ["A-en", "B-en"],
            "extracted_statements": ["a", "b"],
        },
        _PROMPTS,
    )

    # La afirmación cuyo juez falló conserva su evidencia (falla en abierto) y la sana
    # se juzga con normalidad: ambas cuentan para la cobertura.
    assert update["evidence_coverage"] == 1.0
    by_url = {source["url"]: source for source in update["sources"]}
    assert set(by_url) == {"https://x/A-en", "https://x/B-en"}
    # La afirmación sana no se ve afectada por el fallo de la otra.
    assert by_url["https://x/A-en"]["statements"] == [
        {"text": "a", "stance": "supports"}
    ]
    # La que falló conserva la fuente sin postura juzgada.
    assert by_url["https://x/B-en"]["statements"] == [{"text": "b", "stance": None}]
