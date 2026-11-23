"""Clerk signing keys, the JWKS client shared by the web API and the MCP server."""

from functools import lru_cache

from jwt import PyJWKClient

from app.core.config import get_settings

# An unknown kid forces at most one JWKS download per interval, not one per request.
JWKS_REFRESH_COOLDOWN_SECONDS = 60.0


class AuthMisconfigured(RuntimeError):
    """CLERK_JWKS_URL is missing, so there is nowhere to fetch the signing keys from."""


@lru_cache(maxsize=1)
def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    """Return a JWKS client cached by URL."""
    # No per-kid key cache, so a key Clerk removes stops verifying once the JWKS cache expires.
    return PyJWKClient(
        jwks_url, lifespan=600, cooldown_duration=JWKS_REFRESH_COOLDOWN_SECONDS
    )


def get_signing_key(token: str) -> str:
    """Fetch the token's signing key from Clerk's JWKS, raising AuthMisconfigured without CLERK_JWKS_URL."""
    jwks_url = get_settings().clerk_jwks_url
    if not jwks_url:
        raise AuthMisconfigured("Falta CLERK_JWKS_URL")

    return _get_jwks_client(jwks_url).get_signing_key_from_jwt(token).key
