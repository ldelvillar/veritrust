"""Tests unitarios para la autenticacion JWT en app.api.utils."""

import pytest
from fastapi import HTTPException

from app.api.dependencies import get_current_user as get_user_module


def test_normalize_pem_key_returns_none_for_empty_values():
    assert get_user_module._normalize_pem_key(None) is None
    assert get_user_module._normalize_pem_key("") is None


def test_normalize_pem_key_replaces_escaped_newlines():
    raw_key = "-----BEGIN PUBLIC KEY-----\\nabc\\n-----END PUBLIC KEY-----"

    normalized = get_user_module._normalize_pem_key(raw_key)

    assert "\\n" not in normalized
    assert "\n" in normalized
    assert normalized.startswith("-----BEGIN PUBLIC KEY-----")


def test_get_signing_key_uses_jwks_client_when_available(monkeypatch):
    class _FakeSigningKey:
        key = "jwks-key"

    class _FakeJwksClient:
        def get_signing_key_from_jwt(self, token):
            assert token == "token-123"
            return _FakeSigningKey()

    monkeypatch.setattr(get_user_module, "jwks_client", _FakeJwksClient())
    monkeypatch.setattr(get_user_module, "CLERK_PEM_PUBLIC_KEY", None)

    signing_key = get_user_module._get_signing_key("token-123")

    assert signing_key == "jwks-key"


def test_get_signing_key_uses_pem_when_jwks_is_missing(monkeypatch):
    monkeypatch.setattr(get_user_module, "jwks_client", None)
    monkeypatch.setattr(
        get_user_module,
        "CLERK_PEM_PUBLIC_KEY",
        "-----BEGIN PUBLIC KEY-----\\nabc\\n-----END PUBLIC KEY-----",
    )

    signing_key = get_user_module._get_signing_key("irrelevant-token")

    assert signing_key == "-----BEGIN PUBLIC KEY-----\nabc\n-----END PUBLIC KEY-----"


def test_get_signing_key_raises_500_if_no_provider_is_configured(monkeypatch):
    monkeypatch.setattr(get_user_module, "jwks_client", None)
    monkeypatch.setattr(get_user_module, "CLERK_PEM_PUBLIC_KEY", None)

    with pytest.raises(HTTPException) as exc:
        get_user_module._get_signing_key("irrelevant-token")

    assert exc.value.status_code == 500
    assert "Authentication provider is not configured" in exc.value.detail


def test_get_expected_issuer_uses_explicit_clerk_issuer(monkeypatch):
    monkeypatch.setattr(
        get_user_module, "CLERK_ISSUER", "https://my-tenant.clerk.accounts.dev"
    )

    issuer = get_user_module._get_expected_issuer()

    assert issuer == "https://my-tenant.clerk.accounts.dev"


def test_get_expected_issuer_falls_back_to_jwks_url(monkeypatch):
    monkeypatch.setattr(get_user_module, "CLERK_ISSUER", None)
    monkeypatch.setattr(
        get_user_module,
        "CLERK_JWKS_URL",
        "https://my-tenant.clerk.accounts.dev/.well-known/jwks.json",
    )

    issuer = get_user_module._get_expected_issuer()

    assert issuer == "https://my-tenant.clerk.accounts.dev"


def test_get_expected_issuer_raises_500_when_not_configured(monkeypatch):
    monkeypatch.setattr(get_user_module, "CLERK_ISSUER", None)
    monkeypatch.setattr(get_user_module, "CLERK_JWKS_URL", None)

    with pytest.raises(HTTPException) as exc:
        get_user_module._get_expected_issuer()

    assert exc.value.status_code == 500
    assert "Authentication provider is not fully configured" in exc.value.detail


def test_get_expected_audience_parses_single_audience(monkeypatch):
    monkeypatch.setattr(get_user_module, "CLERK_AUDIENCE", "my-api")

    audience = get_user_module._get_expected_audience()

    assert audience == "my-api"


def test_get_expected_audience_parses_multiple_audiences(monkeypatch):
    monkeypatch.setattr(get_user_module, "CLERK_AUDIENCE", "my-api, my-other-api")

    audience = get_user_module._get_expected_audience()

    assert audience == ["my-api", "my-other-api"]


def test_get_expected_audience_raises_500_when_not_configured(monkeypatch):
    monkeypatch.setattr(get_user_module, "CLERK_AUDIENCE", "")

    with pytest.raises(HTTPException) as exc:
        get_user_module._get_expected_audience()

    assert exc.value.status_code == 500
    assert "Authentication provider is not fully configured" in exc.value.detail


def test_get_current_user_returns_payload_when_token_is_valid(monkeypatch):
    monkeypatch.setattr(
        get_user_module, "CLERK_ISSUER", "https://my-tenant.clerk.accounts.dev"
    )
    monkeypatch.setattr(get_user_module, "CLERK_AUDIENCE", "my-api")

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
    assert exc.value.detail == "Missing Authorization header"


def test_get_current_user_rejects_invalid_auth_header():
    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user("Token abc")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid auth header"


def test_get_current_user_returns_401_when_token_is_expired(monkeypatch):
    monkeypatch.setattr(
        get_user_module, "CLERK_ISSUER", "https://my-tenant.clerk.accounts.dev"
    )
    monkeypatch.setattr(get_user_module, "CLERK_AUDIENCE", "my-api")
    monkeypatch.setattr(get_user_module, "_get_signing_key", lambda _: "signing-key")

    def _raise_expired(*args, **kwargs):
        raise get_user_module.jwt.ExpiredSignatureError("expired")

    monkeypatch.setattr(get_user_module.jwt, "decode", _raise_expired)

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user("Bearer expired-token")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token expired"


def test_get_current_user_returns_401_when_token_is_invalid(monkeypatch):
    monkeypatch.setattr(
        get_user_module, "CLERK_ISSUER", "https://my-tenant.clerk.accounts.dev"
    )
    monkeypatch.setattr(get_user_module, "CLERK_AUDIENCE", "my-api")
    monkeypatch.setattr(get_user_module, "_get_signing_key", lambda _: "signing-key")

    def _raise_invalid(*args, **kwargs):
        raise get_user_module.jwt.InvalidTokenError("invalid")

    monkeypatch.setattr(get_user_module.jwt, "decode", _raise_invalid)

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user("Bearer invalid-token")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token"


def test_get_current_user_returns_500_for_invalid_key_format(monkeypatch):
    monkeypatch.setattr(
        get_user_module, "CLERK_ISSUER", "https://my-tenant.clerk.accounts.dev"
    )
    monkeypatch.setattr(get_user_module, "CLERK_AUDIENCE", "my-api")
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
