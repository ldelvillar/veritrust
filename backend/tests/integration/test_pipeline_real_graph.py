"""Tests del grafo real de cuatro agentes con solo los servicios externos simulados."""

from types import SimpleNamespace

import httpx
import pytest

import app.agents.extractor as extractor_module
import app.agents.health_expert as health_module
import app.agents.investigator as investigator_module
import app.agents.relevance as relevance_module
import app.agents.translator as translator_module
import app.worker as worker_module
from app.agents.errors import OllamaConnectionError, ainvoke_graph
from app.agents.main import create_evidence_graph, create_graph
from app.core.analysis_lifecycle import AnalysisFailure, TextContent
from app.core.config import Settings
from app.prompts.agents import PromptItem, Prompts, load_prompts
from app.schemas.errors import ErrorCode
from app.utils.evidence import EvidenceRetrievalError
from tests.support.lifecycle import FakeRun

PIPELINE = {"provider": "test", "models": {}, "prompts": {"judge": "v0"}}


@pytest.fixture
def prompts():
    return Prompts(
        extractor=PromptItem(version="v1", text="extractor"),
        translator=PromptItem(version="v1", text="translator"),
        judge=PromptItem(version="v1", text="judge"),
        # El experto renderiza las plantillas del YAML, así que aquí va el prompt real.
        health_expert=load_prompts().health_expert,
    )


def _initial_state(text: str) -> dict:
    """Replica el estado inicial exacto que el worker envía al grafo."""
    return {
        "input_text": text,
        "claims": [],
        "sources": [],
        "medical_explanation": "",
    }


def _stub_extractor(monkeypatch, statements, queries, drug_terms=None):
    """Simula solo la llamada al LLM del extractor; el resto del agente es real."""

    class _Chain:
        def invoke(self, payload):
            return SimpleNamespace(
                statements=statements,
                search_queries=queries,
                drug_terms=drug_terms or [],
            )

    monkeypatch.setattr(
        extractor_module,
        "get_extractor_chain",
        lambda prompt_text, model=None: _Chain(),
    )


def _stub_translator(monkeypatch, translations):
    """Simula solo la llamada al LLM del traductor; el padding real sigue activo."""

    class _Chain:
        def invoke(self, payload):
            return SimpleNamespace(translations=translations)

    monkeypatch.setattr(
        translator_module,
        "get_translator_chain",
        lambda prompt_text, model=None: _Chain(),
    )


def _guard_translator(monkeypatch):
    """Falla el test si el traductor llega a invocar su LLM."""

    def _should_not_be_called(prompt_text):
        raise AssertionError("El traductor no debe invocar su LLM sin afirmaciones")

    monkeypatch.setattr(
        translator_module, "get_translator_chain", _should_not_be_called
    )


def _stub_health(monkeypatch, llm_error=None):
    """Simula el LLM del experto; devuelve lo que este recibe."""
    captured: dict = {"human": None}

    class _FakeLLM:
        def invoke(self, messages):
            if llm_error is not None:
                raise llm_error
            captured["human"] = messages[-1].content
            return SimpleNamespace(content="Informe médico integrado")

    monkeypatch.setattr(health_module, "get_health_expert_llm", lambda: _FakeLLM())
    return captured


def _guard_health(monkeypatch):
    """Falla el test si el experto llega a instanciar su LLM."""

    def _fail(*args, **kwargs):
        raise AssertionError("No debe usarse el LLM sin afirmaciones")

    monkeypatch.setattr(health_module, "get_health_expert_llm", _fail)


def _stub_sources(monkeypatch, europepmc=None, pubmed=None, openfda=None, cima=None):
    """Sustituye las cuatro fuentes de evidencia; None equivale a no devolver nada."""

    def _as_search(impl):
        if impl is None:
            return lambda query, max_results=3: []
        return impl

    monkeypatch.setattr(investigator_module, "search_europepmc", _as_search(europepmc))
    monkeypatch.setattr(investigator_module, "search_pubmed", _as_search(pubmed))
    monkeypatch.setattr(investigator_module, "search_openfda", _as_search(openfda))
    monkeypatch.setattr(investigator_module, "search_cima", _as_search(cima))


