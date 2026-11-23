"""Verification of the Clerk OAuth access tokens MCP clients present."""

import asyncio
import logging

import jwt
from mcp.server.auth.provider import AccessToken
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings
from app.core.jwks import (
    JWKS_FAILED_REFRESH_BACKOFF_SECONDS,
    AuthMisconfigured,
    get_signing_key,
)

logger = logging.getLogger(__name__)


def _decode_oauth_token(token: str) -> AccessToken | None:
    """Validate the signature, issuer and expiry of a Clerk OAuth access token."""
    issuer = get_settings().expected_issuer
    if not issuer:
        logger.error(
            "MCP mal configurado: falta CLERK_ISSUER o un CLERK_JWKS_URL válido"
        )
        return None

    try:
        claims = jwt.decode(
            token,
            get_signing_key(token),
            algorithms=["RS256"],
            issuer=issuer,
            leeway=10,
            options={
                "verify_iss": True,
                "verify_aud": False,
                "require": ["exp", "sub"],
            },
        )
    except jwt.PyJWKClientConnectionError:
        raise
    except jwt.PyJWTError:
        return None
    except AuthMisconfigured:
        logger.error(
            "MCP mal configurado: no se pudo obtener la clave de firma de Clerk"
        )
        return None

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
    """MCP SDK token verifier backed by Clerk's JWKS."""

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return the verified token, ``None`` if it is not a valid OAuth access token, or raise if the JWKS is unreachable."""
        return await asyncio.to_thread(_decode_oauth_token, token)


class JwksUnavailableMiddleware:
    """ASGI middleware that answers 503 when Clerk's JWKS cannot be fetched to verify an access token for the protected path."""

    def __init__(self, app: ASGIApp, protected_path: str) -> None:
        self.app = app
        self.protected_path = protected_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Run the app, answering a JWKS connection error from the token verifier with 503."""
        if scope["type"] != "http" or scope["path"] != self.protected_path:
            # Public routes such as the OAuth metadata ignore the token, so a JWKS outage must not refuse them.
            scope = {
                **scope,
                "headers": [
                    (name, value)
                    for name, value in scope.get("headers", [])
                    if name.lower() != b"authorization"
                ],
            }
            await self.app(scope, receive, send)
            return

        started = False

        async def _send(message: Message) -> None:
            nonlocal started
            started = started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except jwt.PyJWKClientConnectionError as e:
            if started:
                raise
            logger.warning("No se pudo descargar el JWKS de Clerk para el MCP: %s", e)
            response = JSONResponse(
                {
                    "error": "temporarily_unavailable",
                    "error_description": "Could not verify the access token, try again shortly",
                },
                status_code=503,
                headers={"Retry-After": str(int(JWKS_FAILED_REFRESH_BACKOFF_SECONDS))},
            )
            await response(scope, receive, send)
