"""Sonda de liveness del worker para el healthcheck del contenedor."""

import asyncio
import sys

from arq.connections import RedisSettings
from arq.worker import async_check_health

from app.core.config import get_settings


def main() -> int:
    """Devuelve 0 si el worker escribió un heartbeat reciente, 1 si no."""
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    return asyncio.run(async_check_health(redis_settings))


if __name__ == "__main__":
    sys.exit(main())
