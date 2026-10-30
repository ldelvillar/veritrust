"""Tests de integración de los endpoints de facturación (/billing)."""

import importlib
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.get_current_user import get_current_user
from app.core import billing, clerk_webhooks
from app.core.plans import MADRID
from app.db.billing import Usage
from app.db.pool import DatabaseError
from tests.support.billing import PRICE_YEARLY, make_subscription

USER = "test-user"


def _subscription(status: str = "active"):
    return make_subscription(
        user_id=USER,
        status=status,
        price_id=PRICE_YEARLY,
        billing_interval="year",
        cancel_at=datetime(2027, 1, 15, tzinfo=UTC),
    )


@pytest.fixture
def client(stripe_settings):
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    sys.modules.pop("app.main", None)
    server_module = importlib.import_module("app.main")
    server_module.app.dependency_overrides[get_current_user] = lambda: {
        "sub": USER,
        "email": "test-user@example.com",
    }
    return TestClient(server_module.app)


@pytest.fixture
def subscription(monkeypatch):
    """Subscription que devuelve la BD de mentira; None por defecto (Free)."""
    state: dict = {"row": None, "usage": Usage(used=0, pending=0)}

    async def get_user_subscription(user_id):
        assert user_id == USER
        return state["row"]

    async def usage_this_month(user_id, start, end):
        state["window"] = (start, end)
        return state["usage"]

    monkeypatch.setattr(
        "app.api.routes.billing.get_user_subscription", get_user_subscription
    )
    monkeypatch.setattr("app.api.routes.billing.usage_this_month", usage_this_month)
    return state


def test_plan_of_a_user_without_subscription_is_free(client, subscription):
    subscription["usage"] = Usage(used=4, pending=1)

    response = client.get("/billing/plan")

    assert response.status_code == 200
    body = response.json()
    assert body["plan"] == "free"
    assert body["status"] is None
    assert body["interval"] is None
    assert body["cancel_at"] is None
    assert body["limits"]["analyses_per_month"] == 10
    assert body["limits"]["files"] is False
    assert body["usage"]["used"] == 4
    assert body["usage"]["pending"] == 1
    assert body["usage"]["remaining"] == 5
    start, end = subscription["window"]
    assert start.tzinfo == MADRID and start.day == 1
    assert datetime.fromisoformat(body["usage"]["resets_at"]) == end


def test_plan_of_a_subscriber_is_pro_with_its_subscription(client, subscription):
    subscription["row"] = _subscription()

    body = client.get("/billing/plan").json()

    assert body["plan"] == "pro"
    assert body["status"] == "active"
    assert body["interval"] == "year"
    assert datetime.fromisoformat(body["cancel_at"]) == datetime(
        2027, 1, 15, tzinfo=UTC
    )
    assert body["limits"]["analyses_per_month"] == 300
    assert body["limits"]["history_days"] is None
    assert body["usage"]["remaining"] == 300


def test_remaining_never_goes_negative(client, subscription):
    subscription["usage"] = Usage(used=10, pending=2)

    assert client.get("/billing/plan").json()["usage"]["remaining"] == 0


def test_plan_answers_500_when_the_database_fails(client, monkeypatch):
    async def fail(user_id):
        raise DatabaseError("db down")

    monkeypatch.setattr("app.api.routes.billing.get_user_subscription", fail)

    response = client.get("/billing/plan")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "BILLING_FETCH_FAILED"


def test_checkout_returns_the_stripe_url(client, subscription, monkeypatch):
    calls = []

    async def create_checkout_session(user_id, email, interval):
        calls.append((user_id, email, interval))
        return "https://checkout.stripe.test/s"

    monkeypatch.setattr(billing, "create_checkout_session", create_checkout_session)

    response = client.post("/billing/checkout", json={"interval": "year"})

    assert response.status_code == 200
    assert response.json() == {"url": "https://checkout.stripe.test/s"}
    assert calls == [(USER, "test-user@example.com", "year")]


@pytest.mark.parametrize("status", ["active", "past_due"])
def test_checkout_refuses_a_pro_user(client, subscription, status):
    subscription["row"] = _subscription(status)

    response = client.post("/billing/checkout", json={"interval": "month"})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ALREADY_SUBSCRIBED"


def test_checkout_lets_a_canceled_user_subscribe_again(
    client, subscription, monkeypatch
):
    subscription["row"] = _subscription("canceled")

    async def create_checkout_session(user_id, email, interval):
        return "https://checkout.stripe.test/s"

    monkeypatch.setattr(billing, "create_checkout_session", create_checkout_session)

    assert (
        client.post("/billing/checkout", json={"interval": "month"}).status_code == 200
    )


