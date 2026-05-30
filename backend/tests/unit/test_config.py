"""Tests unitarios para la configuración central (app.core.config)."""

import pytest

from app.core.config import Settings, SettingsValidationError, _normalize_pem_key


def _make_settings(**overrides) -> Settings:
    """Construye Settings deterministas, ignorando .env y el entorno real."""
    base: dict[str, object] = {
        "database_url": "postgresql://user:pass@localhost:5432/db",
        "environment": "development",
        "cors_allowed_origins": "http://localhost:3000",
        "cors_allow_credentials": True,
        "clerk_pem_public_key": None,
        "clerk_jwks_url": "https://tenant.clerk.accounts.dev/.well-known/jwks.json",
        "clerk_issuer": None,
        "clerk_audience": "my-api",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def test_analysis_queue_defaults_keep_reaper_above_job_timeout():
    settings = _make_settings()

    assert settings.analysis_job_timeout_seconds == 600
    assert settings.analysis_stale_after_seconds == 900
    # El reaper nunca debe correr a una fila viva: su umbral excede al job_timeout.
    assert settings.analysis_stale_after_seconds > settings.analysis_job_timeout_seconds


def test_normalize_pem_key_returns_none_for_empty_values():
    assert _normalize_pem_key(None) is None
    assert _normalize_pem_key("") is None


def test_normalize_pem_key_replaces_escaped_newlines():
    raw_key = "-----BEGIN PUBLIC KEY-----\\nabc\\n-----END PUBLIC KEY-----"

    normalized = _normalize_pem_key(raw_key)

    assert normalized is not None
    assert "\\n" not in normalized
    assert "\n" in normalized
    assert normalized.startswith("-----BEGIN PUBLIC KEY-----")


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
        clerk_pem_public_key=None,
        clerk_issuer=None,
        clerk_audience="",
    )

    with pytest.raises(SettingsValidationError) as exc:
        settings.validate_runtime()

    message = str(exc.value)
    assert "DATABASE_URL" in message
    assert "CLERK_AUDIENCE" in message


def test_validate_runtime_requires_cors_origins_in_production():
    settings = _make_settings(environment="production", cors_allowed_origins="")

    with pytest.raises(SettingsValidationError) as exc:
        settings.validate_runtime()

    assert "CORS_ALLOWED_ORIGINS" in str(exc.value)


def test_validate_runtime_rejects_wildcard_origin_with_credentials():
    settings = _make_settings(
        environment="production",
        cors_allowed_origins="*",
        cors_allow_credentials=True,
    )

    with pytest.raises(SettingsValidationError):
        settings.validate_runtime()
