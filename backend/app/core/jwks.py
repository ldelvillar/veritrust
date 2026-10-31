"""Clerk signing keys, the JWKS client shared by the web API and the MCP server."""

import threading
from functools import lru_cache
from time import monotonic
from typing import Any

import jwt
from jwt import PyJWK, PyJWKClient

from app.core.config import get_settings

# An unknown kid forces at most one JWKS download per interval, not one per request.
JWKS_REFRESH_COOLDOWN_SECONDS = 60.0


class AuthMisconfigured(RuntimeError):
    """CLERK_JWKS_URL is missing, so there is nowhere to fetch the signing keys from."""


class _CooldownJWKClient(PyJWKClient):
    """JWKS client that downloads the JWKS again at most once per interval on an unknown kid."""

    def __init__(self, uri: str, **kwargs: Any) -> None:
        super().__init__(uri, **kwargs)
        self._refresh_lock = threading.Lock()
        self._last_forced_refresh = float("-inf")

    def get_signing_key(self, kid: str) -> PyJWK:
        """Return the kid's key, refreshing the JWKS only when the last forced refresh is behind the interval."""
        signing_key = self.match_kid(self.get_signing_keys(), kid)
        if signing_key is not None:
            return signing_key
        with self._refresh_lock:
            if monotonic() - self._last_forced_refresh < JWKS_REFRESH_COOLDOWN_SECONDS:
                raise jwt.PyJWKClientError(
                    f'Unable to find a signing key that matches: "{kid}"'
                )
            self._last_forced_refresh = monotonic()
        return super().get_signing_key(kid)


@lru_cache(maxsize=1)
def _get_jwks_client(jwks_url: str) -> _CooldownJWKClient:
    """Return a JWKS client cached by URL."""
    return _CooldownJWKClient(jwks_url, cache_keys=True, lifespan=600)


def get_signing_key(token: str) -> str:
    """Fetch the token's signing key from Clerk's JWKS, raising AuthMisconfigured without CLERK_JWKS_URL."""
    jwks_url = get_settings().clerk_jwks_url
    if not jwks_url:
        raise AuthMisconfigured("Falta CLERK_JWKS_URL")

    return _get_jwks_client(jwks_url).get_signing_key_from_jwt(token).key
