"""Claves de firma de Clerk: el cliente JWKS que comparten la API web y el servidor MCP."""

import threading
from functools import lru_cache
from time import monotonic
from typing import Any

import jwt
from jwt import PyJWK, PyJWKClient

from app.core.config import get_settings

# Un kid desconocido fuerza como mucho una descarga del JWKS por intervalo, no una por petición.
JWKS_REFRESH_COOLDOWN_SECONDS = 60.0


class AuthMisconfigured(RuntimeError):
    """Falta CLERK_JWKS_URL, así que no hay de dónde obtener las claves de firma."""


class _CooldownJWKClient(PyJWKClient):
    """
    Cliente JWKS que ante un kid desconocido vuelve a
    descargar el JWKS como mucho una vez por intervalo.
    """

    def __init__(self, uri: str, **kwargs: Any) -> None:
        super().__init__(uri, **kwargs)
        self._refresh_lock = threading.Lock()
        self._last_forced_refresh = float("-inf")

    def get_signing_key(self, kid: str) -> PyJWK:
        """
        Devuelve la clave del kid y solo refresca el JWKS si el último refresco forzado quedó atrás.
        """
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
    """Devuelve un cliente JWKS cacheado por URL."""
    return _CooldownJWKClient(jwks_url, cache_keys=True, lifespan=600)


def get_signing_key(token: str) -> str:
    """
    Obtiene la clave de firma del token del JWKS de Clerk.
    Lanza AuthMisconfigured sin CLERK_JWKS_URL.
    """
    jwks_url = get_settings().clerk_jwks_url
    if not jwks_url:
        raise AuthMisconfigured("Falta CLERK_JWKS_URL")

    return _get_jwks_client(jwks_url).get_signing_key_from_jwt(token).key
