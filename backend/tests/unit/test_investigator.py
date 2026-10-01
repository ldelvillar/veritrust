"""Tests del nodo investigador con las fuentes de evidencia mockeadas."""

import threading
from types import SimpleNamespace

from app.agents import investigator as investigator_module
from app.agents.investigator import (
    EVIDENCE_MAX_STATEMENTS,
    gather_evidence,
    investigator,
)
from app.core.claim import Claim, EvidenceSearch
from app.utils.evidence import EvidenceRetrievalError

_PROMPTS = SimpleNamespace(judge=SimpleNamespace(text="judge-prompt"))
_NOTHING_SEARCHED = EvidenceSearch(total=0, searched=0, covered=0, outage=False)


def _claims(
    translations: list[str],
    *,
    originals: list[str] | None = None,
    queries: list[str] | None = None,
    drug_terms: list[str] | None = None,
) -> list[Claim]:
    """Afirmaciones ya traducidas, tal y como las deja el traductor en el estado."""
    empty = [""] * len(translations)
    return [
        Claim(index=index, text=text, text_en=text_en, query=query, drug_term=drug)
        for index, (text, text_en, query, drug) in enumerate(
            zip(
                originals if originals is not None else empty,
                translations,
                queries or empty,
                drug_terms or empty,
                strict=True,
            )
        )
    ]


def _search(total: int, covered: int, *, outage: bool = False) -> EvidenceSearch:
    """Recuento esperado cuando la cota no recorta ninguna afirmación."""
    return EvidenceSearch(total=total, searched=total, covered=covered, outage=outage)


def _patch_sources(monkeypatch, fake):
    """Sustituye las cuatro fuentes (Europe PMC, PubMed, openFDA y CIMA) por el doble."""
    monkeypatch.setattr(investigator_module, "search_europepmc", fake)
    monkeypatch.setattr(investigator_module, "search_pubmed", fake)
    monkeypatch.setattr(investigator_module, "search_openfda", fake)
    monkeypatch.setattr(investigator_module, "search_cima", fake)


def _patch_judge(monkeypatch, judge):
    """Sustituye al juez por un doble que recibe prompt, afirmación y evidencia."""
    monkeypatch.setattr(investigator_module, "judge_stances", judge)


def _judge_all(stance):
    """Juez que da la misma postura a todas las fuentes candidatas."""
    return lambda prompt, claim, evidence: (stance,) * len(evidence)


def test_returns_empty_without_claims():
    update = investigator({"claims": []})
    assert update == {
        "claims": [],
        "shown_claims": [],
        "sources": [],
        "evidence_search": _NOTHING_SEARCHED,
        "judge_failures": 0,
    }


