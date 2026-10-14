"""Claves API de Clerk (ak_…): verificación contra su Backend API, con una caché breve."""

import hashlib
from time import monotonic

import httpx

from app.core.config import get_settings

API_KEY_PREFIX = "ak_"
# Una clave revocada se sigue aceptando como mucho este tiempo tras su última verificación.
VERIFIED_KEY_TTL_SECONDS = 60.0
_VERIFY_PATH = "/api_keys/verify"
_REQUEST_TIMEOUT_SECONDS = 5

# Huella SHA-256 de la clave → (user_id, instante monotónico en que caduca la entrada).
_verified: dict[str, tuple[str, float]] = {}


class InvalidApiKey(Exception):
    """La clave no existe, está revocada o caducada, o no pertenece a un usuario."""


class ClerkUnreachable(Exception):
    """El Backend API de Clerk no respondió o falló al verificar la clave."""


class ApiKeysMisconfigured(Exception):
    """Clerk rechaza CLERK_SECRET_KEY o no tiene activadas las claves API en esta instancia."""


def _ask_clerk(secret: str) -> str:
    """Verifica la clave en el Backend API de Clerk y devuelve el user_id de su subject."""
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
    """Devuelve el user_id dueño de la clave, consultando a Clerk solo si no está en caché."""
    fingerprint = hashlib.sha256(secret.encode()).hexdigest()
    cached = _verified.get(fingerprint)
    if cached is not None and monotonic() < cached[1]:
        return cached[0]

    user_id = _ask_clerk(secret)
    _verified[fingerprint] = (user_id, monotonic() + VERIFIED_KEY_TTL_SECONDS)
    return user_id
