"""Tests de integración para la API server, verificando endpoints y manejo de errores."""

import importlib
import sys
import types

from pathlib import Path
from fastapi.testclient import TestClient

from app.api.dependencies.check_rate_limit import rate_limit
from app.api.dependencies.get_current_user import get_current_user
from app.db.main import HistoryDatabaseError


def _load_server_module(monkeypatch, invoke_result=None, invoke_error=None):
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    fake_agents_module = types.ModuleType("app.agents.main")
    start_calls = {"count": 0}

    class _FakeGraph:
        def __init__(self):
            self.invocations = []

        def invoke(self, state):
            self.invocations.append(state)
            if invoke_error is not None:
                raise invoke_error
            return invoke_result if invoke_result is not None else {}

    fake_graph = _FakeGraph()

    def create_graph():
        return fake_graph

    fake_agents_module.create_graph = create_graph

    fake_start_module = types.ModuleType("app.utils.ollama")

    def ensure_ollama_available():
        start_calls["count"] += 1

    fake_start_module.ensure_ollama_available = ensure_ollama_available

    fake_extract_module = types.ModuleType("app.utils.extract_text_from_url")

    class FakeURLExtractionError(Exception):
        pass

    fake_extract_module.URLExtractionError = FakeURLExtractionError
    fake_extract_module.extract_text_from_url = lambda url: "Texto extraído de la URL"

    monkeypatch.setitem(sys.modules, "app.agents.main", fake_agents_module)
    monkeypatch.setitem(sys.modules, "app.utils.ollama", fake_start_module)
    monkeypatch.setitem(
        sys.modules, "app.utils.extract_text_from_url", fake_extract_module
    )

    sys.modules.pop("app.main", None)
    server_module = importlib.import_module("app.main")

    server_module.app.state.verification_system = fake_graph
    start_calls["count"] += 1

    # Evita que el rate limit se acumule entre tests
    rate_limit.clear()
    server_module.app.dependency_overrides[get_current_user] = lambda: {
        "sub": "test-user"
    }

    return server_module, fake_graph, start_calls


def test_root_endpoint_returns_service_status(monkeypatch):
    server_module, _, start_calls = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "online"
    assert start_calls["count"] == 1


def test_analisis_returns_success_payload(monkeypatch):
    result = {
        "label": "falsa",
        "confidence": 0.92,
        "medical_explanation": "No hay evidencia clínica sólida.",
    }
    server_module, fake_graph, _ = _load_server_module(
        monkeypatch, invoke_result=result
    )
    client = TestClient(server_module.app)

    response = client.post("/analysis", json={"text": "Bleach cures COVID"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "analysis_id" in body
    assert body["label"] == "falsa"
    assert body["confidence"] == 0.92
    assert "explanation" in body
    assert fake_graph.invocations[0]["input_text"] == "Bleach cures COVID"


def test_analisis_saves_history_only_on_success(monkeypatch):
    result = {
        "label": "falsa",
        "confidence": 0.92,
        "medical_explanation": "No hay evidencia clínica sólida.",
    }
    server_module, _, _ = _load_server_module(monkeypatch, invoke_result=result)
    client = TestClient(server_module.app)

    calls = []

    def fake_save_successful_analysis(**kwargs):
        calls.append(kwargs)
        return "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(
        "app.api.routes.analysis.save_successful_analysis",
        fake_save_successful_analysis,
    )

    response = client.post("/analysis", json={"text": "Bleach cures COVID"})

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["analysis_id"] == "11111111-1111-1111-1111-111111111111"
    assert len(calls) == 1
    assert calls[0]["user_id"] == "test-user"


def test_analisis_does_not_save_history_when_explanation_is_empty(monkeypatch):
    result = {
        "label": "verdadera",
        "confidence": 0.6,
        "medical_explanation": "",
    }
    server_module, _, _ = _load_server_module(monkeypatch, invoke_result=result)
    client = TestClient(server_module.app)

    calls = []

    def fake_save_successful_analysis(**kwargs):
        calls.append(kwargs)
        return "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(
        "app.api.routes.analysis.save_successful_analysis",
        fake_save_successful_analysis,
    )

    response = client.post("/analysis", json={"text": "Texto sin claim"})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "NO_MEDICAL_CLAIMS"
    assert calls == []


