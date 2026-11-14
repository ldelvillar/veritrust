"""Tests of the arq worker, which turns a Run's input into its Verdict and dispatches it."""

import httpx
import pytest
from arq.connections import RedisSettings

import app.worker as worker
from app.core.analysis_lifecycle import (
    AnalysisFailure,
    AnalysisRunner,
    FileContent,
    TextContent,
    UrlContent,
)
from app.core.claim import Claim, with_hits
from app.core.verdict import ClaimVerdict, Verdict
from app.db.deleted_users import UserDeleted
from app.db.pool import DatabaseError
from app.schemas.errors import ErrorCode
from app.utils.extract_text_from_file import FileExtractionError
from app.utils.extract_text_from_url import URLExtractionError
from tests.support.graph import FakeGraph, graph_ending_in
from tests.support.lifecycle import FakeRun

PIPELINE = {"provider": "test", "models": {}, "prompts": {"judge": "v0"}}
VERDICT = Verdict(
    kind="fake",
    confidence=0.92,
    falsehood=0.92,
    evidence_coverage=0.5,
    claims=(ClaimVerdict(text="La lejía cura", kind="fake", confidence=0.9),),
)


def _ctx(graph) -> dict:
    """Worker context whose full graph is ``graph``."""
    return {"verification_system": graph, "pipeline": PIPELINE}


async def test_analyse_turns_the_graph_result_into_a_completion():
    sources = [{"title": "Estudio", "url": "https://doi.org/10.1/x"}]
    graph = graph_ending_in(
        {
            "verdict": VERDICT,
            "medical_explanation": "No hay evidencia clínica sólida.",
            "sources": sources,
        }
    )

    completion = await worker.analyse(
        _ctx(graph), FakeRun(TextContent("Bleach cures COVID"))
    )

    assert graph.seen[0]["input_text"] == "Bleach cures COVID"
    assert completion.verdict is VERDICT
    assert completion.explanation == "No hay evidencia clínica sólida."
    assert completion.sources == sources
    # The Verdict is attributed to the configuration the worker started with.
    assert completion.pipeline == PIPELINE


async def test_analyse_reports_no_medical_claims_when_the_graph_gives_no_verdict():
    graph = graph_ending_in({"verdict": None, "medical_explanation": ""})

    with pytest.raises(AnalysisFailure) as failure:
        await worker.analyse(_ctx(graph), FakeRun(TextContent("Texto sin claim")))

    assert failure.value.code == ErrorCode.NO_MEDICAL_CLAIMS


async def test_analyse_completes_without_report_when_the_explanation_is_empty():
    graph = graph_ending_in({"verdict": VERDICT, "medical_explanation": ""})

    completion = await worker.analyse(_ctx(graph), FakeRun(TextContent("Texto")))

    assert completion.verdict is VERDICT
    assert completion.explanation is None


async def test_analyse_finishes_preparing_before_the_graph_and_reports_each_agent():
    run = FakeRun(TextContent("Texto"))
    graph = graph_ending_in(
        {"verdict": VERDICT, "medical_explanation": "."},
        stages=("extractor", "translator", "investigator", "health_expert"),
    )

    await worker.analyse(_ctx(graph), run)

    assert run.finished_stages == [
        "preparing",
        "extractor",
        "translator",
        "investigator",
        "health_expert",
    ]


async def test_analyse_cuts_the_page_text_to_the_rows_limit(monkeypatch):
    graph = graph_ending_in({"verdict": VERDICT})
    monkeypatch.setattr(worker, "extract_text_from_url", lambda url: "a" * 5000)

    await worker.analyse(
        _ctx(graph), FakeRun(UrlContent("https://ejemplo.com/noticia", max_chars=3000))
    )

    assert graph.seen[0]["input_text"] == "a" * 3000