def test_checkout_rejects_an_unknown_interval(client, subscription):
    response = client.post("/billing/checkout", json={"interval": "week"})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "VALIDATION"


def test_checkout_answers_503_when_stripe_fails(client, subscription, monkeypatch):
    async def fail(user_id, email, interval):
        raise billing.BillingUnavailable("sin red")

    monkeypatch.setattr(billing, "create_checkout_session", fail)

    response = client.post("/billing/checkout", json={"interval": "month"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "BILLING_UNAVAILABLE"


def test_portal_returns_the_stripe_url(client, monkeypatch):
    async def create_portal_session(user_id):
        return f"https://billing.stripe.test/{user_id}"

    monkeypatch.setattr(billing, "create_portal_session", create_portal_session)

    response = client.post("/billing/portal")

    assert response.status_code == 200
    assert response.json() == {"url": f"https://billing.stripe.test/{USER}"}


def test_portal_answers_404_without_a_customer(client, monkeypatch):
    async def missing(user_id):
        raise billing.BillingAccountNotFound(user_id)

    monkeypatch.setattr(billing, "create_portal_session", missing)

    response = client.post("/billing/portal")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "BILLING_ACCOUNT_NOT_FOUND"


def test_webhook_passes_the_raw_body_and_signature(client, monkeypatch):
    received = []

    async def handle_webhook(payload, signature):
        received.append((payload, signature))

    monkeypatch.setattr(billing, "handle_webhook", handle_webhook)
    raw = b'{"id": "evt_1",  "type": "invoice.paid"}'

    response = client.post(
        "/billing/webhook",
        content=raw,
        headers={"Stripe-Signature": "t=1,v1=abc", "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json() == {"received": True}
    assert received == [(raw, "t=1,v1=abc")]


def test_webhook_needs_no_user_token(client, monkeypatch):
    client.app.dependency_overrides.clear()

    async def handle_webhook(payload, signature):
        return None

    monkeypatch.setattr(billing, "handle_webhook", handle_webhook)

    assert client.post("/billing/webhook", content=b"{}").status_code == 200


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (billing.InvalidWebhook("firma"), 400, "INVALID_WEBHOOK"),
        (billing.BillingUnavailable("sin red"), 503, "BILLING_UNAVAILABLE"),
        (DatabaseError("db down"), 500, "BILLING_FETCH_FAILED"),
    ],
)
def test_webhook_failures_answer_non_2xx_so_stripe_retries(
    client, monkeypatch, error, status, code
):
    async def handle_webhook(payload, signature):
        raise error

    monkeypatch.setattr(billing, "handle_webhook", handle_webhook)

    response = client.post("/billing/webhook", content=b"{}")

    assert response.status_code == status
    assert response.json()["detail"]["code"] == code


def test_clerk_webhook_passes_the_raw_body_and_headers_without_a_user(
    client, monkeypatch
):
    client.app.dependency_overrides.clear()
    received = []

    async def handle_webhook(payload, headers, intake):
        received.append((payload, headers["svix-id"]))

    monkeypatch.setattr(clerk_webhooks, "handle_webhook", handle_webhook)
    raw = b'{"type": "user.deleted",  "data": {"id": "user_1"}}'

    response = client.post(
        "/webhooks/clerk",
        content=raw,
        headers={"svix-id": "msg_1", "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json() == {"received": True}
    assert received == [(raw, "msg_1")]


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (clerk_webhooks.InvalidClerkWebhook("firma"), 400, "INVALID_WEBHOOK"),
        (billing.BillingUnavailable("sin red"), 503, "BILLING_UNAVAILABLE"),
        (DatabaseError("db down"), 500, "BILLING_FETCH_FAILED"),
    ],
)
def test_clerk_webhook_failures_answer_non_2xx_so_clerk_retries(
    client, monkeypatch, error, status, code
):
    async def handle_webhook(payload, headers, intake):
        raise error

    monkeypatch.setattr(clerk_webhooks, "handle_webhook", handle_webhook)

    response = client.post("/webhooks/clerk", content=b"{}")

    assert response.status_code == status
    assert response.json()["detail"]["code"] == code


def test_billing_routes_require_a_user(client):
    client.app.dependency_overrides.clear()

    assert client.get("/billing/plan").status_code == 401
    assert (
        client.post("/billing/checkout", json={"interval": "month"}).status_code == 401
    )
    assert client.post("/billing/portal").status_code == 401


def test_resets_at_is_the_first_of_next_madrid_month(client, subscription):
    resets_at = datetime.fromisoformat(
        client.get("/billing/plan").json()["usage"]["resets_at"]
    )

    local = resets_at.astimezone(MADRID)
    assert (local.day, local.hour, local.minute) == (1, 0, 0)
