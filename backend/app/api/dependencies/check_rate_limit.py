"""Dependencies that enforce rate limits, per user and per IP."""

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
    """Apply the limit with the process's Redis and answer its refusal as 429 or 503."""
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
    """Dependency that enforces the authenticated user's rate limit."""
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
    """Client IP, the last X-Forwarded-For hop, the only one the proxy writes."""
    hops = [
        hop.strip()
        for hop in (request.headers.get("x-forwarded-for") or "").split(",")
        if hop.strip()
    ]
    if hops:
        return hops[-1]
    return request.client.host if request.client else "unknown"


async def check_public_rate_limit(request: Request) -> None:
    """Dependency that rate limits the public endpoints by IP."""
    settings = get_settings()
    await _enforce(
        request,
        key=f"contact_rate_limit:{_client_ip(request)}",
        max_requests=settings.contact_rate_limit_max_requests,
        window=settings.contact_rate_limit_window_seconds,
    )
