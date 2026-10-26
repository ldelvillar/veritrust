"""Pruebas del adaptador de Stripe (``app/core/billing.py``) con un cliente y una BD de mentira."""

import hashlib
import hmac
import json
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
import stripe

from app.core import billing
from app.core.plans import SubscriptionRow
from tests.support.billing import PRICE_MONTHLY, PRICE_YEARLY, WEBHOOK_SECRET

USER = "user-a"
PERIOD_END = 1_798_761_600


class _Service:
    """Servicio de Stripe de mentira que registra los parámetros de cada llamada."""

    def __init__(self, result=None):
        self.result = result
        self.calls: list = []
        self.error: Exception | None = None

    async def _answer(self, call):
        self.calls.append(call)
        if self.error is not None:
            raise self.error
        return self.result

    async def create_async(self, params=None, options=None):
        return await self._answer(params)

    async def retrieve_async(self, object_id, params=None, options=None):
        return await self._answer(object_id)


class _CheckoutSessions(_Service):
    """Sesiones de Checkout de mentira, con las abiertas del cliente y las que caducan."""

    def __init__(self, result):
        super().__init__(result)
        self.open_ids: list[str] = []
        self.expired: list[str] = []

    async def list_async(self, params=None, options=None):
        assert params == {"customer": params["customer"], "status": "open"}
        return SimpleNamespace(data=[SimpleNamespace(id=i) for i in self.open_ids])

    async def expire_async(self, session_id, params=None, options=None):
        self.expired.append(session_id)


class _FakeStripe:
    """StripeClient de mentira; la verificación de firmas es la real del SDK."""

    def __init__(self):
        self.customers = _Service(SimpleNamespace(id="cus_new"))
        self.checkout = _CheckoutSessions(
            SimpleNamespace(url="https://checkout.stripe.test/s")
        )
        self.portal = _Service(SimpleNamespace(url="https://billing.stripe.test/p"))
        self.subscriptions = _Service(_subscription())
        self.v1 = SimpleNamespace(
            customers=self.customers,
            checkout=SimpleNamespace(sessions=self.checkout),
            billing_portal=SimpleNamespace(sessions=self.portal),
            subscriptions=self.subscriptions,
        )
        self.construct_event = stripe.StripeClient("sk_test_dummy").construct_event


class _FakeBillingDb:
    """Tablas de facturación en memoria con la misma interfaz que ``app.db.billing``."""

    def __init__(self):
        self.customers: dict[str, str] = {}
        self.subscriptions: dict[str, SubscriptionRow] = {}
        self.events: dict[str, str] = {}
        self.locked: list[str] = []

    async def get_customer_id(self, user_id):
        return self.customers.get(user_id)

    async def insert_customer(self, user_id, stripe_customer_id):
        return self.customers.setdefault(user_id, stripe_customer_id)

    async def user_id_for_customer(self, stripe_customer_id, conn=None):
        return next(
            (u for u, c in self.customers.items() if c == stripe_customer_id), None
        )

    async def upsert_subscription(self, row, conn=None):
        self.subscriptions[row.stripe_subscription_id] = row

    async def is_event_processed(self, event_id):
        return event_id in self.events

    async def record_event(self, event_id, event_type):
        self.events[event_id] = event_type

    @asynccontextmanager
    async def subscription_lock(self, stripe_subscription_id):
        self.locked.append(stripe_subscription_id)
        yield None


def _subscription(**overrides) -> stripe.Subscription:
    data = {
        "id": "sub_1",
        "object": "subscription",
        "customer": "cus_1",
        "status": "active",
        "cancel_at_period_end": False,
        "cancel_at": None,
        "metadata": {"clerk_user_id": USER},
        "items": {
            "object": "list",
            "data": [
                {
                    "id": "si_1",
                    "object": "subscription_item",
                    "current_period_end": PERIOD_END,
                    "price": {
                        "id": PRICE_MONTHLY,
                        "object": "price",
                        "recurring": {"interval": "month"},
                    },
                }
            ],
        },
    }
    data.update(overrides)
    return stripe.Subscription.construct_from(data, "sk_test_dummy")


@pytest.fixture
def fake_stripe(stripe_settings, monkeypatch):
    client = _FakeStripe()
    monkeypatch.setattr(billing, "_client", lambda: client)
    return client


