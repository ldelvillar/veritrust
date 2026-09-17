"""Verificación de los access tokens OAuth de Clerk que presentan los clientes MCP."""

import asyncio
import logging

import jwt
from fastapi import HTTPException
from mcp.server.auth.provider import AccessToken

from app.api.dependencies.get_current_user import _get_signing_key
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _decode_oauth_token(token: str) -> AccessToken | None:
    """Valida firma, emisor y caducidad de un access token OAuth de Clerk."""
    issuer = get_settings().expected_issuer
    if not issuer:
        logger.error(
            "MCP mal configurado: falta CLERK_ISSUER o un CLERK_JWKS_URL válido"
        )
        return None

    try:
        claims = jwt.decode(
            token,
            _get_signing_key(token),
            algorithms=["RS256"],
            issuer=issuer,
            leeway=10,
            options={
                "verify_iss": True,
                "verify_aud": False,
                "require": ["exp", "sub"],
            },
        )
    except jwt.PyJWTError:
        return None
    except HTTPException:
        logger.error(
            "MCP mal configurado: no se pudo obtener la clave de firma de Clerk"
        )
        return None

    # RFC 9068: un access token OAuth lleva client_id; un token de sesión del navegador no.
    client_id = claims.get("client_id")
    if not isinstance(client_id, str) or not client_id:
        return None

    raw_scopes = claims.get("scope") or claims.get("scp") or ""
    scopes = raw_scopes.split() if isinstance(raw_scopes, str) else list(raw_scopes)

    return AccessToken(
        token=token,
        client_id=client_id,
        scopes=scopes,
        expires_at=int(claims["exp"]),
        subject=str(claims["sub"]),
        claims={"iss": claims.get("iss")},
    )


class ClerkOAuthTokenVerifier:
    """Verificador de tokens del SDK MCP respaldado por el JWKS de Clerk."""

    async def verify_token(self, token: str) -> AccessToken | None:
        """Devuelve el token verificado o ``None`` si no es un access token OAuth válido."""
        return await asyncio.to_thread(_decode_oauth_token, token)