def test_analisis_returns_success_with_url(monkeypatch):
    result = {
        "label": "verdadera",
        "confidence": 0.85,
        "medical_explanation": "El texto extraído contiene información correcta.",
    }
    server_module, fake_graph, _ = _load_server_module(
        monkeypatch, invoke_result=result
    )
    client = TestClient(server_module.app)

    response = client.post(
        "/analysis",
        json={"url": "https://ejemplo.com/noticia", "source_type": "url"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["label"] == "verdadera"
    assert body["confidence"] == 0.85
    assert "explanation" in body
    assert fake_graph.invocations[0]["input_text"] == "Texto extraído de la URL"


def test_analisis_rejects_invalid_url(monkeypatch):
    server_module, _, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post(
        "/analysis",
        json={"url": "not-a-valid-url", "source_type": "url"},
    )

    # Pydantic HttpUrl validation should fail with 422
    assert response.status_code == 422


def test_analisis_returns_warning_when_explanation_is_empty(monkeypatch):
    result = {
        "label": "verdadera",
        "confidence": 0.6,
        "medical_explanation": "",
    }
    server_module, _, _ = _load_server_module(monkeypatch, invoke_result=result)
    client = TestClient(server_module.app)

    response = client.post("/analysis", json={"text": "Texto sin claim"})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "NO_MEDICAL_CLAIMS"


def test_analisis_returns_500_on_unexpected_error(monkeypatch):
    server_module, _, _ = _load_server_module(
        monkeypatch, invoke_error=RuntimeError("graph failed")
    )
    client = TestClient(server_module.app)

    response = client.post("/analysis", json={"text": "Texto"})

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "INTERNAL"


def test_analisis_detail_returns_analysis_for_authenticated_user(monkeypatch):
    server_module, _, _ = _load_server_module(monkeypatch)
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
        created_at="2026-04-10T12:00:00+00:00",
    )

    def fake_get_user_analysis_by_id(*, user_id, analysis_id):
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


def test_analisis_detail_returns_404_when_not_found(monkeypatch):
    server_module, _, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    monkeypatch.setattr(
        "app.api.routes.analysis.get_user_analysis_by_id",
        lambda **kwargs: None,
    )

    response = client.get("/analysis/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ANALYSIS_NOT_FOUND"


def test_analisis_detail_returns_400_when_id_is_invalid(monkeypatch):
    server_module, _, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.get("/analysis/not-a-uuid")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_ANALYSIS_ID"


def test_analisis_detail_returns_500_when_database_fails(monkeypatch):
    server_module, _, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    def fake_get_user_analysis_by_id(*, user_id, analysis_id):
        raise HistoryDatabaseError("db down")

    monkeypatch.setattr(
        "app.api.routes.analysis.get_user_analysis_by_id",
        fake_get_user_analysis_by_id,
    )

    response = client.get("/analysis/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "ANALYSIS_FETCH_FAILED"


def test_analisis_returns_422_when_text_field_is_missing(monkeypatch):
    server_module, fake_graph, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post("/analysis", json={})

    assert response.status_code == 422
    assert fake_graph.invocations == []


def test_analisis_returns_422_when_text_and_url_are_both_sent(monkeypatch):
    server_module, fake_graph, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post(
        "/analysis",
        json={
            "text": "Un texto",
            "url": "https://ejemplo.com/noticia",
        },
    )

    assert response.status_code == 422
    assert fake_graph.invocations == []


def test_analisis_returns_422_when_url_has_non_url_source_type(monkeypatch):
    server_module, fake_graph, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post(
        "/analysis",
        json={
            "url": "https://ejemplo.com/noticia",
            "source_type": "text",
        },
    )

    assert response.status_code == 422
    assert fake_graph.invocations == []


def test_analisis_returns_422_when_text_has_url_source_type(monkeypatch):
    server_module, fake_graph, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post(
        "/analysis",
        json={
            "text": "Un texto",
            "source_type": "url",
        },
    )

    assert response.status_code == 422
    assert fake_graph.invocations == []


def test_analisis_returns_422_when_text_is_empty_or_whitespace(monkeypatch):
    server_module, fake_graph, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    empty_response = client.post("/analysis", json={"text": ""})
    whitespace_response = client.post("/analysis", json={"text": "   \n\t  "})

    assert empty_response.status_code == 422
    assert whitespace_response.status_code == 422
    assert fake_graph.invocations == []


def test_analisis_returns_422_when_text_is_too_long(monkeypatch):
    server_module, fake_graph, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    very_long_text = "a" * 10001
    response = client.post("/analysis", json={"text": very_long_text})

    assert response.status_code == 422
    assert fake_graph.invocations == []


def test_analisis_requires_auth_when_dependency_is_not_overridden(monkeypatch):
    server_module, _, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)
    server_module.app.dependency_overrides.pop(get_current_user, None)

    response = client.post("/analysis", json={"text": "Texto"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing Authorization header"


def test_historial_returns_user_history(monkeypatch):
    server_module, _, _ = _load_server_module(monkeypatch)
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
            "created_at": "2026-04-10T12:00:00+00:00",
        }
    ]

    def fake_list_user_analysis_history(
        *,
        user_id,
        limit,
        offset,
        search_query,
        source_type,
        created_after,
        score_sort_order,
    ):
        assert user_id == "test-user"
        assert limit == 10
        assert offset == 0
        assert search_query == "vacuna"
        assert source_type == "text"
        assert created_after is not None
        assert score_sort_order == "asc"
        return [types.SimpleNamespace(**row) for row in history_rows], 12

    monkeypatch.setattr(
        "app.api.routes.history.list_user_analysis_history",
        fake_list_user_analysis_history,
    )

    response = client.get(
        "/history?page=1&page_size=10&search=vacuna&source_type=text&date_range=30d&score_sort=asc"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["count"] == 12
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["items"][0]["user_id"] == "test-user"
    assert body["items"][0]["source_type"] == "text"


def test_historial_returns_500_when_database_fails(monkeypatch):
    server_module, _, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    def fake_list_user_analysis_history(**kwargs):
        raise HistoryDatabaseError("db down")

    monkeypatch.setattr(
        "app.api.routes.history.list_user_analysis_history",
        fake_list_user_analysis_history,
    )

    response = client.get("/history")

    assert response.status_code == 500
    assert "No se pudo recuperar el historial" in response.json()["detail"]


def test_dashboard_summary_returns_summary(monkeypatch):
    server_module, _, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    summary = types.SimpleNamespace(
        kpis=types.SimpleNamespace(
            total_analyses=23,
            reliable_rate=61.5,
            average_confidence=74.2,
            week_over_week_delta=15.0,
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

    def fake_get_user_dashboard_summary(*, user_id):
        assert user_id == "test-user"
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
    assert body["trend"][0]["date"] == "2026-04-10"
    assert body["source_breakdown"][0]["source_type"] == "url"
    assert body["domain_breakdown"][0]["domain"] == "ejemplo.com"
    assert body["alerts"][0]["label"] == "falsa"


def test_dashboard_summary_returns_500_when_database_fails(monkeypatch):
    server_module, _, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    def fake_get_user_dashboard_summary(*, user_id):
        raise HistoryDatabaseError("db down")

    monkeypatch.setattr(
        "app.api.routes.dashboard.get_user_dashboard_summary",
        fake_get_user_dashboard_summary,
    )

    response = client.get("/dashboard/summary")

    assert response.status_code == 500
    assert "No se pudo recuperar el dashboard" in response.json()["detail"]