def test_collects_sources_and_full_coverage(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": f"hit for {query}", "url": f"https://x/{query}"}]

    _patch_sources(monkeypatch, fake_search)

    update = investigator({"claims": _claims(["A", "B"], originals=["a", "b"])})

    assert set(update.keys()) == {
        "claims",
        "shown_claims",
        "sources",
        "evidence_search",
        "judge_failures",
    }
    assert update["evidence_search"] == _search(2, covered=2)
    # Las cuatro fuentes devuelven la misma URL por afirmación: se deduplica a una.
    assert len(update["sources"]) == 2
    assert update["sources"][0]["statements"] == [
        {"claim_index": 0, "text": "a", "stance": None}
    ]


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

    update = investigator({"claims": _claims(["A"], originals=["a"])})

    # Resultados distintos de cada fuente se conservan ambos para la misma afirmación.
    assert update["evidence_search"] == _search(1, covered=1)
    assert {source["url"] for source in update["sources"]} == {
        "https://pmc/1",
        "https://pubmed/1",
    }


def test_cap_drops_extra_statements_and_counts_them_uncovered(monkeypatch):
    queried: set[str] = set()

    def fake_search(query, *, max_results):
        queried.add(query)
        return [{"title": query, "url": f"https://x/{query}"}]

    _patch_sources(monkeypatch, fake_search)

    total = EVIDENCE_MAX_STATEMENTS + 2
    statements = [f"S{i}" for i in range(total)]
    update = investigator({"claims": _claims(statements)})

    # Solo se buscan las primeras N afirmaciones; las recortadas cuentan como no cubiertas.
    assert queried == set(statements[:EVIDENCE_MAX_STATEMENTS])
    assert update["evidence_search"] == EvidenceSearch(
        total=total,
        searched=EVIDENCE_MAX_STATEMENTS,
        covered=EVIDENCE_MAX_STATEMENTS,
        outage=False,
    )
    assert len(update["sources"]) == EVIDENCE_MAX_STATEMENTS


def test_total_outage_is_reported_as_an_outage(monkeypatch):
    def fake_search(query, *, max_results):
        raise EvidenceRetrievalError("down")

    _patch_sources(monkeypatch, fake_search)

    update = investigator({"claims": _claims(["A", "B"])})

    # Caída total del servicio: se informa como corte, no como falta de literatura.
    assert update["sources"] == []
    assert update["evidence_search"] == _search(2, covered=0, outage=True)


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

    update = investigator({"claims": _claims(["A"])})

    # Una fuente caída no invalida la afirmación: las demás sí aportan evidencia.
    assert update["evidence_search"] == _search(1, covered=1)
    assert [source["url"] for source in update["sources"]] == ["https://pubmed/1"]


def test_blank_translations_skip_lookups(monkeypatch):
    called = False

    def fake_search(query, *, max_results):
        nonlocal called
        called = True
        return []

    _patch_sources(monkeypatch, fake_search)

    # Traducciones en blanco (relleno): no hay nada que consultar.
    claims = gather_evidence(_claims(["", "  "]))

    assert [claim.outcome for claim in claims] == ["unsearchable", "unsearchable"]
    assert called is False


def test_runs_lookups_concurrently(monkeypatch):
    # La barrera solo se libera si las 9 búsquedas (3 afirmaciones × 3 fuentes de
    # literatura; sin fármaco no se consulta CIMA) coinciden en el tiempo; en
    # ejecución secuencial la primera espera agotaría el timeout y la rompería.
    barrier = threading.Barrier(9, timeout=5)

    def fake_search(query, *, max_results):
        barrier.wait()
        return [{"title": query, "url": f"https://x/{query}"}]

    _patch_sources(monkeypatch, fake_search)

    update = investigator({"claims": _claims(["A", "B", "C"])})

    assert update["evidence_search"] == _search(3, covered=3)
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
            "claims": _claims(
                ["ibuprofen cures cancer"],
                originals=["el ibuprofeno cura el cáncer"],
                queries=['"ibuprofen" AND "cancer"'],
                drug_terms=["ibuprofeno"],
            )
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
            "claims": _claims(
                ["a diet claim"],
                originals=["una dieta sana"],
                queries=['"diet"'],
                drug_terms=[""],
            )
        }
    )

    # Sin fármaco nombrado, CIMA no se consulta.
    assert cima_called is False


