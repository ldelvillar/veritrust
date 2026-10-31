"""Worker liveness probe for the container healthcheck."""

import asyncio
import sys

from arq.connections import RedisSettings
from arq.worker import async_check_health

from app.core.config import get_settings


def main() -> int:
    """Return 0 if the worker wrote a recent heartbeat, 1 otherwise."""
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    return asyncio.run(async_check_health(redis_settings))


if __name__ == "__main__":
    sys.exit(main())
