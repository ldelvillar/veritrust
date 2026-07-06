"""
Dependencia para obtener el usuario actual a partir
del token de autenticación en el header Authorization.
"""

import logging
from functools import lru_cache

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

from app.core.config import get_settings
from app.core.errors import make_error_detail
from app.schemas.errors import ErrorCode

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    """Devuelve un cliente JWKS cacheado por URL."""
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=600)


def _get_signing_key(token: str) -> str:
    """Obtiene la clave de firma usando JWKS de Clerk."""
    settings = get_settings()

    if not settings.clerk_jwks_url:
        logger.error("Autenticación mal configurada: falta CLERK_JWKS_URL")
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.AUTH_MISCONFIGURED),
        )

    return _get_jwks_client(settings.clerk_jwks_url).get_signing_key_from_jwt(token).key


def _get_expected_issuer() -> str:
    """Obtiene el issuer esperado de Clerk para validar el claim iss."""
    issuer = get_settings().expected_issuer
    if issuer:
        return issuer

    logger.error(
        "Autenticación mal configurada: falta CLERK_ISSUER o un CLERK_JWKS_URL válido"
    )
    raise HTTPException(
        status_code=500,
        detail=make_error_detail(ErrorCode.AUTH_MISCONFIGURED),
    )


def _get_expected_audience() -> str | list[str]:
    """Obtiene la audiencia esperada de Clerk para validar el claim aud."""
    audience = get_settings().expected_audience()
    if audience is None:
        logger.error("Autenticación mal configurada: falta CLERK_AUDIENCE")
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.AUTH_MISCONFIGURED),
        )

    return audience


def get_current_user(authorization: str = Header(None)) -> dict[str, str]:
    """Dependencia para obtener el usuario actual a partir del token de autenticación."""
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail=make_error_detail(ErrorCode.UNAUTHENTICATED),
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail=make_error_detail(ErrorCode.INVALID_TOKEN),
        )

    token = authorization.replace("Bearer ", "")

    try:
        signing_key = _get_signing_key(token)
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=_get_expected_audience(),
            issuer=_get_expected_issuer(),
            leeway=10,
            options={"verify_aud": True, "verify_iss": True},
        )

    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=401,
            detail=make_error_detail(ErrorCode.EXPIRED_TOKEN),
        ) from e
    except (TypeError, ValueError) as e:
        logger.exception("Autenticación mal configurada: clave de firma inválida")
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.AUTH_MISCONFIGURED),
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=make_error_detail(ErrorCode.INVALID_TOKEN),
        ) from e