def _failing_search(query, max_results=3):
    raise EvidenceRetrievalError("fuente caída")


def _stub_judge(monkeypatch, stance="inconclusive", record=None):
    """Simula solo el LLM del juez; el filtrado real sigue activo."""

    class _Chain:
        def invoke(self, payload):
            if record is not None:
                record.append(payload["claim"])
            # Una postura por fuente candidata (una línea numerada por fuente).
            candidates = len(payload["sources"].splitlines())
            return SimpleNamespace(stances=[stance] * candidates)

    monkeypatch.setattr(
        relevance_module,
        "get_relevance_chain",
        lambda prompt_text, model=None: _Chain(),
    )


def test_full_pipeline_carries_claims_from_extraction_to_verdict(monkeypatch, prompts):
    """Las afirmaciones fluyen extractor→traductor→investigador→experto sin perderse."""
    _stub_extractor(
        monkeypatch,
        statements=[
            "El ibuprofeno cura la gripe",
            "La vitamina C previene el resfriado",
        ],
        queries=['"ibuprofen" AND "flu"', '"vitamin C" AND "cold"'],
        drug_terms=["ibuprofeno", ""],
    )
    _stub_translator(
        monkeypatch, ["Ibuprofen cures the flu", "Vitamin C prevents the common cold"]
    )
    captured = _stub_health(monkeypatch)

    def fake_europepmc(query, max_results=3):
        return [
            {
                "title": f"Estudio sobre {query}",
                "url": f"https://europepmc.org/{abs(hash(query))}",
                "source": "BMJ",
                "year": "2021",
                "abstract": "Resumen.",
            }
        ]

    def fake_cima(drug, max_results=3):
        return [
            {
                "title": f"Ficha técnica de {drug}",
                "url": f"https://cima.aemps.es/{drug}",
                "source": "AEMPS",
                "year": "2020",
                "abstract": "Ficha.",
            }
        ]

    # PubMed y openFDA caídos: el pipeline debe seguir con las fuentes vivas.
    _stub_sources(
        monkeypatch,
        europepmc=fake_europepmc,
        pubmed=_failing_search,
        openfda=_failing_search,
        cima=fake_cima,
    )
    judged: list[str] = []
    _stub_judge(monkeypatch, stance="supports", record=judged)

    graph = create_graph(prompts)
    result = graph.invoke(_initial_state("El ibuprofeno cura la gripe..."))

    # El juez evalúa las traducciones, nunca el texto original en español.
    assert judged == [
        "Ibuprofen cures the flu",
        "Vitamin C prevents the common cold",
    ]
    verdict = result["verdict"]
    # Los veredictos por afirmación conservan el texto original en español.
    assert [c.text for c in verdict.claims] == [
        "El ibuprofeno cura la gripe",
        "La vitamina C previene el resfriado",
    ]
    assert verdict.label == "verdadera"
    # Evidencia a favor (2 y 1 fuentes): falsedad media = (1/4 + 1/3) / 2 = 7/24.
    assert verdict.confidence == pytest.approx(17 / 24)
    assert verdict.evidence_coverage == 1.0
    assert result["medical_explanation"] == "Informe médico integrado"

    # Las fuentes fusionadas enlazan cada afirmación original que respaldan.
    urls = {s["url"] for s in result["sources"]}
    assert "https://cima.aemps.es/ibuprofeno" in urls
    linked = {st["text"] for s in result["sources"] for st in s["statements"]}
    assert linked == {
        "El ibuprofeno cura la gripe",
        "La vitamina C previene el resfriado",
    }
    # El informe del experto se fundamenta en las fuentes recuperadas.
    assert "Estudio sobre" in captured["human"]


