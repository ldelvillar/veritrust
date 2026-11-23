"""Clerk signing keys, the JWKS client shared by the web API and the MCP server."""

import json
import threading
import time
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWK, PyJWKClient, PyJWKSet

from app.core.config import get_settings

# A downloaded JWKS is trusted this long, so a key Clerk removes stops verifying once it passes.
JWKS_CACHE_LIFESPAN_SECONDS = 600.0
# An unknown kid forces at most one JWKS download per interval, not one per request.
JWKS_REFRESH_COOLDOWN_SECONDS = 60.0
# A download that fails is retried after this, so an outage neither spends the interval nor goes unthrottled.
JWKS_FAILED_REFRESH_BACKOFF_SECONDS = 5.0
JWKS_FETCH_TIMEOUT_SECONDS = 5.0


class AuthMisconfigured(RuntimeError):
    """CLERK_JWKS_URL is missing, so there is nowhere to fetch the signing keys from."""


class _CooldownJWKClient(PyJWKClient):
    """JWKS client that downloads one JWKS at a time, on cache expiry or at most once per interval on an unknown kid."""

    def __init__(self, uri: str, **kwargs: Any) -> None:
        super().__init__(uri, cache_jwk_set=False, **kwargs)
        self._download_lock = threading.Lock()
        # The signing keys and when they expire, swapped as one tuple so lock-free readers see a consistent pair.
        self._cached: tuple[list[PyJWK], float] = ([], float("-inf"))
        self._next_forced_refresh = float("-inf")
        self._backoff_until = float("-inf")

    def get_signing_key(self, kid: str) -> PyJWK:
        """Return the kid's key, downloading the JWKS only when it expired or the unknown-kid interval has passed."""
        # Cached kids are looked up outside the lock, so a slow download never delays them.
        signing_keys, expires_at = self._cached
        if time.monotonic() < expires_at:
            signing_key = self.match_kid(signing_keys, kid)
            if signing_key is not None:
                return signing_key
        # A request waits at most one download timeout for a download already running, then answers unavailable.
        if not self._download_lock.acquire(timeout=JWKS_FETCH_TIMEOUT_SECONDS):
            raise jwt.PyJWKClientConnectionError(
                "Timed out waiting for the JWKS download already running"
            )
        try:
            signing_key = self._refresh_for(kid)
        finally:
            self._download_lock.release()
        if signing_key is None:
            raise jwt.PyJWKClientError(
                f'Unable to find a signing key that matches: "{kid}"'
            )
        return signing_key

    def _refresh_for(self, kid: str) -> PyJWK | None:
        """Download the JWKS for the kid unless another request already did or the cooldown or backoff is running."""
        signing_keys, expires_at = self._cached
        fresh = time.monotonic() < expires_at
        # Another request may have downloaded the JWKS since this one looked the kid up.
        if fresh and (signing_key := self.match_kid(signing_keys, kid)) is not None:
            return signing_key
        if time.monotonic() < self._backoff_until:
            raise jwt.PyJWKClientConnectionError(
                "The last JWKS download failed, retrying after the backoff"
            )
        if fresh and time.monotonic() < self._next_forced_refresh:
            return None
        try:
            signing_keys = self._download()
        except jwt.PyJWKClientConnectionError:
            self._backoff_until = time.monotonic() + JWKS_FAILED_REFRESH_BACKOFF_SECONDS
            raise
        self._cached = (signing_keys, time.monotonic() + JWKS_CACHE_LIFESPAN_SECONDS)
        # Only a download forced by an unknown kid spends the interval; a cache fill or expiry download does not.
        if fresh:
            self._next_forced_refresh = time.monotonic() + JWKS_REFRESH_COOLDOWN_SECONDS
        return self.match_kid(signing_keys, kid)

    def _download(self) -> list[PyJWK]:
        """Download and parse the JWKS, reporting any failure, including a body with no usable keys, as a connection error."""
        try:
            jwk_set = PyJWKSet.from_dict(self.fetch_data())
            return self._get_signing_keys_from_jwk_set(jwk_set)
        except jwt.PyJWKClientConnectionError:
            raise
        except (
            OSError,
            json.JSONDecodeError,
            UnicodeDecodeError,
            jwt.PyJWKClientError,
            jwt.PyJWKSetError,
        ) as e:
            raise jwt.PyJWKClientConnectionError(
                f'Fail to download or read the JWKS, err: "{e}"'
            ) from e


@lru_cache(maxsize=1)
def _get_jwks_client(jwks_url: str) -> _CooldownJWKClient:
    """Return a JWKS client cached by URL."""
    # No per-kid key cache, so a key Clerk removes stops verifying once the JWKS cache expires.
    return _CooldownJWKClient(jwks_url, timeout=JWKS_FETCH_TIMEOUT_SECONDS)


def get_signing_key(token: str) -> str:
    """Fetch the token's signing key from Clerk's JWKS, raising AuthMisconfigured without CLERK_JWKS_URL."""
    jwks_url = get_settings().clerk_jwks_url
    if not jwks_url:
        raise AuthMisconfigured("Falta CLERK_JWKS_URL")

    return _get_jwks_client(jwks_url).get_signing_key_from_jwt(token).key
