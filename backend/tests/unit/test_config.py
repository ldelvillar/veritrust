"""Unit tests for the central configuration (app.core.config)."""

import pytest

from app.core.config import Settings, SettingsValidationError
from tests.support.billing import (
    CLERK_WEBHOOK_SECRET,
    PRICE_MONTHLY,
    PRICE_YEARLY,
    WEBHOOK_SECRET,
)


def _make_settings(**overrides) -> Settings:
    """Build deterministic Settings, ignoring .env and the real environment."""
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
    return Settings(_env_file=None, **base)


def test_analysis_queue_defaults():
    settings = _make_settings()

    assert settings.analysis_job_timeout_seconds == 900
    # The reaper only touches rows with no live job, so it can go below job_timeout safely.
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


def test_validate_runtime_rejects_a_whitespace_only_app_base_url():
    settings = _make_settings(app_base_url=" ")

    assert settings.app_base_url == ""
    with pytest.raises(SettingsValidationError, match="APP_BASE_URL"):
        settings.validate_runtime()


def test_app_base_url_is_stripped_of_surrounding_whitespace():
    assert _make_settings(app_base_url=" https://veritrust.es ").app_base_url == (
        "https://veritrust.es"
    )


def test_app_base_url_drops_the_trailing_slash():
    assert _make_settings(app_base_url="https://veritrust.es/").app_base_url == (
        "https://veritrust.es"
    )


def test_validate_runtime_requires_mcp_url_to_end_in_mcp():
    settings = _make_settings(mcp_resource_url="https://api.veritrust.es/tools")

    with pytest.raises(SettingsValidationError, match="/mcp"):
        settings.validate_runtime()


def test_mcp_resource_url_drops_trailing_slashes():
    settings = _make_settings(mcp_resource_url="https://api.veritrust.es/mcp//")

    assert settings.mcp_resource_url == "https://api.veritrust.es/mcp"


def test_validate_runtime_treats_an_mcp_url_of_only_slashes_as_missing():
    settings = _make_settings(mcp_resource_url="///")

    assert settings.mcp_resource_url == ""
    with pytest.raises(SettingsValidationError, match="MCP_RESOURCE_URL"):
        settings.validate_runtime()


def test_validate_runtime_rejects_a_doubled_slash_before_mcp():
    settings = _make_settings(mcp_resource_url="https://api.veritrust.es//mcp//")

    with pytest.raises(SettingsValidationError, match="/mcp"):
        settings.validate_runtime()


def test_a_whitespace_only_clerk_issuer_is_rejected_not_ignored():
    settings = _make_settings(clerk_issuer=" ")

    with pytest.raises(SettingsValidationError, match="sin espacios.*CLERK_ISSUER"):
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
        resend_api_key="",
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
    worker_without_resend = _make_settings(
        environment="production", resend_api_key=" ", resend_from_email=""
    )

    worker_without_inbox.validate_runtime(web=False)
    with pytest.raises(SettingsValidationError) as exc:
        worker_without_resend.validate_runtime(web=False)

    message = str(exc.value)
    assert "RESEND_API_KEY" in message
    assert "RESEND_FROM_EMAIL" in message