async def test_pipeline_with_no_claims_ends_as_no_medical_claims_row(
    monkeypatch, prompts
):
    """Texto sin afirmaciones: nada de LLMs aguas abajo y fila failed NO_MEDICAL_CLAIMS."""
    _stub_extractor(monkeypatch, statements=[], queries=[], drug_terms=[])
    _guard_translator(monkeypatch)
    _guard_health(monkeypatch)

    def _no_search(query, max_results=3):
        raise AssertionError("El investigador no debe buscar sin afirmaciones")

    _stub_sources(
        monkeypatch,
        europepmc=_no_search,
        pubmed=_no_search,
        openfda=_no_search,
        cima=_no_search,
    )

    ctx = {"verification_system": create_graph(prompts), "pipeline": PIPELINE}
    with pytest.raises(AnalysisFailure) as failure:
        await worker_module.analyse(
            ctx, FakeRun(TextContent("Hoy hace un día soleado en Madrid"))
        )

    assert failure.value.code == ErrorCode.NO_MEDICAL_CLAIMS


async def test_pipeline_with_explanation_disabled_still_completes(monkeypatch, prompts):
    """Sin informe del experto el veredicto se guarda igual; nunca es NO_MEDICAL_CLAIMS."""
    _stub_extractor(
        monkeypatch,
        statements=["La vitamina C previene el resfriado"],
        queries=['"vitamin C" AND "cold"'],
    )
    _stub_translator(monkeypatch, ["Vitamin C prevents the common cold"])
    _stub_health(monkeypatch)
    monkeypatch.setattr(
        health_module,
        "get_settings",
        lambda: Settings(health_expert_explanation_enabled=False),
    )

    def fake_europepmc(query, max_results=3):
        return [
            {
                "title": "Vitamin C for preventing colds",
                "url": "https://europepmc.org/vitc",
                "abstract": "Resumen.",
            }
        ]

    _stub_sources(monkeypatch, europepmc=fake_europepmc)
    _stub_judge(monkeypatch, stance="contradicts")

    ctx = {"verification_system": create_graph(prompts), "pipeline": PIPELINE}
    completion = await worker_module.analyse(
        ctx, FakeRun(TextContent("La vitamina C previene el resfriado"))
    )

    assert completion.verdict.label == "falsa"
    assert completion.explanation is None


def test_missing_search_queries_fall_back_to_translated_claims(monkeypatch, prompts):
    """Si el extractor devuelve menos consultas que afirmaciones, se busca con la traducción."""
    _stub_extractor(
        monkeypatch,
        statements=["Afirmación uno", "Afirmación dos"],
        queries=['"query one"'],
        drug_terms=[],
    )
    _stub_translator(monkeypatch, ["Claim one EN", "Claim two EN"])
    _stub_health(monkeypatch)
    _stub_judge(monkeypatch)

    europepmc_queries: list[str] = []

    def recording_europepmc(query, max_results=3):
        europepmc_queries.append(query)
        return [
            {
                "title": f"Hit {query}",
                "url": f"https://europepmc.org/{len(europepmc_queries)}",
                "abstract": "Resumen.",
            }
        ]

    _stub_sources(monkeypatch, europepmc=recording_europepmc)

    graph = create_graph(prompts)
    result = graph.invoke(_initial_state("Texto"))

    # La afirmación sin consulta enfocada se investiga con su traducción al inglés.
    # Las búsquedas corren en un pool de hilos, así que el orden no está garantizado.
    assert set(europepmc_queries) == {'"query one"', "Claim two EN"}
    assert result["verdict"].evidence_coverage == 1.0


