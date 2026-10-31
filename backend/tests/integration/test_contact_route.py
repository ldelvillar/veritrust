"""Integration tests of the public POST /contact endpoint."""

import importlib
import sys
from pathlib import Path

import fakeredis
from fastapi.testclient import TestClient

from app.utils.email import ContactEmailError, ContactEmailNotConfigured


class _LoopSafeFakeRedis:
    """Fake Redis that survives the TestClient's event loop changes."""

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

    # TestClient(app) does not run the lifespan, so a fresh Redis is injected per test.
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
    # Empty metadata values are dropped by schema validation.
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

    # The default limit is 5 requests per IP and window, so the first 5 pass.
    for _ in range(5):
        ok = client.post("/contact", json=_VALID_BODY)
        assert ok.status_code == 200

    blocked = client.post("/contact", json=_VALID_BODY)

    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "RATE_LIMIT"


def test_contact_rate_limit_ignores_spoofed_forwarded_for_hops(monkeypatch):
    """Rotating X-Forwarded-For cannot grant quota, since only the hop the proxy adds counts."""
    server_module = _load_server_module()
    client = TestClient(server_module.app)

    async def fake_send_contact_email(**kwargs):
        return None

    monkeypatch.setattr(
        "app.api.routes.contact.send_contact_email", fake_send_contact_email
    )

    # Chain as Caddy delivers it, the client's value first and the real peer last.
    def post_from(spoofed: str, peer: str = "10.0.0.9"):
        return client.post(
            "/contact",
            json=_VALID_BODY,
            headers={"X-Forwarded-For": f"{spoofed}, {peer}"},
        )

    for spoofed in ("1.2.3.4", "5.6.7.8", "9.9.9.9", "4.4.4.4", "8.8.8.8"):
        assert post_from(spoofed).status_code == 200

    assert post_from("7.7.7.7").status_code == 429

    # Another peer keeps its quota, so the key still tells IPs apart and is not constant.
    assert post_from("1.2.3.4", peer="10.0.0.10").status_code == 200
