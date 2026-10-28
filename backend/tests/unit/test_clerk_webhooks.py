"""Pruebas del webhook de Clerk (``app/core/clerk_webhooks.py``) con firmas Svix reales."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from svix.webhooks import Webhook

from app.core import clerk_webhooks
from app.core.config import get_settings
from tests.support.billing import CLERK_WEBHOOK_SECRET

USER = "user_2abc"


@pytest.fixture(autouse=True)
def clerk_secret(monkeypatch):
    monkeypatch.setenv("CLERK_WEBHOOK_SECRET", CLERK_WEBHOOK_SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def forgotten(monkeypatch):
    """Sustituye la baja de facturación por la lista de usuarios dados de baja."""
    users: list[str] = []

    async def forget_user(user_id):
        users.append(user_id)

    monkeypatch.setattr(clerk_webhooks.billing, "forget_user", forget_user)
    return users


def _signed(
    event: dict, *, secret: str = CLERK_WEBHOOK_SECRET, sent_at: datetime | None = None
) -> tuple[bytes, dict[str, str]]:
    payload = json.dumps(event)
    timestamp = sent_at or datetime.now(UTC)
    signature = Webhook(secret).sign("msg_1", timestamp, payload)
    return payload.encode(), {
        "svix-id": "msg_1",
        "svix-timestamp": str(int(timestamp.timestamp())),
        "svix-signature": signature,
    }


def _user_deleted(user_id: str | None = USER) -> dict:
    data = {"deleted": True, "object": "user"}
    if user_id is not None:
        data["id"] = user_id
    return {"object": "event", "type": "user.deleted", "data": data}


async def test_a_deleted_user_loses_their_billing(forgotten):
    payload, headers = _signed(_user_deleted())

    await clerk_webhooks.handle_webhook(payload, headers)

    assert forgotten == [USER]


async def test_other_events_are_acknowledged_without_effect(forgotten):
    payload, headers = _signed(
        {"object": "event", "type": "user.created", "data": {"id": USER}}
    )

    await clerk_webhooks.handle_webhook(payload, headers)

    assert forgotten == []


async def test_a_user_deleted_event_without_an_id_is_skipped(forgotten):
    payload, headers = _signed(_user_deleted(user_id=None))

    await clerk_webhooks.handle_webhook(payload, headers)

    assert forgotten == []


def _tampered():
    payload, headers = _signed(_user_deleted())
    return payload.replace(USER.encode(), b"user_victim"), headers


def _wrong_secret():
    return _signed(_user_deleted(), secret="whsec_b3RybyBzZWNyZXRv")


def _stale():
    return _signed(_user_deleted(), sent_at=datetime.now(UTC) - timedelta(hours=1))


def _unsigned():
    payload, _ = _signed(_user_deleted())
    return payload, {}


def _malformed_signature():
    payload, headers = _signed(_user_deleted())
    return payload, {**headers, "svix-signature": "sin-coma"}


@pytest.mark.parametrize(
    "request_parts",
    [_tampered, _wrong_secret, _stale, _unsigned, _malformed_signature],
    ids=["tampered", "wrong-secret", "stale", "unsigned", "malformed"],
)
async def test_unsigned_or_altered_requests_are_rejected(forgotten, request_parts):
    payload, headers = request_parts()

    with pytest.raises(clerk_webhooks.InvalidClerkWebhook):
        await clerk_webhooks.handle_webhook(payload, headers)

    assert forgotten == []
