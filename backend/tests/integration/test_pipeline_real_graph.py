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
from app.agents.main import create_graph
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
        "extracted_statements": [],
        "translated_statements": [],
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
    """Simula solo el LLM del juez; el filtrado y el padding reales siguen activos."""

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
    assert result["translated_statements"] == ["", ""]
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