@pytest.fixture
def fake_db(monkeypatch):
    db = _FakeBillingDb()
    monkeypatch.setattr(billing, "billing_db", db)
    return db


def _signed(event_type: str, obj: dict, event_id: str = "evt_1") -> tuple[bytes, str]:
    payload = json.dumps(
        {"id": event_id, "object": "event", "type": event_type, "data": {"object": obj}}
    ).encode()
    timestamp = int(time.time())
    signature = hmac.new(
        WEBHOOK_SECRET.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return payload, f"t={timestamp},v1={signature}"


async def test_checkout_stores_a_new_customer_before_opening_the_session(
    fake_stripe, fake_db
):
    url = await billing.create_checkout_session(USER, "a@example.com", "month")

    assert url == "https://checkout.stripe.test/s"
    assert fake_stripe.customers.calls == [
        {"metadata": {"clerk_user_id": USER}, "email": "a@example.com"}
    ]
    assert fake_db.customers == {USER: "cus_new"}
    params = fake_stripe.checkout.calls[0]
    assert params["customer"] == "cus_new"
    assert params["mode"] == "subscription"
    assert params["client_reference_id"] == USER
    assert params["subscription_data"] == {"metadata": {"clerk_user_id": USER}}
    assert params["line_items"] == [{"price": PRICE_MONTHLY, "quantity": 1}]
    assert params["automatic_tax"] == {"enabled": True}
    assert params["billing_address_collection"] == "required"
    assert params["tax_id_collection"] == {"enabled": True}
    assert params["allow_promotion_codes"] is False
    assert params["consent_collection"] == {"terms_of_service": "required"}
    assert (
        "https://veritrust.test/terminos-y-condiciones"
        in params["custom_text"]["terms_of_service_acceptance"]["message"]
    )
    assert params["success_url"] == "https://veritrust.test/app/cuenta?checkout=success"
    assert (
        params["cancel_url"] == "https://veritrust.test/app/cuenta?checkout=cancelled"
    )


async def test_checkout_reuses_the_stored_customer_and_the_yearly_price(
    fake_stripe, fake_db
):
    fake_db.customers[USER] = "cus_1"

    await billing.create_checkout_session(USER, None, "year")

    assert fake_stripe.customers.calls == []
    params = fake_stripe.checkout.calls[0]
    assert params["customer"] == "cus_1"
    assert params["line_items"] == [{"price": PRICE_YEARLY, "quantity": 1}]


async def test_checkout_expires_the_customers_other_open_sessions(fake_stripe, fake_db):
    fake_db.customers[USER] = "cus_1"
    fake_stripe.checkout.open_ids = ["cs_tab_1", "cs_tab_2"]

    await billing.create_checkout_session(USER, None, "month")

    assert fake_stripe.checkout.expired == ["cs_tab_1", "cs_tab_2"]
    assert len(fake_stripe.checkout.calls) == 1


async def test_checkout_translates_stripe_errors(fake_stripe, fake_db):
    fake_stripe.checkout.error = stripe.APIConnectionError("sin red")

    with pytest.raises(billing.BillingUnavailable):
        await billing.create_checkout_session(USER, None, "month")


async def test_portal_needs_a_stored_customer(fake_stripe, fake_db):
    with pytest.raises(billing.BillingAccountNotFound):
        await billing.create_portal_session(USER)

    fake_db.customers[USER] = "cus_1"

    assert await billing.create_portal_session(USER) == "https://billing.stripe.test/p"
    assert fake_stripe.portal.calls == [
        {
            "customer": "cus_1",
            "return_url": "https://veritrust.test/app/cuenta",
            "locale": "es",
        }
    ]


@pytest.mark.parametrize(
    ("payload", "signature"),
    [
        (b'{"id": "evt_1"}', None),
        (b'{"id": "evt_1"}', "t=1,v1=deadbeef"),
        (b"no es json", None),
    ],
)
async def test_webhook_rejects_unsigned_requests(
    fake_stripe, fake_db, payload, signature
):
    with pytest.raises(billing.InvalidWebhook):
        await billing.handle_webhook(payload, signature)

    assert fake_db.events == {}


async def test_webhook_rejects_a_body_changed_after_signing(fake_stripe, fake_db):
    payload, signature = _signed("customer.subscription.updated", {"id": "sub_1"})

    with pytest.raises(billing.InvalidWebhook):
        await billing.handle_webhook(payload.replace(b"sub_1", b"sub_2"), signature)


async def test_subscription_event_refetches_and_stores_the_subscription(
    fake_stripe, fake_db
):
    fake_db.customers[USER] = "cus_1"
    fake_stripe.subscriptions.result = _subscription(
        status="past_due", cancel_at=PERIOD_END
    )
    # El objeto embebido está desfasado: solo se usa su id.
    payload, signature = _signed(
        "customer.subscription.updated", {"id": "sub_1", "status": "active"}
    )

    await billing.handle_webhook(payload, signature)

    assert fake_stripe.subscriptions.calls == ["sub_1"]
    assert fake_db.locked == ["sub_1"]
    assert fake_db.subscriptions["sub_1"] == SubscriptionRow(
        stripe_subscription_id="sub_1",
        user_id=USER,
        status="past_due",
        price_id=PRICE_MONTHLY,
        billing_interval="month",
        current_period_end=datetime.fromtimestamp(PERIOD_END, UTC),
        cancel_at=datetime.fromtimestamp(PERIOD_END, UTC),
    )
    assert fake_db.events == {"evt_1": "customer.subscription.updated"}


@pytest.mark.parametrize(
    ("stripe_fields", "expected"),
    [
        ({}, None),
        ({"cancel_at_period_end": True}, PERIOD_END),
        ({"cancel_at": PERIOD_END - 86_400}, PERIOD_END - 86_400),
        ({"cancel_at_period_end": True, "cancel_at": PERIOD_END}, PERIOD_END),
    ],
)
async def test_sync_stores_the_scheduled_cancellation_date(
    fake_stripe, fake_db, stripe_fields, expected
):
    fake_stripe.subscriptions.result = _subscription(**stripe_fields)

    await billing.sync_subscription("sub_1")

    cancel_at = fake_db.subscriptions["sub_1"].cancel_at
    assert cancel_at == (
        None if expected is None else datetime.fromtimestamp(expected, UTC)
    )


async def test_checkout_completed_links_the_customer_and_syncs(fake_stripe, fake_db):
    payload, signature = _signed(
        "checkout.session.completed",
        {
            "id": "cs_1",
            "customer": "cus_1",
            "client_reference_id": USER,
            "subscription": "sub_1",
        },
    )

    await billing.handle_webhook(payload, signature)

    assert fake_db.customers == {USER: "cus_1"}
    assert fake_db.subscriptions["sub_1"].user_id == USER


async def test_invoice_event_syncs_its_parent_subscription(fake_stripe, fake_db):
    fake_db.customers[USER] = "cus_1"
    payload, signature = _signed(
        "invoice.payment_failed",
        {
            "id": "in_1",
            "parent": {
                "type": "subscription_details",
                "subscription_details": {"subscription": "sub_1"},
            },
        },
    )

    await billing.handle_webhook(payload, signature)

    assert fake_stripe.subscriptions.calls == ["sub_1"]


async def test_unhandled_event_is_recorded_without_syncing(fake_stripe, fake_db):
    payload, signature = _signed("customer.created", {"id": "cus_1"})

    await billing.handle_webhook(payload, signature)

    assert fake_stripe.subscriptions.calls == []
    assert fake_db.events == {"evt_1": "customer.created"}


async def test_processed_event_is_skipped(fake_stripe, fake_db):
    fake_db.events["evt_1"] = "customer.subscription.updated"
    payload, signature = _signed("customer.subscription.updated", {"id": "sub_1"})

    await billing.handle_webhook(payload, signature)

    assert fake_stripe.subscriptions.calls == []


async def test_failed_event_is_not_recorded_so_stripe_retries_it(fake_stripe, fake_db):
    fake_stripe.subscriptions.error = stripe.APIConnectionError("sin red")
    payload, signature = _signed("customer.subscription.updated", {"id": "sub_1"})

    with pytest.raises(billing.BillingUnavailable):
        await billing.handle_webhook(payload, signature)

    assert fake_db.events == {}


async def test_sync_falls_back_to_metadata_for_an_unknown_customer(
    fake_stripe, fake_db
):
    await billing.sync_subscription("sub_1")

    assert fake_db.subscriptions["sub_1"].user_id == USER


async def test_sync_skips_a_subscription_with_no_user(fake_stripe, fake_db):
    fake_stripe.subscriptions.result = _subscription(metadata={})

    await billing.sync_subscription("sub_1")

    assert fake_db.subscriptions == {}