def test_empty_translator_output_still_produces_a_verdict(monkeypatch, prompts):
    """Un traductor que devuelve una lista vacía no debe romper los agentes siguientes."""
    _stub_extractor(
        monkeypatch,
        statements=["Afirmación uno", "Afirmación dos"],
        queries=['"query one"', '"query two"'],
        drug_terms=[],
    )
    _stub_translator(monkeypatch, [])
    _stub_health(monkeypatch)
    judged_claims: list[str] = []
    _stub_judge(monkeypatch, stance="supports", record=judged_claims)

    def fake_europepmc(query, max_results=3):
        return [
            {"title": f"Hit {query}", "url": f"https://e.org/{query}", "abstract": "R."}
        ]

    _stub_sources(monkeypatch, europepmc=fake_europepmc)

    graph = create_graph(prompts)
    result = graph.invoke(_initial_state("Texto"))

    # El traductor real rellena con cadenas vacías y el pipeline sigue en pie.
    assert [claim.text_en for claim in result["claims"]] == ["", ""]
    # Sin traducción, el juez de relevancia recibe la consulta como respaldo.
    assert judged_claims == ['"query one"', '"query two"']
    assert result["verdict"].label == "verdadera"
    assert len(result["verdict"].claims) == 2


def test_total_evidence_outage_does_not_penalize_confidence(monkeypatch, prompts):
    """Con todas las fuentes caídas la cobertura es desconocida: fallo nuestro, no del contenido."""
    _stub_extractor(
        monkeypatch,
        statements=["Afirmación uno"],
        queries=['"query one"'],
        drug_terms=[],
    )
    _stub_translator(monkeypatch, ["Claim one EN"])
    captured = _stub_health(monkeypatch)
    _stub_judge(monkeypatch)
    _stub_sources(
        monkeypatch,
        europepmc=_failing_search,
        pubmed=_failing_search,
        openfda=_failing_search,
    )

    graph = create_graph(prompts)
    result = graph.invoke(_initial_state("Texto"))

    assert result["sources"] == []
    assert result["verdict"].evidence_coverage is None
    # Sin fuentes no hay postura: incierta, y el corte no atenúa.
    assert result["verdict"].label == "incierta"
    assert result["verdict"].confidence == pytest.approx(0.5)
    # El experto recibe la instrucción de no inventar referencias.
    assert "No se hallaron fuentes" in captured["human"]


async def test_total_outage_beyond_the_cap_reports_unknown_coverage(
    monkeypatch, prompts
):
    """Con todas las fuentes caídas y más afirmaciones que la cota, la cobertura es desconocida."""
    _stub_extractor(
        monkeypatch,
        statements=[f"Afirmación {i}" for i in range(10)],
        queries=[f'"query {i}"' for i in range(10)],
        drug_terms=[],
    )
    _stub_translator(monkeypatch, [f"Claim {i} EN" for i in range(10)])
    _stub_health(monkeypatch)
    _stub_judge(monkeypatch)
    _stub_sources(
        monkeypatch,
        europepmc=_failing_search,
        pubmed=_failing_search,
        openfda=_failing_search,
    )

    ctx = {"verification_system": create_graph(prompts), "pipeline": PIPELINE}
    completion = await worker_module.analyse(ctx, FakeRun(TextContent("Texto")))

    # No se buscó nada con éxito: el informe no puede mostrar un 80 % de cobertura.
    assert completion.verdict.evidence_coverage is None
    # Solo penalizan las 2 afirmaciones que la cota dejó sin buscar: 0.5 × (1 − 0.25 × 0.2).
    assert completion.verdict.confidence == pytest.approx(0.475)


def test_partial_evidence_coverage_attenuates_confidence(monkeypatch, prompts):
    """La afirmación sin literatura reduce la cobertura y esta atenúa la confianza final."""
    _stub_extractor(
        monkeypatch,
        statements=["Afirmación uno", "Afirmación dos"],
        queries=['"query one"', '"query two"'],
        drug_terms=[],
    )
    _stub_translator(monkeypatch, ["Claim one EN", "Claim two EN"])
    _stub_health(monkeypatch)
    _stub_judge(monkeypatch)

    def only_first_claim(query, max_results=3):
        if query == '"query one"':
            return [{"title": "Hit", "url": "https://e.org/1", "abstract": "R."}]
        return []

    _stub_sources(monkeypatch, europepmc=only_first_claim)

    graph = create_graph(prompts)
    result = graph.invoke(_initial_state("Texto"))

    assert result["verdict"].evidence_coverage == 0.5
    # Valor esperado independiente: 0.5 × (1 − 0.25 × (1 − 0.5)) = 0.4375.
    assert result["verdict"].confidence == pytest.approx(0.4375)
    assert result["verdict"].confidence < 0.5


