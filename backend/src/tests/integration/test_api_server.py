"""Tests de integración para la API server, verificando endpoints y manejo de errores."""

import importlib
import sys
import types
from pathlib import Path
from fastapi.testclient import TestClient
from src.api import utils as api_utils
from src.api.messages import ERROR_INTERNAL, ERROR_NO_MEDICAL_CLAIMS


def _load_server_module(monkeypatch, invoke_result=None, invoke_error=None):
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    fake_agents_module = types.ModuleType("src.agents.main")
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

    fake_start_module = types.ModuleType("src.utils.start_ollama")

    def start_ollama():
        start_calls["count"] += 1

    fake_start_module.start_ollama = start_ollama

    fake_extract_module = types.ModuleType("src.utils.extract_text_from_url")

    class FakeURLExtractionError(Exception):
        pass

    fake_extract_module.URLExtractionError = FakeURLExtractionError
    fake_extract_module.extract_text_from_url = lambda url: "Texto extraído de la URL"

    monkeypatch.setitem(sys.modules, "src.agents.main", fake_agents_module)
    monkeypatch.setitem(sys.modules, "src.utils.start_ollama", fake_start_module)
    monkeypatch.setitem(
        sys.modules, "src.utils.extract_text_from_url", fake_extract_module
    )

    sys.modules.pop("src.api.server", None)
    server_module = importlib.import_module("src.api.server")

    # Evita que el rate limit se acumule entre tests
    api_utils.rate_limit.clear()
    server_module.app.dependency_overrides[server_module.get_current_user] = lambda: {
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

    response = client.post("/analisis", json={"text": "Bleach cures COVID"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["label"] == "falsa"
    assert body["confidence"] == 0.92
    assert "explanation" in body
    assert fake_graph.invocations[0]["input_text"] == "Bleach cures COVID"


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
        "/analisis",
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
        "/analisis",
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

    response = client.post("/analisis", json={"text": "Texto sin claim"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["message"] == ERROR_NO_MEDICAL_CLAIMS
    assert body["explanations"] == ""


def test_analisis_returns_500_on_unexpected_error(monkeypatch):
    server_module, _, _ = _load_server_module(
        monkeypatch, invoke_error=RuntimeError("graph failed")
    )
    client = TestClient(server_module.app)

    response = client.post("/analisis", json={"text": "Texto"})

    assert response.status_code == 500
    assert response.json()["detail"] == ERROR_INTERNAL


def test_analisis_returns_422_when_text_field_is_missing(monkeypatch):
    server_module, fake_graph, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post("/analisis", json={})

    assert response.status_code == 422
    assert fake_graph.invocations == []


def test_analisis_returns_422_when_text_and_url_are_both_sent(monkeypatch):
    server_module, fake_graph, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    response = client.post(
        "/analisis",
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
        "/analisis",
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
        "/analisis",
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

    empty_response = client.post("/analisis", json={"text": ""})
    whitespace_response = client.post("/analisis", json={"text": "   \n\t  "})

    assert empty_response.status_code == 422
    assert whitespace_response.status_code == 422
    assert fake_graph.invocations == []


def test_analisis_returns_422_when_text_is_too_long(monkeypatch):
    server_module, fake_graph, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)

    very_long_text = "a" * 10001
    response = client.post("/analisis", json={"text": very_long_text})

    assert response.status_code == 422
    assert fake_graph.invocations == []


def test_analisis_requires_auth_when_dependency_is_not_overridden(monkeypatch):
    server_module, _, _ = _load_server_module(monkeypatch)
    client = TestClient(server_module.app)
    server_module.app.dependency_overrides.pop(server_module.get_current_user, None)

    response = client.post("/analisis", json={"text": "Texto"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing Authorization header"