async def test_analyse_keeps_the_file_text_cut_to_the_rows_limit(monkeypatch):
    graph = graph_ending_in({"verdict": VERDICT})
    run = FakeRun(
        FileContent(data=b"%PDF-1.4 bytes", filename="informe.pdf", max_chars=10)
    )

    def fake_extract(data, filename):
        assert (data, filename) == (b"%PDF-1.4 bytes", "informe.pdf")
        return "Texto extraído del archivo"

    monkeypatch.setattr(worker, "extract_text_from_file", fake_extract)

    await worker.analyse(_ctx(graph), run)

    # The History stores the same text that was analysed.
    assert run.kept_text == ["Texto extr"]
    assert graph.seen[0]["input_text"] == "Texto extr"


def _failing(error):
    def extract(*args):
        raise error

    return extract


@pytest.mark.parametrize(
    ("content", "extractor", "error", "code"),
    [
        (
            UrlContent("https://ejemplo.com/x", max_chars=10_000),
            "extract_text_from_url",
            URLExtractionError("404"),
            ErrorCode.URL_EXTRACTION,
        ),
        (
            FileContent(data=b"%PDF", filename="informe.pdf", max_chars=10_000),
            "extract_text_from_file",
            FileExtractionError("sin texto"),
            ErrorCode.FILE_EXTRACTION,
        ),
    ],
    ids=["url", "file"],
)
async def test_analyse_fails_without_running_the_graph_when_extraction_fails(
    monkeypatch, content, extractor, error, code
):
    graph = graph_ending_in({})
    monkeypatch.setattr(worker, extractor, _failing(error))

    with pytest.raises(AnalysisFailure) as failure:
        await worker.analyse(_ctx(graph), FakeRun(content))

    assert failure.value.code == code
    assert graph.seen == []


async def test_analyse_reports_llm_connection_errors():
    graph = FakeGraph(error=httpx.ConnectError("connect call failed"))

    with pytest.raises(AnalysisFailure) as failure:
        await worker.analyse(_ctx(graph), FakeRun(TextContent("Texto")))

    assert failure.value.code == ErrorCode.CONNECTION


class _RecordingRunner:
    """Fake runner that records what the worker asks of it."""

    def __init__(self):
        self.reaps = 0

    async def reap_orphans(self):
        self.reaps += 1
        return 0


async def test_prune_cron_survives_a_database_failure(monkeypatch):
    async def broken_prune():
        raise DatabaseError("db down")

    monkeypatch.setattr(worker, "prune_expired", broken_prune)

    await worker.prune_deleted_users({})


async def test_reap_cron_delegates_to_the_lifecycle_runner():
    runner = _RecordingRunner()

    await worker.reap_orphaned_analyses({"analysis_runner": runner})

    assert runner.reaps == 1