def test_judge_rejecting_all_sources_leaves_claim_uncovered(monkeypatch, prompts):
    """Evidencia hallada pero irrelevante: el juez la descarta y la cobertura cae a 0."""
    _stub_extractor(
        monkeypatch, statements=["Afirmación"], queries=['"q"'], drug_terms=[]
    )
    _stub_translator(monkeypatch, ["Claim EN"])
    _stub_health(monkeypatch)
    _stub_judge(monkeypatch, stance="unrelated")

    def fake_europepmc(query, max_results=3):
        return [{"title": "Otro tema", "url": "https://e.org/x", "abstract": "R."}]

    _stub_sources(monkeypatch, europepmc=fake_europepmc)

    graph = create_graph(prompts)
    result = graph.invoke(_initial_state("Texto"))

    # El filtrado real del juez vacía las fuentes y penaliza al máximo la confianza.
    assert result["sources"] == []
    assert result["verdict"].evidence_coverage == 0.0
    assert result["verdict"].confidence == pytest.approx(0.5 * 0.75)


async def test_midgraph_transport_failure_surfaces_with_partial_stages(
    monkeypatch, prompts
):
    """Ollama caído en el experto: error tipado y solo las etapas previas completadas."""
    _stub_extractor(
        monkeypatch, statements=["Afirmación"], queries=['"q"'], drug_terms=[]
    )
    _stub_translator(monkeypatch, ["Claim EN"])
    _stub_health(monkeypatch, llm_error=httpx.ConnectError("ollama down"))
    _stub_judge(monkeypatch)
    _stub_sources(monkeypatch)

    stages: list[str] = []

    async def on_stage(node: str) -> None:
        stages.append(node)

    graph = create_graph(prompts)
    with pytest.raises(OllamaConnectionError):
        await ainvoke_graph(graph, _initial_state("Texto"), on_stage=on_stage)

    # El experto nunca terminó: las etapas reflejan el progreso parcial real.
    assert stages == ["extractor", "translator", "investigator"]


async def test_worker_maps_real_graph_transport_failure_to_connection_row(
    monkeypatch, prompts
):
    """La caída de Ollama dentro del grafo real acaba como fila failed CONNECTION."""
    _stub_extractor(
        monkeypatch, statements=["Afirmación"], queries=['"q"'], drug_terms=[]
    )
    _stub_translator(monkeypatch, ["Claim EN"])
    _stub_health(monkeypatch, llm_error=httpx.ConnectError("ollama down"))
    _stub_judge(monkeypatch)
    _stub_sources(monkeypatch)

    ctx = {"verification_system": create_graph(prompts), "pipeline": PIPELINE}
    with pytest.raises(AnalysisFailure) as failure:
        await worker_module.analyse(ctx, FakeRun(TextContent("Texto")))

    assert failure.value.code == ErrorCode.CONNECTION


# Un escenario que recorre todos los desenlaces de una afirmación a la vez.
_CLAIM_QUERIES = [
    '"q0"',
    "",
    '"q2"',
    '"q3"',
    '"q4"',
    '"q5"',
    "()",
    '"q7"',
    '"q8"',
    '"q9"',
    '"q10"',
]
_CLAIM_TRANSLATIONS = [f"Claim {i} EN" if i != 1 else "" for i in range(11)]
_HITS_BY_SOURCE = {
    "europepmc": {
        '"q0"': ["A0", "A1"],
        '"q3"': ["B3a", "B3b"],
        '"q4"': ["D4"],
        '"q5"': ["E5", "A1"],
        "Claim 6 EN": ["G0", "G1", "G2"],
        '"q8"': ["H0", "H1"],
        '"q9"': ["I9"],
        '"q10"': ["J10"],
    },
    "pubmed": {"Claim 6 EN": ["G2", "G3", "G4"]},
    "openfda": {"Claim 6 EN": ["G5", "G6", "G7"]},
    "cima": {"ibuprofeno": ["C5"]},
}
_STANCES_BY_CLAIM = {
    "Claim 0 EN": "supports",
    "Claim 4 EN": "unrelated",
    "Claim 5 EN": "contradicts",
    "Claim 6 EN": [
        "supports",
        "supports",
        "inconclusive",
        "unrelated",
        "contradicts",
        "supports",
        "supports",
        "supports",
    ],
    "Claim 8 EN": "supports",
}


