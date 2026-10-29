"""Datos de prueba de facturación compartidos: valores de Stripe de mentira y Subscriptions."""

from dataclasses import replace
from datetime import UTC, datetime

from app.core.plans import SubscriptionRow

PRICE_MONTHLY = "price_test_monthly"
PRICE_YEARLY = "price_test_yearly"
WEBHOOK_SECRET = "whsec_test_dummy"
# Los secretos de Svix son base64 tras el prefijo; este decodifica a b"clerk-test-dummy".
CLERK_WEBHOOK_SECRET = "whsec_Y2xlcmstdGVzdC1kdW1teQ=="

_SUBSCRIPTION = SubscriptionRow(
    stripe_subscription_id="sub_1",
    user_id="user-a",
    status="active",
    price_id=PRICE_MONTHLY,
    billing_interval="month",
    current_period_end=datetime(2026, 11, 26, tzinfo=UTC),
    cancel_at=None,
)


def make_subscription(**overrides) -> SubscriptionRow:
    """Subscription Pro mensual activa de ``user-a``, con los campos dados cambiados."""
    return replace(_SUBSCRIPTION, **overrides)
