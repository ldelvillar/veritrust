"""
Dependencia para obtener el usuario actual a partir
del token de autenticación en el header Authorization.
"""

import logging

import jwt
from fastapi import Header, HTTPException

from app.core.config import get_settings
from app.core.errors import make_error_detail
from app.core.jwks import AuthMisconfigured, get_signing_key
from app.schemas.errors import ErrorCode

logger = logging.getLogger(__name__)


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
        signing_key = get_signing_key(token)
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
    except jwt.PyJWKClientConnectionError as e:
        logger.warning("No se pudo descargar el JWKS de Clerk: %s", e)
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        ) from e
    except jwt.PyJWKClientError as e:
        raise HTTPException(
            status_code=401,
            detail=make_error_detail(ErrorCode.INVALID_TOKEN),
        ) from e
    except AuthMisconfigured as e:
        logger.error("Autenticación mal configurada: falta CLERK_JWKS_URL")
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.AUTH_MISCONFIGURED),
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
