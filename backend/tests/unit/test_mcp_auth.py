"""Tests del verificador de access tokens OAuth de Clerk para el servidor MCP."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.core.config import Settings
from app.mcp import auth as auth_module

_ISSUER = "https://tenant.clerk.accounts.dev"
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _sign(claims: dict, key=_PRIVATE_KEY) -> str:
    """Firma un token de prueba con la clave RSA indicada."""
    return jwt.encode(claims, key, algorithm="RS256")


def _claims(**overrides) -> dict:
    """Claims de un access token OAuth válido, con sobrescrituras."""
    base: dict = {
        "iss": _ISSUER,
        "sub": "user_123",
        "client_id": "client_abc",
        "scope": "profile email",
        "exp": int(time.time()) + 300,
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


@pytest.fixture(autouse=True)
def _configure(monkeypatch):
    """Fija el issuer de Clerk y resuelve la clave pública sin red."""
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        clerk_issuer=_ISSUER,
        clerk_jwks_url=f"{_ISSUER}/.well-known/jwks.json",
    )
    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        auth_module, "_get_signing_key", lambda token: _PRIVATE_KEY.public_key()
    )


async def test_accepts_a_valid_oauth_access_token():
    token = _sign(_claims())

    access = await auth_module.ClerkOAuthTokenVerifier().verify_token(token)

    assert access is not None
    assert access.subject == "user_123"
    assert access.client_id == "client_abc"
    assert access.scopes == ["profile", "email"]
    assert access.token == token


async def test_accepts_scopes_as_a_list_claim():
    token = _sign(_claims(scope=None, scp=["profile"]))

    access = await auth_module.ClerkOAuthTokenVerifier().verify_token(token)

    assert access is not None
    assert access.scopes == ["profile"]


@pytest.mark.parametrize(
    "claims",
    [
        _claims(exp=int(time.time()) - 60),
        _claims(iss="https://other.clerk.accounts.dev"),
        # Un token de sesión del navegador no lleva client_id: no vale para MCP.
        _claims(client_id=None),
        _claims(sub=None),
    ],
    ids=["expired", "wrong-issuer", "session-token", "no-subject"],
)
async def test_rejects_invalid_tokens(claims):
    assert (
        await auth_module.ClerkOAuthTokenVerifier().verify_token(_sign(claims)) is None
    )


async def test_rejects_a_token_signed_with_another_key():
    token = _sign(_claims(), key=_OTHER_KEY)

    assert await auth_module.ClerkOAuthTokenVerifier().verify_token(token) is None


async def test_rejects_garbage():
    assert await auth_module.ClerkOAuthTokenVerifier().verify_token("not-a-jwt") is None


async def test_returns_none_when_the_signing_key_is_misconfigured(monkeypatch):
    def fail(token):
        raise HTTPException(status_code=500, detail={})

    monkeypatch.setattr(auth_module, "_get_signing_key", fail)

    assert (
        await auth_module.ClerkOAuthTokenVerifier().verify_token(_sign(_claims()))
        is None
    )


async def test_returns_none_without_an_issuer(monkeypatch):
    monkeypatch.setattr(
        auth_module,
        "get_settings",
        lambda: Settings(_env_file=None),  # type: ignore[call-arg]
    )

    assert (
        await auth_module.ClerkOAuthTokenVerifier().verify_token(_sign(_claims()))
        is None
    )
