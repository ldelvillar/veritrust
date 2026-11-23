"""Clerk signing keys, the JWKS client shared by the web API and the MCP server."""

import threading
import time
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWK, PyJWKClient

from app.core.config import get_settings

# An unknown kid forces at most one JWKS download per interval, not one per request.
JWKS_REFRESH_COOLDOWN_SECONDS = 60.0
# A forced refresh that fails is retried after this, so an outage neither spends the interval nor goes unthrottled.
JWKS_FAILED_REFRESH_BACKOFF_SECONDS = 5.0
JWKS_FETCH_TIMEOUT_SECONDS = 5.0


class AuthMisconfigured(RuntimeError):
    """CLERK_JWKS_URL is missing, so there is nowhere to fetch the signing keys from."""


class _CooldownJWKClient(PyJWKClient):
    """JWKS client that downloads the JWKS again at most once per interval on an unknown kid."""

    def __init__(self, uri: str, **kwargs: Any) -> None:
        super().__init__(uri, cooldown_duration=0, **kwargs)
        self._refresh_lock = threading.Lock()
        self._next_forced_refresh = float("-inf")

    def get_signing_key(self, kid: str) -> PyJWK:
        """Return the kid's key, forcing a JWKS refresh only when the interval since the last one has passed."""
        # Cached kids are looked up outside the lock, so a slow forced refresh never delays them.
        signing_key = self.match_kid(self.get_signing_keys(), kid)
        # An unknown kid that finds a refresh already running is refused rather than queued on a thread.
        if signing_key is None and self._refresh_lock.acquire(blocking=False):
            try:
                signing_key = self._refresh_for(kid)
            finally:
                self._refresh_lock.release()
        if signing_key is None:
            raise jwt.PyJWKClientError(
                f'Unable to find a signing key that matches: "{kid}"'
            )
        return signing_key

    def _refresh_for(self, kid: str) -> PyJWK | None:
        """Force a JWKS refresh for an unknown kid unless the cooldown or failure backoff is still running."""
        # Another request may have refreshed the JWKS since this one looked the kid up.
        signing_key = self.match_kid(self.get_signing_keys(), kid)
        if signing_key is not None or time.monotonic() < self._next_forced_refresh:
            return signing_key
        try:
            signing_keys = self.get_signing_keys(refresh=True)
        except jwt.PyJWTError:
            self._next_forced_refresh = (
                time.monotonic() + JWKS_FAILED_REFRESH_BACKOFF_SECONDS
            )
            raise
        self._next_forced_refresh = time.monotonic() + JWKS_REFRESH_COOLDOWN_SECONDS
        return self.match_kid(signing_keys, kid)


@lru_cache(maxsize=1)
def _get_jwks_client(jwks_url: str) -> _CooldownJWKClient:
    """Return a JWKS client cached by URL."""
    # No per-kid key cache, so a key Clerk removes stops verifying once the JWKS cache expires.
    return _CooldownJWKClient(
        jwks_url, lifespan=600, timeout=JWKS_FETCH_TIMEOUT_SECONDS
    )


def get_signing_key(token: str) -> str:
    """Fetch the token's signing key from Clerk's JWKS, raising AuthMisconfigured without CLERK_JWKS_URL."""
    jwks_url = get_settings().clerk_jwks_url
    if not jwks_url:
        raise AuthMisconfigured("Falta CLERK_JWKS_URL")

    return _get_jwks_client(jwks_url).get_signing_key_from_jwt(token).key
