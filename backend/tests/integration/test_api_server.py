"""Tests de integración para la API server, verificando endpoints y manejo de errores."""

import csv
import importlib
import io
import sys
import types
from pathlib import Path

import fakeredis
from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from app.api.dependencies.get_current_user import get_current_user
from app.db.pool import DatabaseError
from app.schemas.history import AnalysisHistoryItem, PublicAnalysisReport


class _FakeArqPool:
    """Pool de arq de mentira que registra los trabajos encolados."""

    def __init__(self):
        self.jobs = []
        self.job_ids = []

    async def enqueue_job(self, *args, **kwargs):
        self.jobs.append(args)
        self.job_ids.append(kwargs.get("_job_id"))

    async def close(self):
        pass


class _LoopSafeFakeRedis:
    """Redis de mentira resistente al cambio de event loop del TestClient."""

    def __init__(self):
        self._server = fakeredis.FakeServer()

    def pipeline(self, *args, **kwargs):
        client = fakeredis.aioredis.FakeRedis(server=self._server)
        return client.pipeline(*args, **kwargs)

    async def ping(self):
        client = fakeredis.aioredis.FakeRedis(server=self._server)
        return await client.ping()


def _load_server_module(monkeypatch):
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    sys.modules.pop("app.main", None)
    server_module = importlib.import_module("app.main")

    # TestClient(app) no ejecuta el lifespan, así que inyectamos el pool a mano.
    fake_pool = _FakeArqPool()
    server_module.app.state.arq_pool = fake_pool

    # Redis de mentira fresco por test: el rate limit no se acumula entre tests.
    server_module.app.state.redis = _LoopSafeFakeRedis()
    server_module.app.dependency_overrides[get_current_user] = lambda: {
        "sub": "test-user"
    }

    return server_module, fake_pool


async def _ok_database():
    return None


