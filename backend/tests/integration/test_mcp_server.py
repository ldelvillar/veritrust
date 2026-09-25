"""Tests de las herramientas MCP con el cliente en proceso del SDK y dobles de cola y BD."""

from types import SimpleNamespace

import fakeredis
import pytest
from arq.jobs import JobStatus
from fastapi.testclient import TestClient
from mcp import Client
from mcp.server.auth.provider import AccessToken
from redis.exceptions import RedisError

import app.mcp.server as server_module
from app.core.analysis_lifecycle import Submitter
from app.core.config import Settings
from app.core.errors import make_error_detail
from app.db.pool import DatabaseError
from app.schemas.analysis import AnalysisStatusResponse
from app.schemas.errors import ErrorCode
from app.schemas.history import AnalysisHistoryItem
from tests.support.lifecycle import StubIntake

ANALYSIS_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "user_123"


def _settings(**overrides) -> Settings:
    """Settings deterministas para el servidor MCP, ignorando .env."""
    base: dict[str, object] = {
        "environment": "production",
        "cors_allowed_origins": "https://veritrust.es",
        "clerk_issuer": "https://tenant.clerk.accounts.dev",
        "app_base_url": "https://veritrust.es",
        "mcp_resource_url": "http://testserver/mcp",
        "mcp_tool_wait_seconds": 5,
        "rate_limit_max_requests": 5,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


JOB_ID = "0123456789abcdef0123456789abcdef"


class _ScriptedJob:
    """Doble de arq.jobs.Job que recorre una secuencia de estados y termina con un resultado."""

    def __init__(self, steps):
        self._steps = list(steps)

    def _current(self):
        return self._steps[0]

    async def result_info(self):
        step = self._current()
        if isinstance(step, tuple):
            success, result = step
            return SimpleNamespace(success=success, result=result)
        return None

    async def status(self):
        step = self._current()
        if len(self._steps) > 1:
            self._steps.pop(0)
        return step


def _patch_job(monkeypatch, *steps):
    """Hace que el servidor reabra los jobs de evidencia con el guion indicado."""
    created: list[str] = []
    job = _ScriptedJob(steps)

    def factory(job_id, redis):
        created.append(job_id)
        return job

    monkeypatch.setattr(server_module, "Job", factory)
    return created


class _ArqPool:
    """Doble del pool de arq que registra los encolados."""

    def __init__(self, fail=False):
        self.enqueued: list[tuple] = []
        self._fail = fail

    async def enqueue_job(self, name, *args, **kwargs):
        if self._fail:
            raise RedisError("down")
        self.enqueued.append((name, args, kwargs))
        return SimpleNamespace(job_id=kwargs.get("_job_id"))


def _record(status="done", **overrides) -> AnalysisHistoryItem:
    """Fila del historial de un análisis MCP."""
    base: dict = {
        "analysis_id": ANALYSIS_ID,
        "user_id": USER_ID,
        "source_type": "text",
        "origin": "mcp",
        "input_text": "La lejía cura la COVID",
        "created_at": "2026-09-17T00:00:00+00:00",
        "status": status,
    }
    if status == "done":
        base.update(
            label="falsa",
            confidence=0.9,
            evidence_coverage=0.5,
            explanation="No hay evidencia.",
            claims=[{"text": "La lejía cura", "label": "falsa", "confidence": 0.9}],
            sources=[{"title": "Estudio", "url": "https://doi.org/10.1/x"}],
        )
    base.update(overrides)
    return AnalysisHistoryItem(**base)


@pytest.fixture
def env(monkeypatch):
    """Configura settings, identidad OAuth y sondeo rápido para las herramientas."""
    settings = _settings()
    monkeypatch.setattr(server_module, "get_settings", lambda: settings)
    monkeypatch.setattr(server_module, "_POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(
        server_module,
        "get_access_token",
        lambda: AccessToken(token="t", client_id="client", scopes=[], subject=USER_ID),
    )
    return settings


def _patch_db(monkeypatch, records) -> list[str]:
    """Sustituye las lecturas del sondeo: el estado avanza por las filas y el informe lee la actual."""
    rows = list(records)
    cursor = -1
    report_reads: list[str] = []

    async def fake_status(*, user_id, analysis_id):
        nonlocal cursor
        assert user_id == USER_ID
        cursor = min(cursor + 1, len(rows) - 1)
        row = rows[cursor]
        if row is None:
            return None
        return AnalysisStatusResponse(status=row.status, stage=row.stage)

    async def fake_get(*, user_id, analysis_id):
        assert user_id == USER_ID
        report_reads.append(analysis_id)
        return rows[max(cursor, 0)]

    monkeypatch.setattr(server_module, "get_user_analysis_status", fake_status)
    monkeypatch.setattr(server_module, "get_user_analysis_by_id", fake_get)
    return report_reads


def _server(pool=None, redis=None, intake=None):
    """Construye el servidor MCP con dobles de cola, Redis y entrada de análisis."""
    return server_module.build_mcp_server(
        arq_pool=pool or _ArqPool(),
        redis=redis if redis is not None else fakeredis.aioredis.FakeRedis(),
        analysis_intake=intake if intake is not None else StubIntake(),
    )


async def test_lists_the_four_tools(env):
    async with Client(_server()) as client:
        tools = await client.list_tools()

    assert sorted(tool.name for tool in tools.tools) == [
        "get_evidence",
        "get_verification",
        "search_evidence",
        "verify_claim",
    ]


async def test_verify_claim_opens_the_analysis_and_waits_until_done(env, monkeypatch):
    _patch_db(monkeypatch, [_record("pending", stage="investigator"), _record("done")])
    intake = StubIntake()
    progress: list[float] = []

    async def on_progress(value, total, message):
        progress.append(value)

    async with Client(_server(intake=intake)) as client:
        result = await client.call_tool(
            "verify_claim",
            {"text": "La lejía cura la COVID"},
            progress_callback=on_progress,
        )

    assert not result.is_error
    body = result.structured_content
    assert body["status"] == "done"
    assert body["verdict"] == "fake"
    assert body["credibility"] == 10
    assert body["report_url"] == f"https://veritrust.es/app/analisis/{ANALYSIS_ID}"
    # Misma entrada que la ruta web, con Origin mcp y sin email para el cliente MCP.
    [(kind, submitter, request)] = intake.calls
    assert (kind, submitter) == ("submit", Submitter(user_id=USER_ID, origin="mcp"))
    assert request.text == "La lejía cura la COVID"


async def test_verify_claim_accepts_a_url(env, monkeypatch):
    _patch_db(monkeypatch, [_record("done", source_type="url")])
    intake = StubIntake()

    async with Client(_server(intake=intake)) as client:
        result = await client.call_tool(
            "verify_claim", {"url": "https://ejemplo.com/noticia"}
        )

    assert not result.is_error
    [(_, _, request)] = intake.calls
    assert request.source_type.value == "url"
    assert str(request.url) == "https://ejemplo.com/noticia"


async def test_verify_claim_returns_pending_when_the_wait_runs_out(env, monkeypatch):
    env.mcp_tool_wait_seconds = 0
    _patch_db(monkeypatch, [_record("pending", stage="extractor")])

    async with Client(_server()) as client:
        result = await client.call_tool(
            "verify_claim", {"text": "La lejía cura la COVID"}
        )

    body = result.structured_content
    assert body["status"] == "pending"
    assert body["stage"] == "extractor"
    assert "get_verification" in body["message"]


@pytest.mark.parametrize(
    "arguments",
    [{}, {"text": "La lejía cura la COVID", "url": "https://ejemplo.com"}],
    ids=["neither", "both"],
)
async def test_verify_claim_requires_exactly_one_input(env, monkeypatch, arguments):
    _patch_db(monkeypatch, [_record()])
    intake = StubIntake()

    async with Client(_server(intake=intake)) as client:
        result = await client.call_tool("verify_claim", arguments)

    assert result.is_error
    assert intake.calls == []


@pytest.mark.parametrize(
    "code", [ErrorCode.SERVICE_UNAVAILABLE, ErrorCode.ANALYSIS_SAVE_FAILED]
)
async def test_verify_claim_reports_the_intake_refusal(env, monkeypatch, code):
    _patch_db(monkeypatch, [_record()])

    async with Client(_server(intake=StubIntake(refuse=code))) as client:
        result = await client.call_tool(
            "verify_claim", {"text": "La lejía cura la COVID"}
        )

    assert result.is_error
    detail = make_error_detail(code)
    assert result.content[0].text.endswith(f"{detail['code']}: {detail['message']}")


async def test_verify_claim_shares_the_web_rate_limit(env, monkeypatch):
    env.rate_limit_max_requests = 1
    _patch_db(monkeypatch, [_record()])
    redis = fakeredis.aioredis.FakeRedis()

    async with Client(_server(redis=redis)) as client:
        first = await client.call_tool(
            "verify_claim", {"text": "La lejía cura la COVID"}
        )
        second = await client.call_tool(
            "verify_claim", {"text": "La lejía cura la COVID"}
        )

    assert not first.is_error
    assert second.is_error
    assert "RATE_LIMIT" in second.content[0].text
    assert await redis.zcard(f"rate_limit:{USER_ID}") == 1


async def test_verify_claim_requires_an_authenticated_user(env, monkeypatch):
    monkeypatch.setattr(server_module, "get_access_token", lambda: None)

    async with Client(_server()) as client:
        result = await client.call_tool(
            "verify_claim", {"text": "La lejía cura la COVID"}
        )

    assert result.is_error
    assert "UNAUTHENTICATED" in result.content[0].text


async def test_get_verification_returns_the_failed_state(env, monkeypatch):
    _patch_db(monkeypatch, [_record("failed", error_code="NO_MEDICAL_CLAIMS")])

    async with Client(_server()) as client:
        result = await client.call_tool(
            "get_verification", {"analysis_id": ANALYSIS_ID}
        )

    body = result.structured_content
    assert body["status"] == "failed"
    assert body["error_code"] == "NO_MEDICAL_CLAIMS"
    assert body["label"] is None


async def test_get_verification_polls_the_status_and_reads_the_report_once(
    env, monkeypatch
):
    report_reads = _patch_db(
        monkeypatch,
        [
            _record("pending", stage="extractor"),
            _record("pending", stage="investigator"),
            _record("done"),
        ],
    )

    async with Client(_server()) as client:
        result = await client.call_tool(
            "get_verification", {"analysis_id": ANALYSIS_ID}
        )

    assert result.structured_content["status"] == "done"
    assert report_reads == [ANALYSIS_ID]


async def test_get_verification_rejects_unknown_and_invalid_ids(env, monkeypatch):
    _patch_db(monkeypatch, [None])

    async with Client(_server()) as client:
        missing = await client.call_tool(
            "get_verification", {"analysis_id": ANALYSIS_ID}
        )
        invalid = await client.call_tool("get_verification", {"analysis_id": "nope"})

    assert "ANALYSIS_NOT_FOUND" in missing.content[0].text
    assert "INVALID_ANALYSIS_ID" in invalid.content[0].text


@pytest.mark.parametrize(
    "read", ["get_user_analysis_status", "get_user_analysis_by_id"]
)
async def test_get_verification_reports_database_errors(env, monkeypatch, read):
    _patch_db(monkeypatch, [_record("done")])

    async def broken_read(**kwargs):
        raise DatabaseError("down")

    monkeypatch.setattr(server_module, read, broken_read)

    async with Client(_server()) as client:
        result = await client.call_tool(
            "get_verification", {"analysis_id": ANALYSIS_ID}
        )

    assert "ANALYSIS_FETCH_FAILED" in result.content[0].text


_EVIDENCE_RESULT = {
    "claims": [
        {
            "claim_index": 0,
            "query": "vitamin C AND common cold",
            "claim": "Vitamin C prevents colds",
            "original": "La vitamina C previene el resfriado",
            "hits": [
                {
                    "title": "Cochrane review",
                    "url": "https://doi.org/10.1/c",
                    "source": "Cochrane",
                    "year": "2013",
                    "stance": "contradicts",
                    "abstract": "Regular supplementation does not prevent colds.",
                }
            ],
            "judged": True,
        },
        {
            "claim_index": 1,
            "query": "q",
            "claim": "B",
            "original": "b",
            "hits": None,
            "judged": False,
        },
    ],
    "unsearched_claims": 1,
}


async def test_search_evidence_waits_for_the_result(env, monkeypatch):
    created = _patch_job(
        monkeypatch, JobStatus.queued, JobStatus.in_progress, (True, _EVIDENCE_RESULT)
    )
    pool = _ArqPool()
    redis = fakeredis.aioredis.FakeRedis()
    progress: list[str] = []

    async def on_progress(value, total, message):
        progress.append(message)

    async with Client(_server(pool, redis)) as client:
        result = await client.call_tool(
            "search_evidence",
            {"claim": "La vitamina C previene el resfriado"},
            progress_callback=on_progress,
        )

    assert not result.is_error
    body = result.structured_content
    assert body["status"] == "done"
    first, second = body["claims"]
    assert first["claim"] == "La vitamina C previene el resfriado"
    assert first["claim_en"] == "Vitamin C prevents colds"
    assert first["judged"] is True
    assert first["evidence"][0]["stance"] == "contradicts"
    assert first["evidence"][0]["abstract"].startswith("Regular supplementation")
    assert second["sources_unavailable"] is True
    assert second["evidence"] == []
    assert body["unsearched_claims"] == 1
    assert progress == ["Queued", "Searching the literature"]

    ((name, args, kwargs),) = pool.enqueued
    assert (name, args) == (
        "run_evidence_search",
        ("La vitamina C previene el resfriado",),
    )
    # El job se reabre por su id y queda ligado al usuario que lo lanzó.
    assert created == [kwargs["_job_id"]] == [body["job_id"]]
    owner_key = f"mcp:evidence_owner:{body['job_id']}"
    assert await redis.get(owner_key) == USER_ID.encode()
    assert await redis.ttl(owner_key) > server_module.EVIDENCE_RESULT_TTL_SECONDS


async def test_search_evidence_returns_pending_when_the_wait_runs_out(env, monkeypatch):
    env.mcp_tool_wait_seconds = 0
    _patch_job(monkeypatch, JobStatus.in_progress)

    async with Client(_server()) as client:
        result = await client.call_tool(
            "search_evidence", {"claim": "La vitamina C previene el resfriado"}
        )

    body = result.structured_content
    assert body["status"] == "pending"
    assert body["claims"] == []
    assert "get_evidence" in body["message"]
    assert len(body["job_id"]) == 32


async def test_get_evidence_resumes_the_users_search(env, monkeypatch):
    _patch_job(monkeypatch, JobStatus.in_progress, (True, _EVIDENCE_RESULT))
    redis = fakeredis.aioredis.FakeRedis()
    await redis.set(f"mcp:evidence_owner:{JOB_ID}", USER_ID)

    async with Client(_server(redis=redis)) as client:
        result = await client.call_tool("get_evidence", {"job_id": JOB_ID})

    body = result.structured_content
    assert body["status"] == "done"
    assert body["job_id"] == JOB_ID
    assert len(body["claims"]) == 2


async def test_get_evidence_hides_other_users_and_unknown_searches(env, monkeypatch):
    _patch_job(monkeypatch, (True, _EVIDENCE_RESULT))
    redis = fakeredis.aioredis.FakeRedis()
    await redis.set(f"mcp:evidence_owner:{JOB_ID}", "someone_else")

    async with Client(_server(redis=redis)) as client:
        foreign = await client.call_tool("get_evidence", {"job_id": JOB_ID})
        unknown = await client.call_tool("get_evidence", {"job_id": "f" * 32})
        malformed = await client.call_tool("get_evidence", {"job_id": "nope"})

    assert "EVIDENCE_SEARCH_NOT_FOUND" in foreign.content[0].text
    assert "EVIDENCE_SEARCH_NOT_FOUND" in unknown.content[0].text
    assert malformed.is_error


async def test_get_evidence_reports_an_expired_search(env, monkeypatch):
    _patch_job(monkeypatch, JobStatus.not_found)
    redis = fakeredis.aioredis.FakeRedis()
    await redis.set(f"mcp:evidence_owner:{JOB_ID}", USER_ID)

    async with Client(_server(redis=redis)) as client:
        result = await client.call_tool("get_evidence", {"job_id": JOB_ID})

    assert "EVIDENCE_SEARCH_NOT_FOUND" in result.content[0].text


@pytest.mark.parametrize(
    ("step", "code"),
    [
        ((True, {"error_code": "NO_MEDICAL_CLAIMS"}), "NO_MEDICAL_CLAIMS"),
        ((False, TimeoutError()), "INTERNAL"),
    ],
    ids=["worker-error-code", "job-crashed"],
)
async def test_search_evidence_maps_job_failures(env, monkeypatch, step, code):
    _patch_job(monkeypatch, step)

    async with Client(_server()) as client:
        result = await client.call_tool("search_evidence", {"claim": "Hola, ¿qué tal?"})

    assert result.is_error
    assert code in result.content[0].text


async def test_search_evidence_reports_enqueue_failures(env, monkeypatch):
    _patch_job(monkeypatch, JobStatus.queued)

    async with Client(_server(_ArqPool(fail=True))) as client:
        result = await client.call_tool(
            "search_evidence", {"claim": "La vitamina C previene el resfriado"}
        )

    assert "SERVICE_UNAVAILABLE" in result.content[0].text


def test_http_app_requires_a_bearer_token_and_publishes_metadata(env):
    http_app = server_module.build_mcp_http_app(_server())
    client = TestClient(http_app)

    unauthenticated = client.post("/mcp", json={})
    metadata = client.get(server_module.MCP_METADATA_PATH)

    assert unauthenticated.status_code == 401
    assert "resource_metadata" in unauthenticated.headers["www-authenticate"]
    assert metadata.status_code == 200
    assert metadata.json()["authorization_servers"] == [
        "https://tenant.clerk.accounts.dev"
    ]
    assert metadata.json()["resource"] == "http://testserver/mcp"
