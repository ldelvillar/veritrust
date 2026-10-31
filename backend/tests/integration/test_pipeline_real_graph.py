"""Tests of the real four-agent graph with only the external services mocked."""

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
        # The expert renders the YAML templates, so the real prompt goes here.
        health_expert=load_prompts().health_expert,
    )


def _initial_state(text: str) -> dict:
    """Replicate the exact initial state the worker sends to the graph."""
    return {
        "input_text": text,
        "claims": [],
        "sources": [],
        "medical_explanation": "",
    }


def _stub_extractor(monkeypatch, statements, queries, drug_terms=None):
    """Mock only the extractor's LLM call, keeping the rest of the agent real."""

    class _Chain:
        def invoke(self, payload):
            return extractor_module.MedicalStatements(
                claims=[
                    extractor_module.ExtractedClaim(
                        statement=statement, search_query=query, drug_term=drug
                    )
                    for statement, query, drug in zip(
                        statements,
                        queries,
                        drug_terms or [""] * len(statements),
                        strict=True,
                    )
                ]
            )

    monkeypatch.setattr(
        extractor_module,
        "get_extractor_chain",
        lambda prompt_text, model=None: _Chain(),
    )


def _stub_translator(monkeypatch, translations):
    """Mock only the translator's LLM call, validated against the schema it requests."""

    class _Chain:
        def __init__(self, statements):
            self._schema = translator_module.TRANSLATIONS.schema(statements)

        def invoke(self, payload):
            return self._schema.model_validate(
                {f"translation_{n}": t for n, t in enumerate(translations, start=1)}
            )

    monkeypatch.setattr(
        translator_module,
        "get_translator_chain",
        lambda prompt_text, statements: _Chain(statements),
    )


def _guard_translator(monkeypatch):
    """Fail the test if the translator ever invokes its LLM."""

    def _should_not_be_called(prompt_text, statements):
        raise AssertionError("El traductor no debe invocar su LLM sin afirmaciones")

    monkeypatch.setattr(
        translator_module, "get_translator_chain", _should_not_be_called
    )


def _stub_health(monkeypatch, llm_error=None):
    """Mock the expert's LLM, returning what it receives."""
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
    """Fail the test if the expert ever instantiates its LLM."""

    def _fail(*args, **kwargs):
        raise AssertionError("No debe usarse el LLM sin afirmaciones")

    monkeypatch.setattr(health_module, "get_health_expert_llm", _fail)


def _stub_sources(monkeypatch, europepmc=None, pubmed=None, openfda=None, cima=None):
    """Replace the four evidence sources, where None means returning nothing."""

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
    """Mock only the judge's LLM, keeping the real filtering active."""

    class _Chain:
        def __init__(self, sources):
            self._sources = sources

        def invoke(self, payload):
            if record is not None:
                record.append(payload["claim"])
            return _judgments([stance] * self._sources, self._sources)

    monkeypatch.setattr(
        relevance_module,
        "get_relevance_chain",
        lambda prompt_text, sources, model=None: _Chain(sources),
    )


def _judgments(stances: list[str], sources: int):
    """Judge answer validated, as in production, against the schema of ``sources`` Sources."""
    schema = relevance_module.EVIDENCE_JUDGMENTS.schema(sources)
    return schema.model_validate(
        {
            f"source_{n}": {"finding": "hallazgo", "stance": stance}
            for n, stance in enumerate(stances, start=1)
        }
    )


def test_full_pipeline_carries_claims_from_extraction_to_verdict(monkeypatch, prompts):
    """Claims flow extractor, translator, investigator and expert without getting lost."""
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

    # PubMed and openFDA are down, so the pipeline must go on with the live sources.
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

    # The judge evaluates the translations, never the original Spanish text.
    assert judged == [
        "Ibuprofen cures the flu",
        "Vitamin C prevents the common cold",
    ]
    verdict = result["verdict"]
    # Per-claim Verdicts keep the original Spanish text.
    assert [c.text for c in verdict.claims] == [
        "El ibuprofeno cura la gripe",
        "La vitamina C previene el resfriado",
    ]
    assert verdict.label == "verdadera"
    # Supporting Evidence (2 and 1 Sources) gives a mean falsehood of (1/4 + 1/3) / 2 = 7/24.
    assert verdict.confidence == pytest.approx(17 / 24)
    assert verdict.evidence_coverage == 1.0
    assert result["medical_explanation"] == "Informe médico integrado"

    # The merged Sources link each original claim they support.
    urls = {s["url"] for s in result["sources"]}
    assert "https://cima.aemps.es/ibuprofeno" in urls
    linked = {st["text"] for s in result["sources"] for st in s["statements"]}
    assert linked == {
        "El ibuprofeno cura la gripe",
        "La vitamina C previene el resfriado",
    }
    # The expert's report is grounded in the retrieved Sources.
    assert "Estudio sobre" in captured["human"]


