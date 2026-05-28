"""Tests unitarios para la autenticacion JWT (app.api.dependencies.get_current_user)."""

import pytest
from fastapi import HTTPException

from app.api.dependencies import get_current_user as get_user_module
from app.core.config import Settings


def _make_settings(**overrides) -> Settings:
    """Construye Settings deterministas, ignorando .env y el entorno real."""
    base: dict[str, object] = {
        "database_url": "postgresql://user:pass@localhost:5432/db",
        "environment": "development",
        "cors_allowed_origins": "http://localhost:3000",
        "clerk_pem_public_key": None,
        "clerk_jwks_url": None,
        "clerk_issuer": None,
        "clerk_audience": "my-api",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def _use_settings(monkeypatch, **overrides) -> Settings:
    """Hace que get_current_user use una configuración controlada."""
    settings = _make_settings(**overrides)
    monkeypatch.setattr(get_user_module, "get_settings", lambda: settings)
    return settings


def test_get_signing_key_uses_jwks_client_when_available(monkeypatch):
    _use_settings(
        monkeypatch,
        clerk_jwks_url="https://tenant.clerk.accounts.dev/.well-known/jwks.json",
    )

    class _FakeSigningKey:
        key = "jwks-key"

    class _FakeJwksClient:
        def get_signing_key_from_jwt(self, token):
            assert token == "token-123"
            return _FakeSigningKey()

    monkeypatch.setattr(
        get_user_module, "_get_jwks_client", lambda url: _FakeJwksClient()
    )

    assert get_user_module._get_signing_key("token-123") == "jwks-key"


def test_get_signing_key_uses_pem_when_jwks_is_missing(monkeypatch):
    _use_settings(
        monkeypatch,
        clerk_jwks_url=None,
        clerk_pem_public_key="-----BEGIN PUBLIC KEY-----\\nabc\\n-----END PUBLIC KEY-----",
    )

    signing_key = get_user_module._get_signing_key("irrelevant-token")

    assert signing_key == "-----BEGIN PUBLIC KEY-----\nabc\n-----END PUBLIC KEY-----"


def test_get_signing_key_raises_500_if_no_provider_is_configured(monkeypatch):
    _use_settings(monkeypatch, clerk_jwks_url=None, clerk_pem_public_key=None)

    with pytest.raises(HTTPException) as exc:
        get_user_module._get_signing_key("irrelevant-token")

    assert exc.value.status_code == 500
    assert "Authentication provider is not configured" in exc.value.detail


def test_get_expected_issuer_uses_explicit_clerk_issuer(monkeypatch):
    _use_settings(monkeypatch, clerk_issuer="https://my-tenant.clerk.accounts.dev")

    assert (
        get_user_module._get_expected_issuer() == "https://my-tenant.clerk.accounts.dev"
    )


def test_get_expected_issuer_falls_back_to_jwks_url(monkeypatch):
    _use_settings(
        monkeypatch,
        clerk_issuer=None,
        clerk_jwks_url="https://my-tenant.clerk.accounts.dev/.well-known/jwks.json",
    )

    assert (
        get_user_module._get_expected_issuer() == "https://my-tenant.clerk.accounts.dev"
    )


def test_get_expected_issuer_raises_500_when_not_configured(monkeypatch):
    _use_settings(monkeypatch, clerk_issuer=None, clerk_jwks_url=None)

    with pytest.raises(HTTPException) as exc:
        get_user_module._get_expected_issuer()

    assert exc.value.status_code == 500
    assert "Authentication provider is not fully configured" in exc.value.detail


def test_get_expected_audience_parses_single_audience(monkeypatch):
    _use_settings(monkeypatch, clerk_audience="my-api")

    assert get_user_module._get_expected_audience() == "my-api"


def test_get_expected_audience_parses_multiple_audiences(monkeypatch):
    _use_settings(monkeypatch, clerk_audience="my-api, my-other-api")

    assert get_user_module._get_expected_audience() == ["my-api", "my-other-api"]


def test_get_expected_audience_raises_500_when_not_configured(monkeypatch):
    _use_settings(monkeypatch, clerk_audience="")

    with pytest.raises(HTTPException) as exc:
        get_user_module._get_expected_audience()

    assert exc.value.status_code == 500
    assert "Authentication provider is not fully configured" in exc.value.detail


def test_get_current_user_returns_payload_when_token_is_valid(monkeypatch):
    _use_settings(
        monkeypatch,
        clerk_issuer="https://my-tenant.clerk.accounts.dev",
        clerk_audience="my-api",
    )

    def _fake_decode(token, signing_key, algorithms, audience, issuer, leeway, options):
        assert token == "valid-token"
        assert signing_key == "signing-key"
        assert algorithms == ["RS256"]
        assert audience == "my-api"
        assert issuer == "https://my-tenant.clerk.accounts.dev"
        assert leeway == 10
        assert options == {"verify_aud": True, "verify_iss": True}
        return {"sub": "user_1", "sid": "session_1"}

    monkeypatch.setattr(get_user_module, "_get_signing_key", lambda _: "signing-key")
    monkeypatch.setattr(get_user_module.jwt, "decode", _fake_decode)

    payload = get_user_module.get_current_user("Bearer valid-token")

    assert payload["sub"] == "user_1"
    assert payload["sid"] == "session_1"


def test_get_current_user_rejects_missing_authorization_header():
    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user(None)

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "UNAUTHENTICATED"


def test_get_current_user_rejects_invalid_auth_header():
    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user("Token abc")

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "INVALID_TOKEN"


def test_get_current_user_returns_401_when_token_is_expired(monkeypatch):
    _use_settings(
        monkeypatch,
        clerk_issuer="https://my-tenant.clerk.accounts.dev",
        clerk_audience="my-api",
    )
    monkeypatch.setattr(get_user_module, "_get_signing_key", lambda _: "signing-key")

    def _raise_expired(*args, **kwargs):
        raise get_user_module.jwt.ExpiredSignatureError("expired")

    monkeypatch.setattr(get_user_module.jwt, "decode", _raise_expired)

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user("Bearer expired-token")

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "EXPIRED_TOKEN"


def test_get_current_user_returns_401_when_token_is_invalid(monkeypatch):
    _use_settings(
        monkeypatch,
        clerk_issuer="https://my-tenant.clerk.accounts.dev",
        clerk_audience="my-api",
    )
    monkeypatch.setattr(get_user_module, "_get_signing_key", lambda _: "signing-key")

    def _raise_invalid(*args, **kwargs):
        raise get_user_module.jwt.InvalidTokenError("invalid")

    monkeypatch.setattr(get_user_module.jwt, "decode", _raise_invalid)

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user("Bearer invalid-token")

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "INVALID_TOKEN"


def test_get_current_user_returns_500_for_invalid_key_format(monkeypatch):
    _use_settings(
        monkeypatch,
        clerk_issuer="https://my-tenant.clerk.accounts.dev",
        clerk_audience="my-api",
    )
    monkeypatch.setattr(get_user_module, "_get_signing_key", lambda _: "bad-key")

    def _raise_type_error(*args, **kwargs):
        raise TypeError("Expecting a PEM-formatted key.")

    monkeypatch.setattr(get_user_module.jwt, "decode", _raise_type_error)

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user("Bearer token")

    assert exc.value.status_code == 500
    assert (
        exc.value.detail == "Authentication provider is configured with an invalid key."
    )
