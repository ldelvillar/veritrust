"""Tests de integración del endpoint público POST /contact."""

import importlib
import sys
from pathlib import Path

import fakeredis
from fastapi.testclient import TestClient

from app.utils.email import ContactEmailError, ContactEmailNotConfigured


class _LoopSafeFakeRedis:
    """Redis de mentira resistente al cambio de event loop del TestClient."""

    def __init__(self):
        self._server = fakeredis.FakeServer()

    def pipeline(self, *args, **kwargs):
        client = fakeredis.aioredis.FakeRedis(server=self._server)
        return client.pipeline(*args, **kwargs)


def _load_server_module():
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    sys.modules.pop("app.main", None)
    server_module = importlib.import_module("app.main")

    # TestClient(app) no ejecuta el lifespan; inyectamos un Redis fresco por test.
    server_module.app.state.redis = _LoopSafeFakeRedis()
    return server_module


_VALID_BODY = {
    "type": "contact",
    "name": "Ana",
    "email": "ana@medio.es",
    "subject": "Consulta general",
    "message": "¿Cómo funciona el análisis?",
}


def test_contact_returns_sent_and_forwards_fields(monkeypatch):
    server_module = _load_server_module()
    client = TestClient(server_module.app)

    received: dict = {}

    async def fake_send_contact_email(**kwargs):
        received.update(kwargs)

    monkeypatch.setattr(
        "app.api.routes.contact.send_contact_email", fake_send_contact_email
    )

    response = client.post("/contact", json=_VALID_BODY)

    assert response.status_code == 200
    assert response.json() == {"status": "sent"}
    assert received["name"] == "Ana"
    assert received["email"] == "ana@medio.es"
    assert received["contact_type"] == "contact"


def test_contact_forwards_demo_metadata(monkeypatch):
    server_module = _load_server_module()
    client = TestClient(server_module.app)

    received: dict = {}

    async def fake_send_contact_email(**kwargs):
        received.update(kwargs)

    monkeypatch.setattr(
        "app.api.routes.contact.send_contact_email", fake_send_contact_email
    )

    response = client.post(
        "/contact",
        json={
            "type": "demo",
            "name": "Ana",
            "email": "ana@medio.es",
            "subject": "Medio S.L.",
            "metadata": {"Organización": "Medio S.L.", "Cargo": ""},
        },
    )

    assert response.status_code == 200
    assert received["contact_type"] == "demo"
    assert received["message"] is None
    # Los valores vacíos del metadata se descartan en la validación del esquema.
    assert received["metadata"] == {"Organización": "Medio S.L."}


def test_contact_returns_422_when_name_missing(monkeypatch):
    server_module = _load_server_module()
    client = TestClient(server_module.app)

    called = []

    async def fake_send_contact_email(**kwargs):
        called.append(kwargs)

    monkeypatch.setattr(
        "app.api.routes.contact.send_contact_email", fake_send_contact_email
    )

    response = client.post("/contact", json={**_VALID_BODY, "name": "   "})

    assert response.status_code == 422
    assert called == []


def test_contact_returns_422_when_email_invalid(monkeypatch):
    server_module = _load_server_module()
    client = TestClient(server_module.app)

    response = client.post("/contact", json={**_VALID_BODY, "email": "no-es-email"})

    assert response.status_code == 422


def test_contact_returns_503_when_email_not_configured(monkeypatch):
    server_module = _load_server_module()
    client = TestClient(server_module.app)

    async def fake_send_contact_email(**kwargs):
        raise ContactEmailNotConfigured

    monkeypatch.setattr(
        "app.api.routes.contact.send_contact_email", fake_send_contact_email
    )

    response = client.post("/contact", json=_VALID_BODY)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SERVICE_UNAVAILABLE"


def test_contact_returns_500_when_send_fails(monkeypatch):
    server_module = _load_server_module()
    client = TestClient(server_module.app)

    async def fake_send_contact_email(**kwargs):
        raise ContactEmailError

    monkeypatch.setattr(
        "app.api.routes.contact.send_contact_email", fake_send_contact_email
    )

    response = client.post("/contact", json=_VALID_BODY)

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "CONTACT_SEND_FAILED"


def test_contact_returns_429_when_rate_limit_exceeded(monkeypatch):
    server_module = _load_server_module()
    client = TestClient(server_module.app)

    async def fake_send_contact_email(**kwargs):
        return None

    monkeypatch.setattr(
        "app.api.routes.contact.send_contact_email", fake_send_contact_email
    )

    # El límite por defecto es 5 peticiones por IP y ventana: las 5 primeras pasan.
    for _ in range(5):
        ok = client.post("/contact", json=_VALID_BODY)
        assert ok.status_code == 200

    blocked = client.post("/contact", json=_VALID_BODY)

    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "RATE_LIMIT"
