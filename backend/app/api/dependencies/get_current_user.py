"""
Dependencia para obtener el usuario actual a partir
del token de autenticación en el header Authorization.
"""

from functools import lru_cache

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

from app.core.config import get_settings


@lru_cache(maxsize=1)
def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    """Devuelve un cliente JWKS cacheado por URL."""
    return PyJWKClient(jwks_url)


def _get_signing_key(token: str) -> str:
    """Obtiene la clave de firma usando JWKS de Clerk o una PEM configurada."""
    settings = get_settings()

    if settings.clerk_jwks_url:
        return (
            _get_jwks_client(settings.clerk_jwks_url)
            .get_signing_key_from_jwt(token)
            .key
        )

    pem_key = settings.pem_public_key
    if not pem_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "Authentication provider is not configured. Set CLERK_JWKS_URL "
                "or CLERK_PEM_PUBLIC_KEY."
            ),
        )

    return pem_key


def _get_expected_issuer() -> str:
    """Obtiene el issuer esperado de Clerk para validar el claim iss."""
    issuer = get_settings().expected_issuer
    if issuer:
        return issuer

    raise HTTPException(
        status_code=500,
        detail=(
            "Authentication provider is not fully configured. Set CLERK_ISSUER "
            "or a valid CLERK_JWKS_URL."
        ),
    )


def _get_expected_audience() -> str | list[str]:
    """Obtiene la audiencia esperada de Clerk para validar el claim aud."""
    audience = get_settings().expected_audience()
    if audience is None:
        raise HTTPException(
            status_code=500,
            detail="Authentication provider is not fully configured. Set CLERK_AUDIENCE.",
        )

    return audience


def get_current_user(authorization: str = Header(None)) -> dict[str, str]:
    """Dependencia para obtener el usuario actual a partir del token de autenticación."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")

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
        raise HTTPException(status_code=401, detail="Token expired") from e
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=500,
            detail="Authentication provider is configured with an invalid key.",
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e
