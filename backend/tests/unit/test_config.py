"""Tests unitarios para la configuración central (app.core.config)."""

import pytest

from app.core.config import Settings, SettingsValidationError
from tests.support.billing import (
    CLERK_WEBHOOK_SECRET,
    PRICE_MONTHLY,
    PRICE_YEARLY,
    WEBHOOK_SECRET,
)


def _make_settings(**overrides) -> Settings:
    """Construye Settings deterministas, ignorando .env y el entorno real."""
    base: dict[str, object] = {
        "database_url": "postgresql://user:pass@localhost:5432/db",
        "environment": "development",
        "cors_allowed_origins": "http://localhost:3000",
        "cors_allow_credentials": True,
        "clerk_jwks_url": "https://tenant.clerk.accounts.dev/.well-known/jwks.json",
        "clerk_issuer": None,
        "clerk_audience": "my-api",
        "clerk_secret_key": "sk_test_dummy",
        "app_base_url": "https://veritrust.es",
        "mcp_resource_url": "https://api.veritrust.es/mcp",
        "stripe_secret_key": "sk_test_dummy",
        "stripe_webhook_secret": WEBHOOK_SECRET,
        "stripe_price_pro_monthly": PRICE_MONTHLY,
        "stripe_price_pro_yearly": PRICE_YEARLY,
        "clerk_webhook_secret": CLERK_WEBHOOK_SECRET,
        "resend_api_key": "re_test_dummy",
        "resend_from_email": "no-reply@example.com",
        "contact_to_email": "equipo@example.com",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def test_analysis_queue_defaults():
    settings = _make_settings()

    assert settings.analysis_job_timeout_seconds == 900
    # El reaper solo toca filas sin job vivo: puede bajar del job_timeout sin riesgo.
    assert settings.analysis_stale_after_seconds == 300


def test_cors_origins_falls_back_to_localhost_only_in_development():
    settings = _make_settings(environment="development", cors_allowed_origins="")
    assert settings.cors_origins() == ["http://localhost:3000"]


def test_cors_origins_parses_comma_separated_list():
    settings = _make_settings(
        cors_allowed_origins="https://a.com, https://b.com ,",
    )
    assert settings.cors_origins() == ["https://a.com", "https://b.com"]


def test_expected_issuer_prefers_explicit_value():
    settings = _make_settings(clerk_issuer="https://explicit.clerk.accounts.dev")
    assert settings.expected_issuer == "https://explicit.clerk.accounts.dev"


def test_expected_issuer_derives_from_jwks_url():
    settings = _make_settings(
        clerk_issuer=None,
        clerk_jwks_url="https://tenant.clerk.accounts.dev/.well-known/jwks.json",
    )
    assert settings.expected_issuer == "https://tenant.clerk.accounts.dev"


def test_expected_issuer_is_none_when_not_configured():
    settings = _make_settings(clerk_issuer=None, clerk_jwks_url=None)
    assert settings.expected_issuer is None


def test_expected_audience_single_and_multiple():
    assert _make_settings(clerk_audience="my-api").expected_audience() == "my-api"
    assert _make_settings(clerk_audience="a, b").expected_audience() == ["a", "b"]


def test_expected_audience_is_none_when_missing():
    assert _make_settings(clerk_audience="").expected_audience() is None


def test_validate_runtime_passes_with_complete_config():
    # No debe lanzar.
    _make_settings(environment="production").validate_runtime()


def test_validate_runtime_reports_missing_required_vars():
    settings = _make_settings(
        database_url="",
        clerk_jwks_url=None,
        clerk_issuer=None,
        clerk_audience="",
        clerk_secret_key="",
        app_base_url="",
        mcp_resource_url="",
        stripe_secret_key="",
        stripe_webhook_secret="",
        stripe_price_pro_monthly="",
        stripe_price_pro_yearly=" ",
        clerk_webhook_secret="",
    )

    with pytest.raises(SettingsValidationError) as exc:
        settings.validate_runtime()

    message = str(exc.value)
    assert "CLERK_WEBHOOK_SECRET" in message
    assert "DATABASE_URL" in message
    assert "CLERK_AUDIENCE" in message
    assert "CLERK_SECRET_KEY" in message
    assert "APP_BASE_URL" in message
    assert "MCP_RESOURCE_URL" in message
    assert "STRIPE_SECRET_KEY" in message
    assert "STRIPE_WEBHOOK_SECRET" in message
    assert "STRIPE_PRICE_PRO_MONTHLY" in message
    assert "STRIPE_PRICE_PRO_YEARLY" in message


def test_validate_runtime_requires_mcp_url_to_end_in_mcp():
    settings = _make_settings(mcp_resource_url="https://api.veritrust.es/tools")

    with pytest.raises(SettingsValidationError, match="/mcp"):
        settings.validate_runtime()


def test_validate_runtime_skips_web_only_settings_for_the_worker():
    settings = _make_settings(
        environment="production",
        cors_allowed_origins="",
        mcp_resource_url=None,
        stripe_secret_key="",
        stripe_webhook_secret="",
        clerk_webhook_secret="",
    )

    settings.validate_runtime(web=False)


def test_validate_runtime_requires_cors_origins_in_production():
    settings = _make_settings(environment="production", cors_allowed_origins="")

    with pytest.raises(SettingsValidationError) as exc:
        settings.validate_runtime()

    assert "CORS_ALLOWED_ORIGINS" in str(exc.value)


def test_validate_runtime_requires_the_email_settings_in_production():
    settings = _make_settings(
        environment="production",
        resend_api_key=None,
        resend_from_email="",
        contact_to_email=" ",
    )

    with pytest.raises(SettingsValidationError) as exc:
        settings.validate_runtime()

    message = str(exc.value)
    assert "RESEND_API_KEY" in message
    assert "RESEND_FROM_EMAIL" in message
    assert "CONTACT_TO_EMAIL" in message


def test_validate_runtime_requires_resend_but_not_the_contact_inbox_for_the_worker():
    worker_without_inbox = _make_settings(environment="production", contact_to_email="")
    worker_without_resend = _make_settings(environment="production", resend_api_key="")

    worker_without_inbox.validate_runtime(web=False)
    with pytest.raises(SettingsValidationError, match="RESEND_API_KEY"):
        worker_without_resend.validate_runtime(web=False)


def test_validate_runtime_leaves_the_email_settings_optional_in_development():
    settings = _make_settings(
        environment="development",
        resend_api_key=None,
        resend_from_email="",
        contact_to_email="",
    )

    settings.validate_runtime()


def test_validate_runtime_rejects_wildcard_origin_with_credentials():
    settings = _make_settings(
        environment="production",
        cors_allowed_origins="*",
        cors_allow_credentials=True,
    )

    with pytest.raises(SettingsValidationError):
        settings.validate_runtime()


def test_validate_runtime_requires_groq_api_key_for_groq_provider():
    settings = _make_settings(llm_provider="GROQ", groq_api_key="  ")

    with pytest.raises(SettingsValidationError, match="GROQ_API_KEY"):
        settings.validate_runtime()


def test_validate_runtime_accepts_groq_provider_with_api_key():
    settings = _make_settings(llm_provider="groq", groq_api_key="clave-de-prueba")

    settings.validate_runtime()


def test_validate_runtime_requires_google_api_key_for_google_provider():
    settings = _make_settings(llm_provider="GOOGLE", google_api_key="  ")

    with pytest.raises(SettingsValidationError, match="GOOGLE_API_KEY"):
        settings.validate_runtime()


def test_validate_runtime_accepts_google_provider_with_api_key():
    settings = _make_settings(llm_provider="google", google_api_key="clave-de-prueba")

    settings.validate_runtime()


def test_validate_runtime_requires_nvidia_api_key_for_nvidia_provider():
    settings = _make_settings(llm_provider="NVIDIA", nvidia_api_key="  ")

    with pytest.raises(SettingsValidationError, match="NVIDIA_API_KEY"):
        settings.validate_runtime()


def test_validate_runtime_accepts_nvidia_provider_with_api_key():
    settings = _make_settings(llm_provider="nvidia", nvidia_api_key="clave-de-prueba")

    settings.validate_runtime()
