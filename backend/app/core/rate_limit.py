"""
Límite de tasa por ventana deslizante sobre Redis, compartido por la API web y el servidor MCP.
"""

import logging
import time
from typing import Any
from uuid import uuid4

from redis.exceptions import RedisError

from app.schemas.errors import ErrorCode

logger = logging.getLogger(__name__)


class RateLimitRefused(Exception):
    """El límite rechazó la petición."""

    def __init__(self, code: ErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


def user_rate_limit_key(user_id: str) -> str:
    """Clave del límite por usuario, compartida por la API web y el servidor MCP."""
    return f"rate_limit:{user_id}"


async def enforce_sliding_window(
    redis: Any, key: str, max_requests: int, window: int
) -> None:
    """Aplica un rate limit de ventana deslizante sobre `key`. Fail-closed si Redis no responde."""
    if redis is None:
        logger.warning("Redis no disponible; se rechaza la petición (fail-closed)")
        raise RateLimitRefused(ErrorCode.SERVICE_UNAVAILABLE)

    now = time.time()
    cutoff = now - window

    try:
        # Poda las marcas fuera de ventana y cuenta las que quedan.
        async with redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            _, count = await pipe.execute()

        if count >= max_requests:
            raise RateLimitRefused(ErrorCode.RATE_LIMIT)

        async with redis.pipeline(transaction=True) as pipe:
            pipe.zadd(key, {f"{now}:{uuid4().hex}": now})
            pipe.expire(key, window)
            await pipe.execute()
    except (RedisError, OSError) as exc:
        logger.warning("Fallo de Redis en el rate limit; se rechaza", exc_info=True)
        raise RateLimitRefused(ErrorCode.SERVICE_UNAVAILABLE) from exc