async def test_startup_wires_graph_prompts_and_pool_into_ctx(monkeypatch):
    """startup leaves the compiled graph under the ctx key run_analysis reads."""
    sentinel_prompts = object()
    sentinel_graph = object()
    sentinel_literature = object()
    calls: list[str] = []
    validated: dict = {}

    class _FakeSettings:
        analysis_job_timeout_seconds = 900
        analysis_stale_after_seconds = 300

        def validate_runtime(self, *, web=True):
            validated["web"] = web

    def fake_create_graph(prompts, literature):
        assert prompts is sentinel_prompts
        assert literature is sentinel_literature
        return sentinel_graph

    async def fake_get_pool():
        calls.append("pool")

    monkeypatch.setattr(worker, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(worker, "ensure_llm_available", lambda: calls.append("llm"))
    monkeypatch.setattr(worker, "load_prompts", lambda: sentinel_prompts)
    monkeypatch.setattr(worker, "live_literature_sources", lambda: sentinel_literature)
    monkeypatch.setattr(worker, "create_graph", fake_create_graph)
    monkeypatch.setattr(
        worker,
        "create_evidence_graph",
        lambda prompts, literature: ("evidence", prompts, literature),
    )
    monkeypatch.setattr(worker, "describe_pipeline", lambda prompts: ("run", prompts))
    monkeypatch.setattr(worker, "get_pool", fake_get_pool)

    class _Redis:
        def register_script(self, script):
            return None

    ctx: dict = {"redis": _Redis()}
    await worker.startup(ctx)

    # The worker serves no web requests, so it must not require CORS or the MCP URL.
    assert validated == {"web": False}
    assert ctx["verification_system"] is sentinel_graph
    assert ctx["evidence_system"] == (
        "evidence",
        sentinel_prompts,
        sentinel_literature,
    )
    # The recorded configuration describes the same prompts the graph was built with.
    assert ctx["pipeline"] == ("run", sentinel_prompts)
    # run_analysis and the reaper use the same lifecycle runner.
    assert isinstance(ctx["analysis_runner"], AnalysisRunner)
    assert set(calls) == {"llm", "pool"}


async def test_shutdown_closes_db_pool(monkeypatch):
    closed = []

    async def fake_close_pool():
        closed.append(True)

    monkeypatch.setattr(worker, "close_pool", fake_close_pool)

    await worker.shutdown({})

    assert closed == [True]


async def test_shutdown_flushes_traces_after_closing_the_pool_even_if_it_fails(
    monkeypatch,
):
    calls = []

    async def failing_close_pool():
        calls.append("close")
        raise RuntimeError("pool already gone")

    monkeypatch.setattr(worker, "close_pool", failing_close_pool)
    monkeypatch.setattr(worker.langfuse, "flush", lambda: calls.append("flush"))

    with pytest.raises(RuntimeError):
        await worker.shutdown({})

    assert calls == ["close", "flush"]


def test_main_starts_arq_worker_with_configured_redis(monkeypatch):
    """The entry point starts arq with WorkerSettings and the Redis DSN from Settings."""
    seen: dict = {}

    def fake_run_worker(settings_cls, redis_settings=None):
        seen["cls"] = settings_cls
        seen["redis"] = redis_settings

    monkeypatch.setattr(worker, "run_worker", fake_run_worker)

    worker.main()

    expected = RedisSettings.from_dsn(worker.get_settings().redis_url)
    assert seen["cls"] is worker.WorkerSettings
    assert (seen["redis"].host, seen["redis"].port) == (expected.host, expected.port)


def test_worker_settings_expose_the_queue_contract():
    """Routes enqueue by name, so the WorkerSettings contract must hold it."""
    settings = worker.get_settings()

    # The web process enqueues by name, so renaming a function would break the queue.
    names = [
        getattr(fn, "name", None) or fn.__name__
        for fn in worker.WorkerSettings.functions
    ]
    assert names == ["run_analysis", "run_evidence_search"]
    # The Evidence search keeps its result so get_evidence can collect it.
    evidence_fn = worker.WorkerSettings.functions[1]
    assert evidence_fn.keep_result_s == worker.EVIDENCE_RESULT_TTL_SECONDS
    assert [cj.name for cj in worker.WorkerSettings.cron_jobs] == [
        "cron:reap_orphaned_analyses",
        "cron:prune_deleted_users",
    ]
    # arq cuts above the internal budget, and the margin lets the failure be notified first.
    assert (
        worker.WorkerSettings.job_timeout
        == settings.analysis_job_timeout_seconds + worker._JOB_TIMEOUT_GRACE_SECONDS
    )
    assert worker.WorkerSettings.max_jobs == settings.worker_max_jobs
    # No results in Redis, since a leftover arq:result: key would block the retry.
    assert worker.WorkerSettings.keep_result == 0


USER = "user-a"
# One Claim searched without results, enough for the search to have a report.
_SEARCHED = [with_hits(Claim(index=0, text="A", query='"a"'), [])]


@pytest.fixture(autouse=True)
def recorded_usage(monkeypatch):
    """Replace the Usage recording with the list of recorded users."""
    users: list[str] = []

    async def record(user_id):
        users.append(user_id)

    monkeypatch.setattr(worker, "record_evidence_search", record)
    return users


def _evidence_ctx(claims=(), error=None) -> dict:
    """Worker context whose evidence-only graph ends with ``claims`` or raises ``error``."""
    graph = FakeGraph(error=error) if error else graph_ending_in({"claims": claims})
    return {"evidence_system": graph}


async def test_run_evidence_search_returns_claims(recorded_usage):
    # One searched without results and two the cap left unsearched.
    ctx = _evidence_ctx(
        [
            with_hits(Claim(index=0, text="La vitamina C cura", query='"c"'), []),
            Claim(index=1, text="B", query='"b"'),
            Claim(index=2, text="C", query='"c"'),
        ]
    )

    result = await worker.run_evidence_search(
        ctx, "La vitamina C cura el resfriado", USER
    )

    (state,) = ctx["evidence_system"].seen
    assert state["input_text"] == "La vitamina C cura el resfriado"
    assert result == {
        "claims": [
            {
                "claim_index": 0,
                "query": '"c"',
                "claim": "",
                "original": "La vitamina C cura",
                "hits": [],
                "judged": True,
            }
        ],
        "unsearched_claims": 2,
    }
    # A search with a result consumes one unit of the Usage of whoever started it.
    assert recorded_usage == [USER]


async def test_run_evidence_search_returns_its_result_even_if_usage_is_lost(
    monkeypatch,
):
    async def broken_record(user_id):
        raise DatabaseError("db down")

    monkeypatch.setattr(worker, "record_evidence_search", broken_record)

    result = await worker.run_evidence_search(_evidence_ctx(_SEARCHED), "Texto", USER)

    assert result["claims"][0]["original"] == "A"


async def test_run_evidence_search_of_a_deleted_account_returns_no_report(
    monkeypatch,
):
    async def refused_record(user_id):
        raise UserDeleted(user_id)

    monkeypatch.setattr(worker, "record_evidence_search", refused_record)

    result = await worker.run_evidence_search(_evidence_ctx(_SEARCHED), "Texto", USER)

    assert result == {"error_code": ErrorCode.INVALID_TOKEN.value}


async def test_run_evidence_search_without_claims_reports_no_medical_claims(
    recorded_usage,
):
    ctx = _evidence_ctx([Claim(index=0, text="Hola")])

    result = await worker.run_evidence_search(ctx, "Hola", USER)

    assert result == {"error_code": "NO_MEDICAL_CLAIMS"}
    assert recorded_usage == []


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (httpx.ConnectError("down"), "CONNECTION"),
        (RuntimeError("boom"), "INTERNAL"),
        (TimeoutError(), "SERVICE_UNAVAILABLE"),
    ],
)
async def test_run_evidence_search_maps_failures_to_error_codes(
    recorded_usage, error, code
):
    result = await worker.run_evidence_search(_evidence_ctx(error=error), "Texto", USER)

    assert result == {"error_code": code}
    assert recorded_usage == []


async def test_run_evidence_search_truncates_long_abstracts():
    long_abstract = "x" * (worker.MAX_ABSTRACT_CHARS + 50)
    hits = [
        {"title": "Ficha", "url": "u1", "abstract": long_abstract},
        {"title": "Corto", "url": "u2", "abstract": "breve"},
        {"title": "Sin resumen", "url": "u3"},
    ]
    ctx = _evidence_ctx([with_hits(Claim(index=0, text="A", query='"a"'), hits)])

    result = await worker.run_evidence_search(ctx, "Texto", USER)

    long_hit, short_hit, empty_hit = result["claims"][0]["hits"]
    # The result lives an hour in Redis, so abstracts are capped before storing it.
    assert len(long_hit["abstract"]) == worker.MAX_ABSTRACT_CHARS + 1
    assert long_hit["abstract"].endswith("…")
    assert short_hit["abstract"] == "breve"
    assert empty_hit["abstract"] is None