def _hit(key: str) -> dict:
    return {
        "title": f"Estudio {key}",
        "url": f"https://e.org/{key}",
        "source": "BMJ",
        "year": "2021",
        "abstract": f"Resumen {key}.",
    }


def _search_by_query(name: str):
    """Fuente simulada que responde por consulta; la consulta de la afirmación 2 la tumba."""

    def search(query, max_results=3):
        if query == '"q2"':
            raise EvidenceRetrievalError("fuente caída")
        return [_hit(key) for key in _HITS_BY_SOURCE[name].get(query, [])]

    return search


def _stub_outcome_scenario(monkeypatch):
    """Simula LLMs y fuentes para las 11 afirmaciones del escenario de desenlaces."""
    _stub_extractor(
        monkeypatch,
        statements=[f"Afirmación {i}" for i in range(11)],
        queries=_CLAIM_QUERIES,
        drug_terms=["", "", "", "", "", "ibuprofeno"],
    )
    _stub_translator(monkeypatch, _CLAIM_TRANSLATIONS)
    _stub_health(monkeypatch)
    _stub_sources(
        monkeypatch,
        europepmc=_search_by_query("europepmc"),
        pubmed=_search_by_query("pubmed"),
        openfda=_search_by_query("openfda"),
        cima=_search_by_query("cima"),
    )

    class _Chain:
        def invoke(self, payload):
            if payload["claim"] == "Claim 3 EN":
                raise RuntimeError("juez caído")
            stances = _STANCES_BY_CLAIM[payload["claim"]]
            if isinstance(stances, str):
                stances = [stances] * len(payload["sources"].splitlines())
            return SimpleNamespace(stances=stances)

    monkeypatch.setattr(
        relevance_module,
        "get_relevance_chain",
        lambda prompt_text, model=None: _Chain(),
    )


def _stored_source(key: str, *links: tuple[int, str | None]) -> dict:
    hit = _hit(key)
    return {
        "title": hit["title"],
        "url": hit["url"],
        "source": hit["source"],
        "year": hit["year"],
        "statements": [
            {"claim_index": index, "text": f"Afirmación {index}", "stance": stance}
            for index, stance in links
        ],
    }


def _judged_hit(key: str, stance: str) -> dict:
    return {**_hit(key), "stance": stance}