async def test_pipeline_with_no_claims_ends_as_no_medical_claims_row(
    monkeypatch, prompts
):
    """Text without claims runs no downstream LLMs and leaves a failed NO_MEDICAL_CLAIMS row."""
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
    """Without the expert's report the Verdict is stored all the same and is never NO_MEDICAL_CLAIMS."""
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
    """If the extractor leaves a claim's query empty, it is searched with the translation."""
    _stub_extractor(
        monkeypatch,
        statements=["Afirmación uno", "Afirmación dos"],
        queries=['"query one"', ""],
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

    # The claim without a focused query is investigated with its English translation, in no guaranteed order since searches run in a thread pool.
    assert set(europepmc_queries) == {'"query one"', "Claim two EN"}
    assert result["verdict"].evidence_coverage == 1.0


def test_empty_translator_output_still_produces_a_verdict(monkeypatch, prompts):
    """A translator that leaves translations empty must not break the following agents."""
    _stub_extractor(
        monkeypatch,
        statements=["Afirmación uno", "Afirmación dos"],
        queries=['"query one"', '"query two"'],
        drug_terms=[],
    )
    _stub_translator(monkeypatch, ["", ""])
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

    # The claims stay untranslated and the pipeline keeps going.
    assert [claim.text_en for claim in result["claims"]] == ["", ""]
    # Without a translation the relevance judge gets the query as a fallback.
    assert judged_claims == ['"query one"', '"query two"']
    assert result["verdict"].label == "verdadera"
    assert len(result["verdict"].claims) == 2


def test_total_evidence_outage_does_not_penalize_confidence(monkeypatch, prompts):
    """With every source down the coverage is unknown, our failure rather than the content's."""
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
    # Without Sources there is no Stance, so it is uncertain and the outage does not attenuate.
    assert result["verdict"].label == "incierta"
    assert result["verdict"].confidence == pytest.approx(0.5)
    # The expert is told not to invent references.
    assert "No se hallaron fuentes" in captured["human"]


def test_judge_rejecting_all_sources_leaves_claim_uncovered(monkeypatch, prompts):
    """Evidence found but irrelevant is discarded by the judge and coverage drops to 0."""
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

    # The judge's real filtering empties the Sources and penalises the Confidence to the maximum.
    assert result["sources"] == []
    assert result["verdict"].evidence_coverage == 0.0
    assert result["verdict"].confidence == pytest.approx(0.5 * 0.75)


async def test_midgraph_transport_failure_surfaces_with_partial_stages(
    monkeypatch, prompts
):
    """Ollama down in the expert gives a typed error with only the previous stages completed."""
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

    # The expert never finished, so the stages reflect the real partial progress.
    assert stages == ["extractor", "translator", "investigator"]


async def test_worker_maps_real_graph_transport_failure_to_connection_row(
    monkeypatch, prompts
):
    """An Ollama outage inside the real graph ends as a failed CONNECTION row."""
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


# One scenario that walks through every claim outcome at once.
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
    """Mock source that answers by query, where claim 2's query brings it down."""

    def search(query, max_results=3):
        if query == '"q2"':
            raise EvidenceRetrievalError("fuente caída")
        return [_hit(key) for key in _HITS_BY_SOURCE[name].get(query, [])]

    return search


def _stub_outcome_scenario(monkeypatch):
    """Mock LLMs and sources for the 11 claims of the outcomes scenario."""
    _stub_extractor(
        monkeypatch,
        statements=[f"Afirmación {i}" for i in range(11)],
        queries=_CLAIM_QUERIES,
        drug_terms=["", "", "", "", "", "ibuprofeno", "", "", "", "", ""],
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
        def __init__(self, sources):
            self._sources = sources

        def invoke(self, payload):
            if payload["claim"] == "Claim 3 EN":
                raise RuntimeError("juez caído")
            stances = _STANCES_BY_CLAIM[payload["claim"]]
            if isinstance(stances, str):
                stances = [stances] * self._sources
            return _judgments(stances, self._sources)

    monkeypatch.setattr(
        relevance_module,
        "get_relevance_chain",
        lambda prompt_text, sources, model=None: _Chain(sources),
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
    """Pin the Sources, coverage and Verdict of an Analysis that walks through every claim outcome."""
    _stub_outcome_scenario(monkeypatch)

    result = await ainvoke_graph(
        create_graph(prompts), {"input_text": "Texto con once afirmaciones"}
    )

    # Only 12 Sources are stored, so G7 and claim 8's two are left out.
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
    # 10 searchable and 8 searched, covering 0, 3, 5, 6 and 8, the last even though the cap hides its Sources.
    evidence_search = result["evidence_search"]
    assert (
        evidence_search.total,
        evidence_search.searched,
        evidence_search.covered,
        evidence_search.outage,
    ) == (10, 8, 5, False)
    assert result["judge_failures"] == 1
    # Each claim keeps all its Evidence, while the Verdict only sees what the report shows.
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
    # The true claims 0 and 6 do not offset the false claim 5, so it is partly false with its Confidence.
    assert verdict.label == "parcialmente falsa"
    assert verdict.falsehood == pytest.approx(falsehood)
    assert verdict.evidence_coverage == 0.5
    assert verdict.confidence == pytest.approx(0.8 * (1 - 0.25 * 0.5))


async def test_every_claim_outcome_reaches_the_evidence_job_unchanged(
    monkeypatch, prompts
):
    """Pin the evidence job's result for each claim outcome."""
    _stub_outcome_scenario(monkeypatch)
    recorded: list[str] = []

    async def record_evidence_search(user_id):
        recorded.append(user_id)

    monkeypatch.setattr(worker_module, "record_evidence_search", record_evidence_search)

    result = await worker_module.run_evidence_search(
        {"evidence_system": create_evidence_graph(prompts)},
        "Texto con once afirmaciones",
        "user-a",
    )
    assert recorded == ["user-a"]

    def entry(index, query, hits, judged):
        return {
            "claim_index": index,
            "query": query,
            "claim": f"Claim {index} EN",
            "original": f"Afirmación {index}",
            "hits": hits,
            "judged": judged,
        }

    # Claim 1 has no query and the cap of 8 leaves out 9 and 10.
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
