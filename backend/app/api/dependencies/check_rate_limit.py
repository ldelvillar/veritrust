"""Dependencias para comprobar límites de tasa (por usuario y por IP)."""

from fastapi import Depends, HTTPException, Request

from app.api.dependencies.get_current_user import get_current_user
from app.core.config import get_settings
from app.core.errors import make_error_detail
from app.core.rate_limit import (
    RateLimitRefused,
    enforce_sliding_window,
    user_rate_limit_key,
)
from app.schemas.errors import ErrorCode


async def _enforce(
    request: Request, *, key: str, max_requests: int, window: int
) -> None:
    """Aplica el límite con el Redis del proceso y responde su rechazo como 429 o 503."""
    try:
        await enforce_sliding_window(
            getattr(request.app.state, "redis", None),
            key=key,
            max_requests=max_requests,
            window=window,
        )
    except RateLimitRefused as exc:
        status_code = 429 if exc.code == ErrorCode.RATE_LIMIT else 503
        raise HTTPException(
            status_code=status_code, detail=make_error_detail(exc.code)
        ) from exc


async def check_rate_limit(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    """Dependencia que verifica el rate limit del usuario autenticado."""
    user_id = user["sub"]
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail=make_error_detail(ErrorCode.INVALID_TOKEN),
        )

    settings = get_settings()
    await _enforce(
        request,
        key=user_rate_limit_key(user_id),
        max_requests=settings.rate_limit_max_requests,
        window=settings.rate_limit_window_seconds,
    )
    return user


def _client_ip(request: Request) -> str:
    """IP del cliente: el último salto de X-Forwarded-For, el único que escribe el proxy."""
    hops = [
        hop.strip()
        for hop in (request.headers.get("x-forwarded-for") or "").split(",")
        if hop.strip()
    ]
    if hops:
        return hops[-1]
    return request.client.host if request.client else "unknown"


async def check_public_rate_limit(request: Request) -> None:
    """Dependencia que limita por IP los endpoints públicos (sin autenticación)."""
    settings = get_settings()
    await _enforce(
        request,
        key=f"contact_rate_limit:{_client_ip(request)}",
        max_requests=settings.contact_rate_limit_max_requests,
        window=settings.contact_rate_limit_window_seconds,
    )
