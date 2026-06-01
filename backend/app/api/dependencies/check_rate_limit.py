"""Dependencia para comprobar el límite de tasa del usuario."""

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

    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        # Fail-closed: este endpoint encola un pipeline caro (3 LLM + BERT). Sin
        # Redis no hay control de abuso, así que rechazamos en vez de dejar pasar.
        logger.warning("Redis no disponible; se rechaza el análisis (fail-closed)")
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        )

    settings = get_settings()
    window = settings.rate_limit_window_seconds
    max_requests = settings.rate_limit_max_requests

    now = time.time()
    cutoff = now - window
    key = f"rate_limit:{user_id}"

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

    return user
