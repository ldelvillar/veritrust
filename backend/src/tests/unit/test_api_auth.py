"""Tests unitarios para la autenticacion JWT en src.api.utils."""

import pytest
from fastapi import HTTPException
from src.api import utils as utils_module


def test_normalize_pem_key_returns_none_for_empty_values():
    assert utils_module._normalize_pem_key(None) is None
    assert utils_module._normalize_pem_key("") is None


def test_normalize_pem_key_replaces_escaped_newlines():
    raw_key = "-----BEGIN PUBLIC KEY-----\\nabc\\n-----END PUBLIC KEY-----"

    normalized = utils_module._normalize_pem_key(raw_key)

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

    monkeypatch.setattr(utils_module, "jwks_client", _FakeJwksClient())
    monkeypatch.setattr(utils_module, "CLERK_PEM_PUBLIC_KEY", None)

    signing_key = utils_module._get_signing_key("token-123")

    assert signing_key == "jwks-key"


def test_get_signing_key_uses_pem_when_jwks_is_missing(monkeypatch):
    monkeypatch.setattr(utils_module, "jwks_client", None)
    monkeypatch.setattr(
        utils_module,
        "CLERK_PEM_PUBLIC_KEY",
        "-----BEGIN PUBLIC KEY-----\\nabc\\n-----END PUBLIC KEY-----",
    )

    signing_key = utils_module._get_signing_key("irrelevant-token")

    assert signing_key == "-----BEGIN PUBLIC KEY-----\nabc\n-----END PUBLIC KEY-----"


def test_get_signing_key_raises_500_if_no_provider_is_configured(monkeypatch):
    monkeypatch.setattr(utils_module, "jwks_client", None)
    monkeypatch.setattr(utils_module, "CLERK_PEM_PUBLIC_KEY", None)

    with pytest.raises(HTTPException) as exc:
        utils_module._get_signing_key("irrelevant-token")

    assert exc.value.status_code == 500
    assert "Authentication provider is not configured" in exc.value.detail


def test_get_current_user_returns_payload_when_token_is_valid(monkeypatch):
    def _fake_decode(token, signing_key, algorithms, options):
        assert token == "valid-token"
        assert signing_key == "signing-key"
        assert algorithms == ["RS256"]
        assert options == {"verify_aud": False, "verify_iss": False}
        return {"sub": "user_1", "sid": "session_1"}

    monkeypatch.setattr(utils_module, "_get_signing_key", lambda _: "signing-key")
    monkeypatch.setattr(utils_module.jwt, "decode", _fake_decode)

    payload = utils_module.get_current_user("Bearer valid-token")

    assert payload["sub"] == "user_1"
    assert payload["sid"] == "session_1"


def test_get_current_user_rejects_missing_authorization_header():
    with pytest.raises(HTTPException) as exc:
        utils_module.get_current_user(None)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Missing Authorization header"


def test_get_current_user_rejects_invalid_auth_header():
    with pytest.raises(HTTPException) as exc:
        utils_module.get_current_user("Token abc")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid auth header"


def test_get_current_user_returns_401_when_token_is_expired(monkeypatch):
    monkeypatch.setattr(utils_module, "_get_signing_key", lambda _: "signing-key")

    def _raise_expired(*args, **kwargs):
        raise utils_module.jwt.ExpiredSignatureError("expired")

    monkeypatch.setattr(utils_module.jwt, "decode", _raise_expired)

    with pytest.raises(HTTPException) as exc:
        utils_module.get_current_user("Bearer expired-token")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token expired"


def test_get_current_user_returns_401_when_token_is_invalid(monkeypatch):
    monkeypatch.setattr(utils_module, "_get_signing_key", lambda _: "signing-key")

    def _raise_invalid(*args, **kwargs):
        raise utils_module.jwt.InvalidTokenError("invalid")

    monkeypatch.setattr(utils_module.jwt, "decode", _raise_invalid)

    with pytest.raises(HTTPException) as exc:
        utils_module.get_current_user("Bearer invalid-token")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token"


def test_get_current_user_returns_500_for_invalid_key_format(monkeypatch):
    monkeypatch.setattr(utils_module, "_get_signing_key", lambda _: "bad-key")

    def _raise_type_error(*args, **kwargs):
        raise TypeError("Expecting a PEM-formatted key.")

    monkeypatch.setattr(utils_module.jwt, "decode", _raise_type_error)

    with pytest.raises(HTTPException) as exc:
        utils_module.get_current_user("Bearer token")

    assert exc.value.status_code == 500
    assert (
        exc.value.detail == "Authentication provider is configured with an invalid key."
    )
