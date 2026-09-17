"""Tests de las herramientas MCP con el cliente en proceso del SDK y dobles de cola y BD."""

import fakeredis
import pytest
from fastapi.testclient import TestClient
from mcp import Client
from mcp.server.auth.provider import AccessToken
from redis.exceptions import RedisError

import app.mcp.server as server_module
from app.core.config import Settings
from app.db.pool import DatabaseError
from app.schemas.history import AnalysisHistoryItem

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


class _Job:
    """Doble de un job de arq que devuelve un resultado fijo o agota la espera."""

    def __init__(self, result=None):
        self._result = result

    async def result(self, timeout=None, **kwargs):
        if self._result is None:
            raise TimeoutError
        return self._result

    async def status(self):
        return "in_progress"


class _ArqPool:
    """Doble del pool de arq que registra los encolados."""

    def __init__(self, job=None, fail=False):
        self.enqueued: list[tuple] = []
        self._job = job
        self._fail = fail

    async def enqueue_job(self, name, *args, **kwargs):
        if self._fail:
            raise RedisError("down")
        self.enqueued.append((name, args, kwargs))
        return self._job


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


def _patch_db(monkeypatch, records):
    """Sustituye la BD: crea análisis y devuelve las filas indicadas en orden."""
    created: list[dict] = []
    failed: list[dict] = []
    pending = list(records)

    async def fake_create(**kwargs):
        created.append(kwargs)
        return ANALYSIS_ID

    async def fake_get(*, user_id, analysis_id):
        assert user_id == USER_ID
        return pending.pop(0) if len(pending) > 1 else pending[0]

    async def fake_fail(**kwargs):
        failed.append(kwargs)

    monkeypatch.setattr(server_module, "create_pending_analysis", fake_create)
    monkeypatch.setattr(server_module, "get_user_analysis_by_id", fake_get)
    monkeypatch.setattr(server_module, "fail_analysis", fake_fail)
    return created, failed


def _server(pool=None, redis=None):
    """Construye el servidor MCP con dobles de cola y Redis."""
    return server_module.build_mcp_server(
        arq_pool=pool or _ArqPool(),
        redis=redis if redis is not None else fakeredis.aioredis.FakeRedis(),
    )


async def test_lists_the_three_tools(env):
    async with Client(_server()) as client:
        tools = await client.list_tools()

    assert sorted(tool.name for tool in tools.tools) == [
        "get_verification",
        "search_evidence",
        "verify_claim",
    ]


async def test_verify_claim_enqueues_and_waits_until_done(env, monkeypatch):
    created, _ = _patch_db(
        monkeypatch, [_record("pending", stage="investigator"), _record("done")]
    )
    pool = _ArqPool()
    progress: list[float] = []

    async def on_progress(value, total, message):
        progress.append(value)

    async with Client(_server(pool)) as client:
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
    assert created[0]["origin"] == "mcp"
    assert created[0]["user_id"] == USER_ID
    # Mismo contrato de cola que la ruta web, sin email para el cliente MCP.
    assert pool.enqueued == [
        (
            "run_analysis",
            (ANALYSIS_ID, "text", "La lejía cura la COVID", None, None),
            {"_job_id": ANALYSIS_ID},
        )
    ]


async def test_verify_claim_accepts_a_url(env, monkeypatch):
    _patch_db(monkeypatch, [_record("done", source_type="url")])
    pool = _ArqPool()

    async with Client(_server(pool)) as client:
        result = await client.call_tool(
            "verify_claim", {"url": "https://ejemplo.com/noticia"}
        )

    assert not result.is_error
    assert pool.enqueued[0][1][1:4] == ("url", None, "https://ejemplo.com/noticia")


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
    created, _ = _patch_db(monkeypatch, [_record()])

    async with Client(_server()) as client:
        result = await client.call_tool("verify_claim", arguments)

    assert result.is_error
    assert created == []


