"""
Dependencia para obtener el usuario actual a partir
del token de autenticación en el header Authorization.
"""

import os

import jwt
from jwt import PyJWKClient
from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()

CLERK_PEM_PUBLIC_KEY = os.environ.get("CLERK_PEM_PUBLIC_KEY")
CLERK_JWKS_URL = os.environ.get("CLERK_JWKS_URL")
CLERK_ISSUER = os.environ.get("CLERK_ISSUER")
CLERK_AUDIENCE = os.environ.get("CLERK_AUDIENCE")

jwks_client = PyJWKClient(CLERK_JWKS_URL) if CLERK_JWKS_URL else None


def _normalize_pem_key(key: str | None) -> str | None:
    """Normaliza claves PEM definidas en variables de entorno con \n escapados."""
    if not key:
        return None
    return key.replace("\\n", "\n").strip()


def _get_signing_key(token: str) -> str:
    """Obtiene la clave de firma usando JWKS de Clerk o una PEM configurada."""
    if jwks_client:
        return jwks_client.get_signing_key_from_jwt(token).key

    pem_key = _normalize_pem_key(CLERK_PEM_PUBLIC_KEY)
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
    issuer = (CLERK_ISSUER or "").strip()
    if issuer:
        return issuer

    jwks_url = (CLERK_JWKS_URL or "").strip()
    suffix = "/.well-known/jwks.json"
    if jwks_url.endswith(suffix):
        return jwks_url[: -len(suffix)]

    raise HTTPException(
        status_code=500,
        detail=(
            "Authentication provider is not fully configured. Set CLERK_ISSUER "
            "or a valid CLERK_JWKS_URL."
        ),
    )


def _get_expected_audience() -> str | list[str]:
    """Obtiene la audiencia esperada de Clerk para validar el claim aud."""
    raw_audience = (CLERK_AUDIENCE or "").strip()
    if not raw_audience:
        raise HTTPException(
            status_code=500,
            detail="Authentication provider is not fully configured. Set CLERK_AUDIENCE.",
        )

    audiences = [aud.strip() for aud in raw_audience.split(",") if aud.strip()]
    return audiences if len(audiences) > 1 else audiences[0]


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