def test_validate_runtime_leaves_the_email_settings_optional_in_development():
    settings = _make_settings(
        environment="development",
        resend_api_key="",
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


@pytest.mark.parametrize("url", ["localhost:11434", "//localhost:11434", "http://", ""])
def test_validate_runtime_rejects_an_ollama_url_without_scheme_or_host(url):
    settings = _make_settings(llm_provider="ollama", ollama_base_url=url)

    with pytest.raises(SettingsValidationError, match="OLLAMA_BASE_URL"):
        settings.validate_runtime()


def test_validate_runtime_ignores_the_ollama_url_for_other_providers():
    settings = _make_settings(
        llm_provider="groq", groq_api_key="clave-de-prueba", ollama_base_url="x"
    )

    settings.validate_runtime()


@pytest.mark.parametrize(
    "name",
    [
        "europepmc_base_url",
        "pubmed_base_url",
        "openfda_base_url",
        "cima_base_url",
        "clerk_api_base_url",
        "resend_base_url",
        "app_base_url",
        "clerk_jwks_url",
        "mcp_resource_url",
        "clerk_issuer",
    ],
)
def test_validate_runtime_rejects_a_service_url_without_scheme_or_host(name):
    overrides = {"clerk_issuer": "https://tenant.clerk.accounts.dev", name: "a.b/mcp"}
    settings = _make_settings(**overrides)

    with pytest.raises(SettingsValidationError, match=name.upper()):
        settings.validate_runtime()


@pytest.mark.parametrize("name", ["app_base_url", "clerk_jwks_url"])
def test_validate_runtime_checks_the_worker_urls_too(name):
    settings = _make_settings(
        clerk_issuer="https://tenant.clerk.accounts.dev", **{name: "a.b/x"}
    )

    with pytest.raises(SettingsValidationError, match=name.upper()):
        settings.validate_runtime(web=False)


def test_validate_runtime_skips_the_mcp_url_check_for_the_worker():
    _make_settings(mcp_resource_url="a.b/mcp").validate_runtime(web=False)


@pytest.mark.parametrize("name", ["clerk_jwks_url", "mcp_resource_url", "clerk_issuer"])
def test_validate_runtime_rejects_a_padded_url_with_the_url_error(name):
    overrides = {"clerk_issuer": "https://tenant.clerk.accounts.dev"}
    overrides[name] = "https://api.veritrust.es/mcp "
    settings = _make_settings(**overrides)

    with pytest.raises(SettingsValidationError, match=f"sin espacios.*{name.upper()}"):
        settings.validate_runtime()


@pytest.mark.parametrize(
    "url",
    [
        " https://api.example.com",
        "https://api.example.com ",
        "ftp://api.example.com",
        "http://localhost:abc",
        "http://localhost:99999",
        "http://[::1",
        "https://a b.com",
        "https:/api.example.com",
        "https:api.example.com",
        "https:\\\\api.example.com",
        "https://api.exam\nple.com",
        "https://api.example.com/\trest",
        "http://api.example.com:0",
        "http://api.example.com:",
        "http://api.example.com:/rest",
    ],
)
def test_validate_runtime_rejects_a_padded_or_malformed_url(url):
    settings = _make_settings(pubmed_base_url=url)

    with pytest.raises(SettingsValidationError, match="PUBMED_BASE_URL"):
        settings.validate_runtime()


@pytest.mark.parametrize(
    "url",
    [
        "HTTPS://api.example.com/rest",
        "http://localhost:11434",
        "https://api.example.com/rest/v1",
    ],
)
def test_validate_runtime_accepts_a_well_formed_http_url(url):
    _make_settings(pubmed_base_url=url).validate_runtime()


def test_validate_runtime_reports_every_invalid_url_at_once():
    settings = _make_settings(ollama_base_url="x", pubmed_base_url="y")

    with pytest.raises(SettingsValidationError) as exc:
        settings.validate_runtime()

    assert "OLLAMA_BASE_URL" in str(exc.value)
    assert "PUBMED_BASE_URL" in str(exc.value)


def test_validate_runtime_requires_groq_api_key_for_groq_provider():
    settings = _make_settings(llm_provider="GROQ", groq_api_key="  ")

    with pytest.raises(SettingsValidationError, match="GROQ_API_KEY"):
        settings.validate_runtime()


@pytest.mark.parametrize("rate", [0, float("nan"), float("inf")])
def test_validate_runtime_requires_a_positive_mistral_rate(rate):
    settings = _make_settings(
        llm_provider="mistral",
        mistral_api_key="clave-de-prueba",
        mistral_requests_per_second=rate,
    )

    with pytest.raises(SettingsValidationError, match="MISTRAL_REQUESTS_PER_SECOND"):
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