async def test_verify_claim_fails_the_row_when_enqueue_fails(env, monkeypatch):
    _, failed = _patch_db(monkeypatch, [_record()])

    async with Client(_server(_ArqPool(fail=True))) as client:
        result = await client.call_tool(
            "verify_claim", {"text": "La lejía cura la COVID"}
        )

    assert result.is_error
    assert "SERVICE_UNAVAILABLE" in result.content[0].text
    assert failed == [{"analysis_id": ANALYSIS_ID, "error_code": "SERVICE_UNAVAILABLE"}]


async def test_verify_claim_reports_save_failures(env, monkeypatch):
    _patch_db(monkeypatch, [_record()])

    async def broken_create(**kwargs):
        raise DatabaseError("down")

    monkeypatch.setattr(server_module, "create_pending_analysis", broken_create)

    async with Client(_server()) as client:
        result = await client.call_tool(
            "verify_claim", {"text": "La lejía cura la COVID"}
        )

    assert result.is_error
    assert "ANALYSIS_SAVE_FAILED" in result.content[0].text


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


async def test_get_verification_rejects_unknown_and_invalid_ids(env, monkeypatch):
    _patch_db(monkeypatch, [None])

    async with Client(_server()) as client:
        missing = await client.call_tool(
            "get_verification", {"analysis_id": ANALYSIS_ID}
        )
        invalid = await client.call_tool("get_verification", {"analysis_id": "nope"})

    assert "ANALYSIS_NOT_FOUND" in missing.content[0].text
    assert "INVALID_ANALYSIS_ID" in invalid.content[0].text


async def test_get_verification_reports_database_errors(env, monkeypatch):
    async def broken_get(**kwargs):
        raise DatabaseError("down")

    monkeypatch.setattr(server_module, "get_user_analysis_by_id", broken_get)

    async with Client(_server()) as client:
        result = await client.call_tool(
            "get_verification", {"analysis_id": ANALYSIS_ID}
        )

    assert "ANALYSIS_FETCH_FAILED" in result.content[0].text


async def test_search_evidence_returns_claims_with_truncated_abstracts(env):
    long_abstract = "x" * (server_module.MAX_ABSTRACT_CHARS + 50)
    job = _Job(
        {
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
                            "abstract": long_abstract,
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
    )
    pool = _ArqPool(job=job)

    async with Client(_server(pool)) as client:
        result = await client.call_tool(
            "search_evidence", {"claim": "La vitamina C previene el resfriado"}
        )

    assert not result.is_error
    body = result.structured_content
    first, second = body["claims"]
    assert first["claim"] == "La vitamina C previene el resfriado"
    assert first["claim_en"] == "Vitamin C prevents colds"
    assert first["judged"] is True
    assert first["evidence"][0]["stance"] == "contradicts"
    assert len(first["evidence"][0]["abstract"]) == server_module.MAX_ABSTRACT_CHARS + 1
    assert second["sources_unavailable"] is True
    assert second["evidence"] == []
    assert body["unsearched_claims"] == 1
    assert pool.enqueued == [
        ("run_evidence_search", ("La vitamina C previene el resfriado",), {})
    ]


async def test_search_evidence_maps_worker_error_codes(env):
    pool = _ArqPool(job=_Job({"error_code": "NO_MEDICAL_CLAIMS"}))

    async with Client(_server(pool)) as client:
        result = await client.call_tool("search_evidence", {"claim": "Hola, ¿qué tal?"})

    assert result.is_error
    assert "NO_MEDICAL_CLAIMS" in result.content[0].text


async def test_search_evidence_times_out_as_service_unavailable(env):
    env.mcp_tool_wait_seconds = 0.05
    pool = _ArqPool(job=_Job(None))

    async with Client(_server(pool)) as client:
        result = await client.call_tool(
            "search_evidence", {"claim": "La vitamina C previene el resfriado"}
        )

    assert result.is_error
    assert "SERVICE_UNAVAILABLE" in result.content[0].text


async def test_search_evidence_reports_enqueue_failures(env):
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