def test_judge_receives_the_english_claim_or_its_query(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": query, "url": f"https://x/{query}"}]

    _patch_sources(monkeypatch, fake_search)
    judged: list[str] = []

    def fake_judge(prompt, claim, evidence):
        judged.append(claim)
        return ("supports",) * len(evidence)

    _patch_judge(monkeypatch, fake_judge)

    gather_evidence(
        _claims(["A-en", ""], originals=["a", "b"], queries=['"qa"', '"qb"']),
        _PROMPTS,
    )

    # Sin traducción, el juez recibe la consulta como respaldo.
    assert sorted(judged) == ['"qb"', "A-en"]


def test_judge_runs_concurrently(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": query, "url": f"https://x/{query}", "abstract": "abs"}]

    _patch_sources(monkeypatch, fake_search)

    # La barrera solo se libera si los 3 juicios coinciden en el tiempo; en ejecución
    # secuencial el primero agotaría el timeout de la barrera y rompería la prueba.
    barrier = threading.Barrier(3, timeout=5)

    def fake_judge(prompt, claim, evidence):
        barrier.wait()
        return ("supports",) * len(evidence)

    _patch_judge(monkeypatch, fake_judge)

    update = investigator(
        {"claims": _claims(["A", "B", "C"], originals=["a", "b", "c"])}, _PROMPTS
    )

    assert update["evidence_search"] == _search(3, covered=3)
    assert len(update["sources"]) == 3


def test_parallel_judge_isolates_one_failure(monkeypatch):
    def fake_search(query, *, max_results):
        return [{"title": query, "url": f"https://x/{query}", "abstract": "abs"}]

    _patch_sources(monkeypatch, fake_search)

    # El juez falla para una sola afirmación; en paralelo no debe arrastrar al resto.
    def fake_judge(prompt, claim, evidence):
        return None if claim == "B-en" else ("supports",) * len(evidence)

    _patch_judge(monkeypatch, fake_judge)

    update = investigator(
        {"claims": _claims(["A-en", "B-en"], originals=["a", "b"])}, _PROMPTS
    )

    # La afirmación cuyo juez falló conserva su evidencia (falla en abierto) y la sana
    # se juzga con normalidad: ambas cuentan para la cobertura.
    assert update["evidence_search"] == _search(2, covered=2)
    assert [claim.outcome for claim in update["claims"]] == ["judged", "unjudged"]
    by_url = {source["url"]: source for source in update["sources"]}
    assert by_url["https://x/A-en"]["statements"] == [
        {"claim_index": 0, "text": "a", "stance": "supports"}
    ]
    assert by_url["https://x/B-en"]["statements"] == [
        {"claim_index": 1, "text": "b", "stance": None}
    ]


def test_reports_judge_failures_when_sources_go_unjudged(monkeypatch):
    """El juez falla en abierto: las fuentes sin postura deben quedar contabilizadas."""

    def fake_search(query, max_results):
        return [{"url": "u1", "title": "T1", "abstract": "A1"}]

    _patch_sources(monkeypatch, fake_search)
    _patch_judge(monkeypatch, lambda prompt, claim, evidence: None)

    update = investigator(
        {"claims": _claims(["Claim in English"], originals=["Afirmación"])}, _PROMPTS
    )

    assert update["judge_failures"] == 1


def test_no_judge_failures_when_every_source_is_judged(monkeypatch):
    def fake_search(query, max_results):
        return [{"url": "u1", "title": "T1", "abstract": "A1"}]

    _patch_sources(monkeypatch, fake_search)
    _patch_judge(monkeypatch, _judge_all("supports"))

    update = investigator(
        {"claims": _claims(["Claim in English"], originals=["Afirmación"])}, _PROMPTS
    )

    assert update["judge_failures"] == 0


def test_gather_evidence_marks_unjudged_and_unavailable_claims(monkeypatch):
    def fake_search(query, *, max_results):
        if query == "B-en":
            raise EvidenceRetrievalError("down")
        return [{"title": "t", "url": "https://x/a"}]

    _patch_sources(monkeypatch, fake_search)
    _patch_judge(monkeypatch, lambda prompt, claim, evidence: None)

    claims = gather_evidence(_claims(["A-en", "B-en"], originals=["a", "b"]), _PROMPTS)

    # Todas las fuentes cayeron para la segunda afirmación: sin evidencia disponible.
    assert [claim.outcome for claim in claims] == ["unjudged", "unavailable"]
    assert [item.url for item in claims[0].evidence] == ["https://x/a"]
    assert claims[1].evidence == ()


def test_gather_evidence_leaves_claims_beyond_the_cap_unsearched(monkeypatch):
    _patch_sources(monkeypatch, lambda query, *, max_results: [])

    statements = [f"S{i}" for i in range(EVIDENCE_MAX_STATEMENTS + 2)]
    claims = gather_evidence(_claims(statements))

    # Sin fuentes que juzgar, la afirmación buscada cuenta como juzgada.
    assert [claim.outcome for claim in claims] == [
        "judged"
    ] * EVIDENCE_MAX_STATEMENTS + [
        "unsearched",
        "unsearched",
    ]


def test_gather_evidence_is_empty_without_claims():
    assert gather_evidence([]) == []