async def test_every_claim_outcome_reaches_the_report_unchanged(monkeypatch, prompts):
    """Fija fuentes, cobertura y veredicto de un análisis que recorre cada desenlace de afirmación."""
    _stub_outcome_scenario(monkeypatch)

    result = await ainvoke_graph(
        create_graph(prompts), {"input_text": "Texto con once afirmaciones"}
    )

    # Solo se guardan 12 fuentes: G7 y las dos de la afirmación 8 quedan fuera.
    assert result["sources"] == [
        _stored_source("A0", (0, "supports")),
        _stored_source("A1", (0, "supports"), (5, "contradicts")),
        _stored_source("B3a", (3, None)),
        _stored_source("B3b", (3, None)),
        _stored_source("E5", (5, "contradicts")),
        _stored_source("C5", (5, "contradicts")),
        _stored_source("G0", (6, "supports")),
        _stored_source("G1", (6, "supports")),
        _stored_source("G2", (6, "inconclusive")),
        _stored_source("G4", (6, "contradicts")),
        _stored_source("G5", (6, "supports")),
        _stored_source("G6", (6, "supports")),
    ]
    # 10 buscables y 8 buscadas; cubren 0, 3, 5, 6 y 8, esta aunque la cota esconda sus fuentes.
    evidence_search = result["evidence_search"]
    assert (
        evidence_search.total,
        evidence_search.searched,
        evidence_search.covered,
        evidence_search.outage,
    ) == (10, 8, 5, False)
    assert result["judge_failures"] == 1
    # Cada afirmación conserva toda su evidencia; el veredicto solo ve la que muestra el informe.
    found, shown = result["claims"], result["shown_claims"]
    assert [item.url[-2:] for item in found[8].evidence] == ["H0", "H1"]
    assert shown[8].evidence == ()
    assert [item.url[-2:] for item in found[6].evidence][-1] == "G7"
    assert [item.url[-2:] for item in shown[6].evidence][-1] == "G6"

    verdict = result["verdict"]
    assert [(c.text, c.label, c.confidence) for c in verdict.claims] == [
        ("Afirmación 0", "verdadera", pytest.approx(0.75)),
        ("Afirmación 1", "incierta", pytest.approx(0.5)),
        ("Afirmación 2", "incierta", pytest.approx(0.5)),
        ("Afirmación 3", "incierta", pytest.approx(0.5)),
        ("Afirmación 4", "incierta", pytest.approx(0.5)),
        ("Afirmación 5", "falsa", pytest.approx(0.8)),
        ("Afirmación 6", "verdadera", pytest.approx(5 / 7)),
        ("Afirmación 7", "incierta", pytest.approx(0.5)),
        ("Afirmación 8", "incierta", pytest.approx(0.5)),
        ("Afirmación 9", "incierta", pytest.approx(0.5)),
        ("Afirmación 10", "incierta", pytest.approx(0.5)),
    ]
    falsehood = (1 / 4 + 4 / 5 + 2 / 7) / 3
    assert verdict.label == "verdadera"
    assert verdict.falsehood == pytest.approx(falsehood)
    assert verdict.evidence_coverage == 0.5
    assert verdict.confidence == pytest.approx((1 - falsehood) * (1 - 0.25 * 0.5))


async def test_every_claim_outcome_reaches_the_evidence_job_unchanged(
    monkeypatch, prompts
):
    """Fija el resultado del job de evidencia para cada desenlace de afirmación."""
    _stub_outcome_scenario(monkeypatch)

    result = await worker_module.run_evidence_search(
        {"evidence_system": create_evidence_graph(prompts)},
        "Texto con once afirmaciones",
    )

    def entry(index, query, hits, judged):
        return {
            "claim_index": index,
            "query": query,
            "claim": f"Claim {index} EN",
            "original": f"Afirmación {index}",
            "hits": hits,
            "judged": judged,
        }

    # La 1 no tiene consulta y la cota de 8 deja fuera la 9 y la 10.
    assert result == {
        "claims": [
            entry(
                0,
                '"q0"',
                [_judged_hit("A0", "supports"), _judged_hit("A1", "supports")],
                True,
            ),
            entry(2, '"q2"', None, False),
            entry(3, '"q3"', [_hit("B3a"), _hit("B3b")], False),
            entry(4, '"q4"', [], True),
            entry(
                5,
                '"q5"',
                [
                    _judged_hit("E5", "contradicts"),
                    _judged_hit("A1", "contradicts"),
                    _judged_hit("C5", "contradicts"),
                ],
                True,
            ),
            entry(
                6,
                "Claim 6 EN",
                [
                    _judged_hit("G0", "supports"),
                    _judged_hit("G1", "supports"),
                    _judged_hit("G2", "inconclusive"),
                    _judged_hit("G4", "contradicts"),
                    _judged_hit("G5", "supports"),
                    _judged_hit("G6", "supports"),
                    _judged_hit("G7", "supports"),
                ],
                True,
            ),
            entry(7, '"q7"', [], True),
            entry(
                8,
                '"q8"',
                [_judged_hit("H0", "supports"), _judged_hit("H1", "supports")],
                True,
            ),
        ],
        "unsearched_claims": 2,
    }
