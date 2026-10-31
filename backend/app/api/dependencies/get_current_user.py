"""Dependency that resolves the current user from the token in the Authorization header."""

import logging

import jwt
from fastapi import Header, HTTPException

from app.core.api_keys import (
    API_KEY_PREFIX,
    ApiKeysMisconfigured,
    ClerkUnreachable,
    InvalidApiKey,
    verify_api_key,
)
from app.core.config import get_settings
from app.core.errors import make_error_detail
from app.core.jwks import AuthMisconfigured, get_signing_key
from app.schemas.errors import ErrorCode

logger = logging.getLogger(__name__)


def _user_from_api_key(secret: str) -> dict[str, str]:
    """Verify a Clerk API key and return the user it belongs to."""
    try:
        return {"sub": verify_api_key(secret)}
    except InvalidApiKey as e:
        raise HTTPException(
            status_code=401,
            detail=make_error_detail(ErrorCode.INVALID_TOKEN),
        ) from e
    except ClerkUnreachable as e:
        logger.warning("No se pudo verificar la clave API con Clerk: %s", e)
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        ) from e
    except ApiKeysMisconfigured as e:
        logger.error(
            "Claves API mal configuradas (CLERK_SECRET_KEY o activación en Clerk): %s",
            e,
        )
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.AUTH_MISCONFIGURED),
        ) from e


def _get_expected_issuer() -> str:
    """Return Clerk's expected issuer to validate the iss claim."""
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
    """Return Clerk's expected audience to validate the aud claim."""
    audience = get_settings().expected_audience()
    if audience is None:
        logger.error("Autenticación mal configurada: falta CLERK_AUDIENCE")
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.AUTH_MISCONFIGURED),
        )

    return audience


def get_current_user(authorization: str = Header(None)) -> dict[str, str]:
    """Dependency that resolves the current user from the authentication token."""
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
    if token.startswith(API_KEY_PREFIX):
        return _user_from_api_key(token)

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
