"""Clerk API keys (ak_…), verified against its Backend API with a short cache."""

import hashlib
from time import monotonic

import httpx

from app.core.config import get_settings

API_KEY_PREFIX = "ak_"
# A revoked key is still accepted for at most this long after its last verification.
VERIFIED_KEY_TTL_SECONDS = 60.0
_VERIFY_PATH = "/api_keys/verify"
_REQUEST_TIMEOUT_SECONDS = 5

# SHA-256 fingerprint of the key to (user_id, monotonic instant the entry expires).
_verified: dict[str, tuple[str, float]] = {}


class InvalidApiKey(Exception):
    """The key does not exist, is revoked or expired, or does not belong to a user."""


class ClerkUnreachable(Exception):
    """Clerk's Backend API did not respond or failed to verify the key."""


class ApiKeysMisconfigured(Exception):
    """Clerk rejects CLERK_SECRET_KEY or does not have API keys enabled on this instance."""


def _ask_clerk(secret: str) -> str:
    """Verify the key against Clerk's Backend API and return the user_id of its subject."""
    settings = get_settings()
    try:
        response = httpx.post(
            f"{settings.clerk_api_base_url}{_VERIFY_PATH}",
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
            json={"secret": secret},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.TransportError as e:
        raise ClerkUnreachable(str(e)) from e

    status = response.status_code
    if status in (401, 403):
        raise ApiKeysMisconfigured(f"HTTP {status} {response.text}")
    if status == 429 or status >= 500:
        raise ClerkUnreachable(f"HTTP {status}")
    if status != 200:
        raise InvalidApiKey(f"HTTP {status}")

    api_key = response.json()
    subject: str = api_key["subject"]
    if api_key["revoked"] or api_key["expired"] or not subject.startswith("user_"):
        raise InvalidApiKey(api_key["id"])
    return subject


def verify_api_key(secret: str) -> str:
    """Return the user_id that owns the key, asking Clerk only when it is not cached."""
    fingerprint = hashlib.sha256(secret.encode()).hexdigest()
    cached = _verified.get(fingerprint)
    if cached is not None and monotonic() < cached[1]:
        return cached[0]

    user_id = _ask_clerk(secret)
    _verified[fingerprint] = (user_id, monotonic() + VERIFIED_KEY_TTL_SECONDS)
    return user_id
