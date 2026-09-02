"""Dependencias para comprobar límites de tasa (por usuario y por IP)."""

import logging
import time
from uuid import uuid4

from fastapi import Depends, HTTPException, Request
from redis.exceptions import RedisError

from app.api.dependencies.get_current_user import get_current_user
from app.core.config import get_settings
from app.core.errors import make_error_detail
from app.schemas.errors import ErrorCode

logger = logging.getLogger(__name__)


async def _enforce_sliding_window(
    request: Request, key: str, max_requests: int, window: int
) -> None:
    """Aplica un rate limit de ventana deslizante sobre `key`; falla cerrado si Redis no responde."""
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        # Fail-closed: sin Redis no hay control de abuso, así que rechazamos.
        logger.warning("Redis no disponible; se rechaza la petición (fail-closed)")
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        )

    now = time.time()
    cutoff = now - window

    try:
        # Poda las marcas fuera de ventana y cuenta las que quedan.
        async with redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            _, count = await pipe.execute()

        if count >= max_requests:
            raise HTTPException(
                status_code=429,
                detail=make_error_detail(ErrorCode.RATE_LIMIT),
            )

        async with redis.pipeline(transaction=True) as pipe:
            pipe.zadd(key, {f"{now}:{uuid4().hex}": now})
            pipe.expire(key, window)
            await pipe.execute()
    except (RedisError, OSError) as exc:
        # Fail-closed: si no podemos contabilizar la petición, no la dejamos pasar.
        logger.warning("Fallo de Redis en el rate limit; se rechaza", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
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
    await _enforce_sliding_window(
        request,
        key=f"rate_limit:{user_id}",
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
    await _enforce_sliding_window(
        request,
        key=f"contact_rate_limit:{_client_ip(request)}",
        max_requests=settings.contact_rate_limit_max_requests,
        window=settings.contact_rate_limit_window_seconds,
    )
