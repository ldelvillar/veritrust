"""Tests of the Clerk OAuth access token verifier for the MCP server."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import Settings
from app.core.jwks import AuthMisconfigured
from app.mcp import auth as auth_module

_ISSUER = "https://tenant.clerk.accounts.dev"
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _sign(claims: dict, key=_PRIVATE_KEY) -> str:
    """Sign a test token with the given RSA key."""
    return jwt.encode(claims, key, algorithm="RS256")


def _claims(**overrides) -> dict:
    """Claims of a valid OAuth access token, with overrides."""
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
    """Pin Clerk's issuer and resolve the public key without network."""
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        clerk_issuer=_ISSUER,
        clerk_jwks_url=f"{_ISSUER}/.well-known/jwks.json",
    )
    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        auth_module, "get_signing_key", lambda token: _PRIVATE_KEY.public_key()
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
        # A browser session token carries no client_id, so it is not valid for MCP.
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
        raise AuthMisconfigured("Falta CLERK_JWKS_URL")

    monkeypatch.setattr(auth_module, "get_signing_key", fail)

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