def test_healthz_returns_ready_when_dependencies_respond(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    # La BD real no está disponible en tests; sondeamos solo Redis (fake).
    monkeypatch.setattr("app.api.routes.health._check_database", _ok_database)
    client = TestClient(server_module.app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_healthz_returns_503_when_pool_failed_to_initialize(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    server_module.app.state.arq_pool = None
    client = TestClient(server_module.app)

    response = client.get("/healthz")

    assert response.status_code == 503


def test_healthz_returns_503_when_database_is_down(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)

    async def fail_database():
        raise RuntimeError("db down")

    monkeypatch.setattr("app.api.routes.health._check_database", fail_database)
    client = TestClient(server_module.app)

    response = client.get("/healthz")

    assert response.status_code == 503


def test_healthz_returns_503_when_redis_is_down(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    monkeypatch.setattr("app.api.routes.health._check_database", _ok_database)

    async def fail_redis(_redis):
        raise RuntimeError("redis down")

    monkeypatch.setattr("app.api.routes.health._check_redis", fail_redis)
    client = TestClient(server_module.app)

    response = client.get("/healthz")

    assert response.status_code == 503


def test_analisis_enqueues_job_and_returns_pending(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_create_pending_analysis(**kwargs):
        assert kwargs["user_id"] == "test-user"
        return "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(
        "app.api.routes.analysis.create_pending_analysis",
        fake_create_pending_analysis,
    )

    response = client.post("/analysis", json={"text": "Bleach cures COVID"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["analysis_id"] == "11111111-1111-1111-1111-111111111111"

    # Se encoló run_analysis con el id, el tipo de fuente y el texto.
    assert len(fake_pool.jobs) == 1
    job = fake_pool.jobs[0]
    assert job[0] == "run_analysis"
    assert job[1] == "11111111-1111-1111-1111-111111111111"
    assert job[2] == "text"
    assert job[3] == "Bleach cures COVID"
    assert job[4] is None
    # _job_id=analysis_id: arq deduplica encolados dobles del mismo análisis.
    assert fake_pool.job_ids == ["11111111-1111-1111-1111-111111111111"]


def test_analisis_enqueues_url_job(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_create_pending_analysis(**kwargs):
        return "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(
        "app.api.routes.analysis.create_pending_analysis",
        fake_create_pending_analysis,
    )

    response = client.post(
        "/analysis",
        json={"url": "https://ejemplo.com/noticia", "source_type": "url"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    job = fake_pool.jobs[0]
    assert job[2] == "url"
    assert job[3] is None
    assert job[4] == "https://ejemplo.com/noticia"


def test_analisis_fails_row_and_returns_503_when_enqueue_fails(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)

    class _BrokenArqPool(_FakeArqPool):
        async def enqueue_job(self, *args, **kwargs):
            raise RedisError("redis down")

    server_module.app.state.arq_pool = _BrokenArqPool()
    client = TestClient(server_module.app)

    async def fake_create_pending_analysis(**kwargs):
        return "11111111-1111-1111-1111-111111111111"

    failed = []

    async def fake_fail_analysis(**kwargs):
        failed.append(kwargs)

    monkeypatch.setattr(
        "app.api.routes.analysis.create_pending_analysis",
        fake_create_pending_analysis,
    )
    monkeypatch.setattr(
        "app.api.routes.analysis.fail_analysis",
        fake_fail_analysis,
    )

    response = client.post("/analysis", json={"text": "Bleach cures COVID"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SERVICE_UNAVAILABLE"
    # La fila pendiente se recicla a failed para que el cliente deje de hacer polling.
    assert failed == [
        {
            "analysis_id": "11111111-1111-1111-1111-111111111111",
            "error_code": "SERVICE_UNAVAILABLE",
        }
    ]


def test_analisis_returns_503_when_pool_unavailable(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    server_module.app.state.arq_pool = None
    client = TestClient(server_module.app)

    response = client.post("/analysis", json={"text": "Bleach cures COVID"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SERVICE_UNAVAILABLE"


def test_analisis_returns_429_when_rate_limit_exceeded(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_create_pending_analysis(**kwargs):
        return "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(
        "app.api.routes.analysis.create_pending_analysis",
        fake_create_pending_analysis,
    )

    # El límite por defecto es 5 peticiones por ventana: las 5 primeras pasan.
    for _ in range(5):
        ok = client.post("/analysis", json={"text": "Bleach cures COVID"})
        assert ok.status_code == 200

    blocked = client.post("/analysis", json={"text": "Bleach cures COVID"})

    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "RATE_LIMIT"


def test_analisis_returns_503_when_redis_errors(monkeypatch):
    """Fail-closed: si Redis falla no podemos limitar, así que se rechaza."""
    server_module, _ = _load_server_module(monkeypatch)

    class _BrokenRedis:
        def pipeline(self, *args, **kwargs):
            raise RedisError("redis down")

    server_module.app.state.redis = _BrokenRedis()
    client = TestClient(server_module.app)

    async def fake_create_pending_analysis(**kwargs):
        return "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(
        "app.api.routes.analysis.create_pending_analysis",
        fake_create_pending_analysis,
    )

    response = client.post("/analysis", json={"text": "Bleach cures COVID"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SERVICE_UNAVAILABLE"


def test_analisis_returns_503_when_redis_unavailable(monkeypatch):
    """Fail-closed: sin Redis configurado no se permite encolar el pipeline caro."""
    server_module, _ = _load_server_module(monkeypatch)
    server_module.app.state.redis = None
    client = TestClient(server_module.app)

    async def fake_create_pending_analysis(**kwargs):
        return "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(
        "app.api.routes.analysis.create_pending_analysis",
        fake_create_pending_analysis,
    )

    response = client.post("/analysis", json={"text": "Bleach cures COVID"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SERVICE_UNAVAILABLE"


def test_analisis_returns_save_failed_when_pending_insert_fails(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_create_pending_analysis(**kwargs):
        raise DatabaseError("db down")

    monkeypatch.setattr(
        "app.api.routes.analysis.create_pending_analysis",
        fake_create_pending_analysis,
    )

    response = client.post("/analysis", json={"text": "Bleach cures COVID"})

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "ANALYSIS_SAVE_FAILED"
    assert fake_pool.jobs == []


def test_analisis_rejects_invalid_url(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post(
        "/analysis",
        json={"url": "not-a-valid-url", "source_type": "url"},
    )

    # Pydantic HttpUrl validation should fail with 422
    assert response.status_code == 422
    assert fake_pool.jobs == []


def test_analisis_detail_returns_analysis_for_authenticated_user(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    record = types.SimpleNamespace(
        analysis_id="11111111-1111-1111-1111-111111111111",
        user_id="test-user",
        source_type="text",
        input_text="Texto ejemplo",
        input_url=None,
        label="falsa",
        confidence=0.88,
        explanation="Explicación de ejemplo",
        status="done",
        error_code=None,
        created_at="2026-04-10T12:00:00+00:00",
        claims=[{"text": "Afirmación", "label": "falsa", "confidence": 0.88}],
        sources=[{"title": "Estudio", "url": "https://doi.org/10.1/x"}],
        file_filename=None,
        share_token=None,
        stage=None,
    )

    async def fake_get_user_analysis_by_id(*, user_id, analysis_id):
        assert user_id == "test-user"
        assert analysis_id == "11111111-1111-1111-1111-111111111111"
        return record

    monkeypatch.setattr(
        "app.api.routes.analysis.get_user_analysis_by_id",
        fake_get_user_analysis_by_id,
    )

    response = client.get("/analysis/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == "11111111-1111-1111-1111-111111111111"
    assert body["user_id"] == "test-user"
    assert body["status"] == "done"
    assert body["claims"] == [
        {
            "text": "Afirmación",
            "label": "falsa",
            "confidence": 0.88,
            "verdict": "fake",
        }
    ]


def test_analisis_detail_returns_pending_status(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    record = types.SimpleNamespace(
        analysis_id="11111111-1111-1111-1111-111111111111",
        user_id="test-user",
        source_type="text",
        input_text="Texto ejemplo",
        input_url=None,
        label=None,
        confidence=None,
        explanation=None,
        status="pending",
        error_code=None,
        created_at="2026-04-10T12:00:00+00:00",
        claims=None,
        sources=None,
        file_filename=None,
        share_token=None,
        stage=None,
    )

    async def fake_get_user_analysis_by_id(*, user_id, analysis_id):
        return record

    monkeypatch.setattr(
        "app.api.routes.analysis.get_user_analysis_by_id",
        fake_get_user_analysis_by_id,
    )

    response = client.get("/analysis/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["label"] is None
    assert body["confidence"] is None


def test_analisis_detail_returns_failed_status_with_error_code(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    record = types.SimpleNamespace(
        analysis_id="11111111-1111-1111-1111-111111111111",
        user_id="test-user",
        source_type="text",
        input_text="Texto sin claim",
        input_url=None,
        label=None,
        confidence=None,
        explanation=None,
        status="failed",
        error_code="NO_MEDICAL_CLAIMS",
        created_at="2026-04-10T12:00:00+00:00",
        claims=None,
        sources=None,
        file_filename=None,
        share_token=None,
        stage=None,
    )

    async def fake_get_user_analysis_by_id(*, user_id, analysis_id):
        return record

    monkeypatch.setattr(
        "app.api.routes.analysis.get_user_analysis_by_id",
        fake_get_user_analysis_by_id,
    )

    response = client.get("/analysis/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_code"] == "NO_MEDICAL_CLAIMS"


def test_analisis_detail_returns_404_when_not_found(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_returns_none(**kwargs):
        return None

    monkeypatch.setattr(
        "app.api.routes.analysis.get_user_analysis_by_id",
        fake_returns_none,
    )

    response = client.get("/analysis/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ANALYSIS_NOT_FOUND"


def test_analisis_detail_returns_400_when_id_is_invalid(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.get("/analysis/not-a-uuid")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_ANALYSIS_ID"


def test_analisis_detail_returns_500_when_database_fails(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get_user_analysis_by_id(*, user_id, analysis_id):
        raise DatabaseError("db down")

    monkeypatch.setattr(
        "app.api.routes.analysis.get_user_analysis_by_id",
        fake_get_user_analysis_by_id,
    )

    response = client.get("/analysis/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "ANALYSIS_FETCH_FAILED"


def test_delete_analisis_returns_200_when_deleted(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_delete_user_analysis(*, user_id, analysis_id):
        assert user_id == "test-user"
        assert analysis_id == "11111111-1111-1111-1111-111111111111"
        return True

    monkeypatch.setattr(
        "app.api.routes.analysis.delete_user_analysis",
        fake_delete_user_analysis,
    )

    response = client.delete("/analysis/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "deleted"
    assert body["analysis_id"] == "11111111-1111-1111-1111-111111111111"


def test_delete_analisis_returns_404_when_not_found(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_returns_false(**kwargs):
        return False

    monkeypatch.setattr(
        "app.api.routes.analysis.delete_user_analysis",
        fake_returns_false,
    )

    response = client.delete("/analysis/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ANALYSIS_NOT_FOUND"


def test_delete_analisis_returns_400_when_id_is_invalid(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.delete("/analysis/not-a-uuid")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_ANALYSIS_ID"


def test_delete_analisis_returns_500_when_database_fails(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_delete_user_analysis(*, user_id, analysis_id):
        raise DatabaseError("db down")

    monkeypatch.setattr(
        "app.api.routes.analysis.delete_user_analysis",
        fake_delete_user_analysis,
    )

    response = client.delete("/analysis/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "ANALYSIS_DELETE_FAILED"


_RETRY_ID = "11111111-1111-1111-1111-111111111111"


def _failed_record(
    *,
    source_type: str = "text",
    input_text: str | None = "Bleach cures COVID",
    input_url: str | None = None,
    status: str = "failed",
) -> AnalysisHistoryItem:
    """Construye un registro de historial para los tests de reintento."""
    return AnalysisHistoryItem(
        analysis_id=_RETRY_ID,
        user_id="test-user",
        source_type=source_type,
        input_text=input_text,
        input_url=input_url,
        created_at="2026-06-01T00:00:00+00:00",
        status=status,
        error_code="CONNECTION",
    )


def test_retry_reopens_failed_analysis_and_enqueues_text(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        assert user_id == "test-user"
        return _failed_record(source_type="text")

    reopened = []

    async def fake_reset(*, user_id, analysis_id):
        reopened.append((user_id, analysis_id))
        return True

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)
    monkeypatch.setattr(
        "app.api.routes.analysis.reset_failed_analysis_to_pending", fake_reset
    )

    response = client.post(f"/analysis/{_RETRY_ID}/retry")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["analysis_id"] == _RETRY_ID
    assert reopened == [("test-user", _RETRY_ID)]

    job = fake_pool.jobs[0]
    assert job[0] == "run_analysis"
    assert job[1] == _RETRY_ID
    assert job[2] == "text"
    assert job[3] == "Bleach cures COVID"
    assert job[4] is None
    # _job_id=analysis_id: si el job previo sigue vivo en arq, el retry no lo duplica.
    assert fake_pool.job_ids == [_RETRY_ID]


def test_retry_enqueues_url_with_stored_link(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        return _failed_record(
            source_type="url",
            input_text=None,
            input_url="https://ejemplo.com/noticia",
        )

    async def fake_reset(*, user_id, analysis_id):
        return True

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)
    monkeypatch.setattr(
        "app.api.routes.analysis.reset_failed_analysis_to_pending", fake_reset
    )

    response = client.post(f"/analysis/{_RETRY_ID}/retry")

    assert response.status_code == 200
    job = fake_pool.jobs[0]
    assert job[2] == "url"
    assert job[3] is None
    assert job[4] == "https://ejemplo.com/noticia"


def test_retry_returns_404_when_not_found(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        return None

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)

    response = client.post(f"/analysis/{_RETRY_ID}/retry")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ANALYSIS_NOT_FOUND"
    assert fake_pool.jobs == []


def test_retry_returns_409_when_not_failed(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        return _failed_record(status="done")

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)

    response = client.post(f"/analysis/{_RETRY_ID}/retry")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ANALYSIS_NOT_RETRYABLE"
    assert fake_pool.jobs == []


def test_retry_returns_409_when_reopen_loses_race(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        return _failed_record()

    async def fake_reset(*, user_id, analysis_id):
        return False

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)
    monkeypatch.setattr(
        "app.api.routes.analysis.reset_failed_analysis_to_pending", fake_reset
    )

    response = client.post(f"/analysis/{_RETRY_ID}/retry")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ANALYSIS_NOT_RETRYABLE"
    assert fake_pool.jobs == []


def test_retry_returns_400_when_id_is_invalid(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post("/analysis/not-a-uuid/retry")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_ANALYSIS_ID"


def test_retry_returns_503_when_pool_unavailable(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    server_module.app.state.arq_pool = None
    client = TestClient(server_module.app)

    response = client.post(f"/analysis/{_RETRY_ID}/retry")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SERVICE_UNAVAILABLE"


def test_retry_fails_row_and_returns_503_when_enqueue_fails(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)

    class _BrokenArqPool(_FakeArqPool):
        async def enqueue_job(self, *args, **kwargs):
            raise RedisError("redis down")

    server_module.app.state.arq_pool = _BrokenArqPool()
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        return _failed_record()

    async def fake_reset(*, user_id, analysis_id):
        return True

    failed = []

    async def fake_fail_analysis(**kwargs):
        failed.append(kwargs)

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)
    monkeypatch.setattr(
        "app.api.routes.analysis.reset_failed_analysis_to_pending", fake_reset
    )
    monkeypatch.setattr("app.api.routes.analysis.fail_analysis", fake_fail_analysis)

    response = client.post(f"/analysis/{_RETRY_ID}/retry")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SERVICE_UNAVAILABLE"
    # La fila reabierta se devuelve a failed para que no quede pending.
    assert failed == [{"analysis_id": _RETRY_ID, "error_code": "SERVICE_UNAVAILABLE"}]


def test_retry_returns_500_when_fetch_fails(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        raise DatabaseError("db down")

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)

    response = client.post(f"/analysis/{_RETRY_ID}/retry")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "ANALYSIS_FETCH_FAILED"


def test_retry_returns_500_when_reopen_fails(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        return _failed_record()

    async def fake_reset(*, user_id, analysis_id):
        raise DatabaseError("db down")

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)
    monkeypatch.setattr(
        "app.api.routes.analysis.reset_failed_analysis_to_pending", fake_reset
    )

    response = client.post(f"/analysis/{_RETRY_ID}/retry")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "ANALYSIS_RETRY_FAILED"


def test_analisis_returns_422_when_text_field_is_missing(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post("/analysis", json={})

    assert response.status_code == 422
    assert fake_pool.jobs == []


def test_analisis_returns_422_when_text_and_url_are_both_sent(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post(
        "/analysis",
        json={
            "text": "Un texto",
            "url": "https://ejemplo.com/noticia",
        },
    )

    assert response.status_code == 422
    assert fake_pool.jobs == []


def test_analisis_returns_422_when_url_has_non_url_source_type(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post(
        "/analysis",
        json={
            "url": "https://ejemplo.com/noticia",
            "source_type": "text",
        },
    )

    assert response.status_code == 422
    assert fake_pool.jobs == []


def test_analisis_returns_422_when_text_has_url_source_type(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post(
        "/analysis",
        json={
            "text": "Un texto",
            "source_type": "url",
        },
    )

    assert response.status_code == 422
    assert fake_pool.jobs == []


def test_analisis_returns_422_when_text_is_empty_or_whitespace(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    empty_response = client.post("/analysis", json={"text": ""})
    whitespace_response = client.post("/analysis", json={"text": "   \n\t  "})

    assert empty_response.status_code == 422
    assert whitespace_response.status_code == 422
    assert fake_pool.jobs == []


def test_analisis_returns_422_when_text_is_too_long(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    very_long_text = "a" * 10001
    response = client.post("/analysis", json={"text": very_long_text})

    assert response.status_code == 422
    assert fake_pool.jobs == []


def test_analisis_requires_auth_when_dependency_is_not_overridden(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)
    server_module.app.dependency_overrides.pop(get_current_user, None)

    response = client.post("/analysis", json={"text": "Texto"})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHENTICATED"


def test_historial_returns_user_history(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    history_rows = [
        {
            "analysis_id": "11111111-1111-1111-1111-111111111111",
            "user_id": "test-user",
            "source_type": "text",
            "input_text": "Texto ejemplo",
            "input_url": None,
            "label": "falsa",
            "confidence": 0.88,
            "explanation": "Explicación de ejemplo",
            "status": "done",
            "error_code": None,
            "created_at": "2026-04-10T12:00:00+00:00",
            "file_filename": "documento.pdf",
        }
    ]

    async def fake_list_user_analysis_history(
        *,
        user_id,
        limit,
        offset,
        search_query,
        source_type,
        created_after,
        sort,
        verdict,
        status,
    ):
        assert user_id == "test-user"
        assert verdict == "fake"
        assert limit == 10
        assert offset == 0
        assert search_query == "vacuna"
        assert source_type == "text"
        assert created_after is not None
        assert sort == "credibility_high"
        # Sin parámetro 'status' explícito el filtro de estado queda en None (todos).
        assert status is None
        return [types.SimpleNamespace(**row) for row in history_rows], 12

    monkeypatch.setattr(
        "app.api.routes.history.list_user_analysis_history",
        fake_list_user_analysis_history,
    )

    async def fake_count_history_verdict_facets(
        *, user_id, search_query, source_type, created_after
    ):
        # Los facets ignoran el filtro de veredicto; conservan el resto de filtros.
        assert user_id == "test-user"
        assert search_query == "vacuna"
        assert source_type == "text"
        assert created_after is not None
        return {"total": 12, "real": 3, "fake": 8, "uncertain": 1}

    monkeypatch.setattr(
        "app.api.routes.history.count_history_verdict_facets",
        fake_count_history_verdict_facets,
    )

    async def fake_count_history_source_type_facets(
        *, user_id, search_query, verdict, created_after
    ):
        # Los facets de tipo ignoran el filtro de tipo; conservan el resto.
        assert user_id == "test-user"
        assert search_query == "vacuna"
        assert verdict == "fake"
        assert created_after is not None
        return {"total": 12, "text": 7, "url": 3, "file": 2}

    monkeypatch.setattr(
        "app.api.routes.history.count_history_source_type_facets",
        fake_count_history_source_type_facets,
    )

    response = client.get(
        "/history?page=1&page_size=10&search=vacuna&source_type=text"
        "&verdict=fake&date_range=30d&sort=credibility_high"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["count"] == 12
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["items"][0]["user_id"] == "test-user"
    assert body["items"][0]["source_type"] == "text"
    # El listado debe conservar el nombre del archivo (no descartarlo en la ruta).
    assert body["items"][0]["file_filename"] == "documento.pdf"
    # Conteos globales por veredicto para las tarjetas (independientes de la página).
    assert body["verdict_counts"] == {
        "total": 12,
        "real": 3,
        "fake": 8,
        "uncertain": 1,
    }
    # Conteos globales por tipo de fuente para los chips (independientes de la página).
    assert body["source_type_counts"] == {
        "total": 12,
        "text": 7,
        "url": 3,
        "file": 2,
    }


def test_historial_forwards_status_filter(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_list_user_analysis_history(*, status, **kwargs):
        assert status == "failed"
        return [], 0

    monkeypatch.setattr(
        "app.api.routes.history.list_user_analysis_history",
        fake_list_user_analysis_history,
    )

    async def fake_count_history_verdict_facets(**kwargs):
        return {"total": 0, "real": 0, "fake": 0, "uncertain": 0}

    monkeypatch.setattr(
        "app.api.routes.history.count_history_verdict_facets",
        fake_count_history_verdict_facets,
    )

    async def fake_count_history_source_type_facets(**kwargs):
        return {"total": 0, "text": 0, "url": 0, "file": 0}

    monkeypatch.setattr(
        "app.api.routes.history.count_history_source_type_facets",
        fake_count_history_source_type_facets,
    )

    response = client.get("/history?status=failed")

    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_historial_returns_500_when_database_fails(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_list_user_analysis_history(**kwargs):
        raise DatabaseError("db down")

    monkeypatch.setattr(
        "app.api.routes.history.list_user_analysis_history",
        fake_list_user_analysis_history,
    )

    response = client.get("/history")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "HISTORY_FETCH_FAILED"


def test_dashboard_summary_returns_summary(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    summary = types.SimpleNamespace(
        status="success",
        kpis=types.SimpleNamespace(
            total_analyses=23,
            reliable_rate=61.5,
            average_confidence=74.2,
            week_over_week_delta=15.0,
            active_alerts=7,
        ),
        verdict_distribution=types.SimpleNamespace(
            real=10,
            uncertain=6,
            fake=7,
        ),
        trend=[
            types.SimpleNamespace(
                date="2026-04-10",
                total=3,
                average_confidence=71.0,
            )
        ],
        source_breakdown=[
            types.SimpleNamespace(
                source_type="url",
                total=8,
                average_confidence=68.3,
            )
        ],
        domain_breakdown=[
            types.SimpleNamespace(
                domain="ejemplo.com",
                total=4,
                average_confidence=66.2,
            )
        ],
        alerts=[
            types.SimpleNamespace(
                id="11111111-1111-1111-1111-111111111111",
                source_type="url",
                input_text=None,
                input_url="https://ejemplo.com/nota",
                label="falsa",
                confidence=0.2,
                created_at="2026-04-10T12:00:00+00:00",
            )
        ],
    )

    async def fake_get_user_dashboard_summary(*, user_id, trend_days=14):
        assert user_id == "test-user"
        assert trend_days == 14
        return summary

    monkeypatch.setattr(
        "app.api.routes.dashboard.get_user_dashboard_summary",
        fake_get_user_dashboard_summary,
    )

    response = client.get("/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["kpis"]["total_analyses"] == 23
    assert body["kpis"]["active_alerts"] == 7
    assert body["verdict_distribution"] == {"real": 10, "uncertain": 6, "fake": 7}
    assert body["trend"][0]["date"] == "2026-04-10"
    assert body["source_breakdown"][0]["source_type"] == "url"
    assert body["domain_breakdown"][0]["domain"] == "ejemplo.com"
    assert body["alerts"][0]["label"] == "falsa"


def test_historial_export_returns_csv(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    records = [
        types.SimpleNamespace(
            source_type="url",
            input_text=None,
            input_url="https://ejemplo.com/nota",
            label="falsa",
            confidence=0.88,
            credibility=12,
            created_at="2026-04-10T12:00:00+00:00",
        ),
        types.SimpleNamespace(
            source_type="text",
            input_text="Una afirmación médica",
            input_url=None,
            label="verdadera",
            confidence=0.9,
            credibility=90,
            created_at="2026-04-11T08:30:00+00:00",
        ),
    ]

    async def fake_export_user_analysis_history(
        *, user_id, search_query, source_type, created_after, sort, verdict
    ):
        assert user_id == "test-user"
        assert search_query == "vacuna"
        assert source_type == "url"
        assert created_after is not None
        assert sort == "credibility_low"
        assert verdict == "real"
        return records

    monkeypatch.setattr(
        "app.api.routes.history.export_user_analysis_history",
        fake_export_user_analysis_history,
    )

    response = client.get(
        "/history/export?search=vacuna&source_type=url"
        "&verdict=real&date_range=30d&sort=credibility_low"
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert "historial-veritrust.csv" in response.headers["content-disposition"]

    body = response.content.decode("utf-8-sig")
    lines = body.strip().splitlines()
    assert lines[0] == "Fecha,Tipo,Entrada,Veredicto,Credibilidad"
    assert "https://ejemplo.com/nota,Falsa,12" in lines[1]
    assert "Una afirmación médica,Verdadera,90" in lines[2]


def test_historial_export_neutralizes_csv_formula(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    records = [
        types.SimpleNamespace(
            source_type="text",
            # Payload de inyección: al abrir en Excel ejecutaría la fórmula sin el prefijo.
            input_text="=cmd|'/c calc'!A1",
            input_url=None,
            label="falsa",
            confidence=0.5,
            credibility=10,
            created_at="2026-04-12T09:00:00+00:00",
        ),
    ]

    async def fake_export_user_analysis_history(**kwargs):
        return records

    monkeypatch.setattr(
        "app.api.routes.history.export_user_analysis_history",
        fake_export_user_analysis_history,
    )

    response = client.get("/history/export")

    assert response.status_code == 200
    body = response.content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(body)))
    # La celda "Entrada" (índice 2) queda inerte con la comilla simple antepuesta.
    assert rows[1][2] == "'=cmd|'/c calc'!A1"


def test_historial_export_returns_500_when_database_fails(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_export_user_analysis_history(**kwargs):
        raise DatabaseError("db down")

    monkeypatch.setattr(
        "app.api.routes.history.export_user_analysis_history",
        fake_export_user_analysis_history,
    )

    response = client.get("/history/export")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "HISTORY_FETCH_FAILED"


def test_dashboard_summary_returns_500_when_database_fails(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get_user_dashboard_summary(*, user_id, trend_days=14):
        raise DatabaseError("db down")

    monkeypatch.setattr(
        "app.api.routes.dashboard.get_user_dashboard_summary",
        fake_get_user_dashboard_summary,
    )

    response = client.get("/dashboard/summary")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "DASHBOARD_FETCH_FAILED"


def test_dashboard_summary_forwards_trend_days(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    received: dict = {}

    async def fake_get_user_dashboard_summary(*, user_id, trend_days=14):
        received["trend_days"] = trend_days
        return types.SimpleNamespace(
            status="success",
            kpis=types.SimpleNamespace(
                total_analyses=0,
                reliable_rate=0.0,
                average_confidence=0.0,
                week_over_week_delta=0.0,
                active_alerts=0,
            ),
            verdict_distribution=types.SimpleNamespace(real=0, uncertain=0, fake=0),
            trend=[],
            source_breakdown=[],
            domain_breakdown=[],
            alerts=[],
        )

    monkeypatch.setattr(
        "app.api.routes.dashboard.get_user_dashboard_summary",
        fake_get_user_dashboard_summary,
    )

    response = client.get("/dashboard/summary", params={"trend_days": 30})

    assert response.status_code == 200
    assert received["trend_days"] == 30


def test_dashboard_summary_rejects_out_of_range_trend_days(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.get("/dashboard/summary", params={"trend_days": 365})

    assert response.status_code == 422


_MINIMAL_PDF = b"%PDF-1.4 minimal content"


def test_analisis_file_enqueues_job_and_returns_pending(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_create_pending_file_analysis(**kwargs):
        assert kwargs["user_id"] == "test-user"
        assert kwargs["filename"] == "informe.pdf"
        assert kwargs["data"].startswith(b"%PDF")
        return "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(
        "app.api.routes.analysis.create_pending_file_analysis",
        fake_create_pending_file_analysis,
    )

    response = client.post(
        "/analysis/file",
        files={"file": ("informe.pdf", _MINIMAL_PDF, "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    job = fake_pool.jobs[0]
    assert job[0] == "run_analysis"
    assert job[1] == "11111111-1111-1111-1111-111111111111"
    assert job[2] == "file"
    assert job[3] is None
    assert job[4] is None
    # _job_id=analysis_id: arq deduplica encolados dobles del mismo análisis.
    assert fake_pool.job_ids == ["11111111-1111-1111-1111-111111111111"]


def test_analisis_file_accepts_plain_text(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_create_pending_file_analysis(**kwargs):
        assert kwargs["filename"] == "nota.txt"
        return "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(
        "app.api.routes.analysis.create_pending_file_analysis",
        fake_create_pending_file_analysis,
    )

    response = client.post(
        "/analysis/file",
        files={"file": ("nota.txt", b"texto plano a verificar", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert fake_pool.jobs[0][2] == "file"


def test_analisis_file_rejects_unsupported_type(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post(
        "/analysis/file",
        files={
            "file": (
                "documento.docx",
                b"PK\x03\x04 zip-ish",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "INVALID_FILE"


def test_analisis_file_rejects_oversized(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)
    monkeypatch.setattr(
        "app.api.routes.analysis.get_settings",
        lambda: types.SimpleNamespace(max_file_bytes=10),
    )

    response = client.post(
        "/analysis/file",
        files={"file": ("big.pdf", b"%PDF-1.4" + b"x" * 100, "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "FILE_TOO_LARGE"


def test_get_file_returns_file(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get_analysis_file(*, user_id, analysis_id):
        assert user_id == "test-user"
        return (b"%PDF-1.4 data", "informe.pdf")

    monkeypatch.setattr(
        "app.api.routes.analysis.get_analysis_file", fake_get_analysis_file
    )

    response = client.get("/analysis/11111111-1111-1111-1111-111111111111/file")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-1.4 data"
    assert "informe.pdf" in response.headers["content-disposition"]


def test_get_file_handles_non_latin1_filename(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get_analysis_file(*, user_id, analysis_id):
        # Em dash y emoji no caben en latin-1: antes reventaban la respuesta.
        return (b"%PDF-1.4 data", "informe—salud☕.pdf")

    monkeypatch.setattr(
        "app.api.routes.analysis.get_analysis_file", fake_get_analysis_file
    )

    response = client.get("/analysis/11111111-1111-1111-1111-111111111111/file")

    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 data"
    disposition = response.headers["content-disposition"]
    # El nombre real viaja percent-encoded en filename*; el fallback ASCII no rompe.
    assert "filename*=UTF-8''" in disposition
    assert "%E2%80%94" in disposition


def test_get_file_returns_404_when_missing(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get_analysis_file(*, user_id, analysis_id):
        return None

    monkeypatch.setattr(
        "app.api.routes.analysis.get_analysis_file", fake_get_analysis_file
    )

    response = client.get("/analysis/11111111-1111-1111-1111-111111111111/file")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ANALYSIS_NOT_FOUND"


def test_get_file_returns_400_when_id_invalid(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.get("/analysis/not-a-uuid/file")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_ANALYSIS_ID"


_SHARE_ID = "11111111-1111-1111-1111-111111111111"


def test_share_creates_link_and_returns_token(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        assert user_id == "test-user"
        return _failed_record(status="done")

    async def fake_set(*, user_id, analysis_id):
        return "tok_abc123"

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)
    monkeypatch.setattr("app.api.routes.analysis.set_analysis_share_token", fake_set)

    response = client.post(f"/analysis/{_SHARE_ID}/share")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "shared"
    assert body["share_token"] == "tok_abc123"


def test_share_returns_409_when_not_done(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        return _failed_record(status="pending")

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)

    response = client.post(f"/analysis/{_SHARE_ID}/share")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ANALYSIS_NOT_SHAREABLE"


def test_share_returns_404_when_not_found(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        return None

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)

    response = client.post(f"/analysis/{_SHARE_ID}/share")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ANALYSIS_NOT_FOUND"


def test_share_returns_409_when_set_loses_race(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        return _failed_record(status="done")

    async def fake_set(*, user_id, analysis_id):
        return None

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)
    monkeypatch.setattr("app.api.routes.analysis.set_analysis_share_token", fake_set)

    response = client.post(f"/analysis/{_SHARE_ID}/share")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ANALYSIS_NOT_SHAREABLE"


def test_share_returns_400_when_id_invalid(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post("/analysis/not-a-uuid/share")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_ANALYSIS_ID"


def test_unshare_returns_200_when_cleared(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_clear(*, user_id, analysis_id):
        assert user_id == "test-user"
        return True

    monkeypatch.setattr(
        "app.api.routes.analysis.clear_analysis_share_token", fake_clear
    )

    response = client.delete(f"/analysis/{_SHARE_ID}/share")

    assert response.status_code == 200
    assert response.json()["status"] == "unshared"


def test_unshare_returns_404_when_not_found(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_clear(*, user_id, analysis_id):
        return False

    monkeypatch.setattr(
        "app.api.routes.analysis.clear_analysis_share_token", fake_clear
    )

    response = client.delete(f"/analysis/{_SHARE_ID}/share")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ANALYSIS_NOT_FOUND"


def test_shared_report_returns_public_view_without_user_id(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get_shared(*, token):
        assert token == "tok_abc123"
        return PublicAnalysisReport(
            source_type="text",
            input_text="Bleach cures COVID",
            label="falsa",
            confidence=0.9,
            explanation="Sin respaldo científico.",
            status="done",
            created_at="2026-06-01T00:00:00+00:00",
        )

    monkeypatch.setattr(
        "app.api.routes.share.get_shared_analysis_by_token", fake_get_shared
    )

    response = client.get("/shared/tok_abc123")

    assert response.status_code == 200
    body = response.json()
    assert "user_id" not in body
    assert "share_token" not in body
    assert body["verdict"] == "fake"
    assert body["input_text"] == "Bleach cures COVID"


def test_shared_report_returns_404_for_unknown_token(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get_shared(*, token):
        return None

    monkeypatch.setattr(
        "app.api.routes.share.get_shared_analysis_by_token", fake_get_shared
    )

    response = client.get("/shared/unknown-token")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SHARED_REPORT_NOT_FOUND"


def test_analisis_file_fails_row_and_returns_503_when_enqueue_fails(monkeypatch):
    """Redis caído tras guardar el archivo: la fila pasa a failed y el cliente recibe 503."""
    server_module, _ = _load_server_module(monkeypatch)

    class _BrokenArqPool(_FakeArqPool):
        async def enqueue_job(self, *args, **kwargs):
            raise RedisError("redis down")

    server_module.app.state.arq_pool = _BrokenArqPool()
    client = TestClient(server_module.app)

    async def fake_create_pending_file_analysis(**kwargs):
        return "11111111-1111-1111-1111-111111111111"

    failed = []

    async def fake_fail_analysis(**kwargs):
        failed.append(kwargs)

    monkeypatch.setattr(
        "app.api.routes.analysis.create_pending_file_analysis",
        fake_create_pending_file_analysis,
    )
    monkeypatch.setattr("app.api.routes.analysis.fail_analysis", fake_fail_analysis)

    response = client.post(
        "/analysis/file",
        files={"file": ("informe.pdf", _MINIMAL_PDF, "application/pdf")},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SERVICE_UNAVAILABLE"
    assert failed == [
        {
            "analysis_id": "11111111-1111-1111-1111-111111111111",
            "error_code": "SERVICE_UNAVAILABLE",
        }
    ]


def test_analisis_file_returns_503_when_pool_unavailable(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    server_module.app.state.arq_pool = None
    client = TestClient(server_module.app)

    response = client.post(
        "/analysis/file",
        files={"file": ("informe.pdf", _MINIMAL_PDF, "application/pdf")},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SERVICE_UNAVAILABLE"


def test_analisis_file_rejects_empty_file(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post(
        "/analysis/file",
        files={"file": ("nota.txt", b"", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "INVALID_FILE"
    assert fake_pool.jobs == []


def test_analisis_file_rejects_pdf_without_signature(monkeypatch):
    """Un .pdf sin firma %PDF se rechaza antes de guardar nada ni encolar trabajo."""
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post(
        "/analysis/file",
        files={"file": ("falso.pdf", b"contenido cualquiera", "application/pdf")},
    )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "INVALID_FILE"
    assert fake_pool.jobs == []


def test_analisis_file_returns_save_failed_when_insert_fails(monkeypatch):
    server_module, fake_pool = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_create_pending_file_analysis(**kwargs):
        raise DatabaseError("db down")

    monkeypatch.setattr(
        "app.api.routes.analysis.create_pending_file_analysis",
        fake_create_pending_file_analysis,
    )

    response = client.post(
        "/analysis/file",
        files={"file": ("informe.pdf", _MINIMAL_PDF, "application/pdf")},
    )

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "ANALYSIS_SAVE_FAILED"
    assert fake_pool.jobs == []


def test_analisis_returns_503_when_enqueue_and_fail_update_both_fail(monkeypatch):
    """Redis y la BD caídos a la vez: el cliente sigue recibiendo un 503, no un 500 opaco."""
    server_module, _ = _load_server_module(monkeypatch)

    class _BrokenArqPool(_FakeArqPool):
        async def enqueue_job(self, *args, **kwargs):
            raise ConnectionResetError("socket perdido")

    server_module.app.state.arq_pool = _BrokenArqPool()
    client = TestClient(server_module.app)

    async def fake_create_pending_analysis(**kwargs):
        return "11111111-1111-1111-1111-111111111111"

    async def broken_fail_analysis(**kwargs):
        raise DatabaseError("db down")

    monkeypatch.setattr(
        "app.api.routes.analysis.create_pending_analysis",
        fake_create_pending_analysis,
    )
    monkeypatch.setattr("app.api.routes.analysis.fail_analysis", broken_fail_analysis)

    response = client.post("/analysis", json={"text": "Bleach cures COVID"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SERVICE_UNAVAILABLE"


def test_retry_returns_503_when_reenqueue_and_fail_update_both_fail(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)

    class _BrokenArqPool(_FakeArqPool):
        async def enqueue_job(self, *args, **kwargs):
            raise RedisError("redis down")

    server_module.app.state.arq_pool = _BrokenArqPool()
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        return _failed_record()

    async def fake_reset(*, user_id, analysis_id):
        return True

    async def broken_fail_analysis(**kwargs):
        raise DatabaseError("db down")

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)
    monkeypatch.setattr(
        "app.api.routes.analysis.reset_failed_analysis_to_pending", fake_reset
    )
    monkeypatch.setattr("app.api.routes.analysis.fail_analysis", broken_fail_analysis)

    response = client.post(f"/analysis/{_RETRY_ID}/retry")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SERVICE_UNAVAILABLE"


def test_share_returns_500_when_fetch_fails(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        raise DatabaseError("db down")

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)

    response = client.post(f"/analysis/{_SHARE_ID}/share")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "ANALYSIS_FETCH_FAILED"


def test_share_returns_500_when_set_token_fails(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get(*, user_id, analysis_id):
        return _failed_record(status="done")

    async def fake_set(*, user_id, analysis_id):
        raise DatabaseError("db down")

    monkeypatch.setattr("app.api.routes.analysis.get_user_analysis_by_id", fake_get)
    monkeypatch.setattr("app.api.routes.analysis.set_analysis_share_token", fake_set)

    response = client.post(f"/analysis/{_SHARE_ID}/share")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "SHARE_FAILED"


def test_unshare_returns_500_when_clear_fails(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_clear(*, user_id, analysis_id):
        raise DatabaseError("db down")

    monkeypatch.setattr(
        "app.api.routes.analysis.clear_analysis_share_token", fake_clear
    )

    response = client.delete(f"/analysis/{_SHARE_ID}/share")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "SHARE_FAILED"


def test_unshare_returns_400_when_id_invalid(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.delete("/analysis/not-a-uuid/share")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_ANALYSIS_ID"


def test_get_file_returns_500_when_database_fails(monkeypatch):
    server_module, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    async def fake_get_analysis_file(*, user_id, analysis_id):
        raise DatabaseError("db down")

    monkeypatch.setattr(
        "app.api.routes.analysis.get_analysis_file", fake_get_analysis_file
    )

    response = client.get("/analysis/11111111-1111-1111-1111-111111111111/file")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "ANALYSIS_FETCH_FAILED"


async def test_lifespan_opens_and_closes_web_queue_resources(monkeypatch):
    """El lifespan del proceso web abre BD + pool de arq y los cierra en orden inverso."""
    server_module, _ = _load_server_module(monkeypatch)
    opened: list[str] = []
    closed: list[str] = []

    class _Pool:
        async def close(self):
            closed.append("arq")

    class _Redis:
        async def aclose(self):
            closed.append("redis")

    async def fake_get_pool():
        opened.append("db")

    async def fake_create_pool(settings):
        opened.append("arq")
        return _Pool()

    async def fake_close_pool():
        closed.append("db")

    monkeypatch.setattr(server_module, "get_pool", fake_get_pool)
    monkeypatch.setattr(server_module, "create_pool", fake_create_pool)
    monkeypatch.setattr(server_module, "close_pool", fake_close_pool)
    monkeypatch.setattr(
        server_module,
        "aioredis",
        types.SimpleNamespace(from_url=lambda url: _Redis()),
    )
    monkeypatch.setattr(
        server_module,
        "get_settings",
        lambda: types.SimpleNamespace(
            redis_url="redis://localhost:6379",
            validate_runtime=lambda: None,
        ),
    )

    app_obj = types.SimpleNamespace(state=types.SimpleNamespace())
    async with server_module.lifespan(app_obj):
        assert opened == ["db", "arq"]
        assert app_obj.state.arq_pool is not None
        assert app_obj.state.redis is not None

    assert closed == ["arq", "redis", "db"]
