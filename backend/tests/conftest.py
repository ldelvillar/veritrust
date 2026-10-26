"""Fixtures compartidas por todas las suites de pruebas."""

import pytest

from app.core.config import get_settings
from tests.support.billing import PRICE_MONTHLY, PRICE_YEARLY, WEBHOOK_SECRET


@pytest.fixture
def stripe_settings(monkeypatch):
    """Configura Stripe con valores de prueba y devuelve los Settings resultantes."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("STRIPE_PRICE_PRO_MONTHLY", PRICE_MONTHLY)
    monkeypatch.setenv("STRIPE_PRICE_PRO_YEARLY", PRICE_YEARLY)
    monkeypatch.setenv("APP_BASE_URL", "https://veritrust.test/")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()
