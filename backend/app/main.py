"""Archivo principal de la API REST."""

import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.cors import get_cors_config
from app.core.logging import configure_logging
from app.db.pool import close_pool, get_pool

configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Inicializa los recursos del proceso web."""
    application.state.arq_pool = None
    application.state.redis = None

    try:
        settings = get_settings()
        settings.validate_runtime()
        await get_pool()
        application.state.arq_pool = await create_pool(
            RedisSettings.from_dsn(settings.redis_url)
        )
        application.state.redis = aioredis.from_url(settings.redis_url)
        logger.info("Proceso web listo: pool de Redis y de base de datos abiertos")
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        logger.exception("No se pudo inicializar el proceso web: %s", exc)

    yield

    if application.state.arq_pool is not None:
        await application.state.arq_pool.close()
    if application.state.redis is not None:
        await application.state.redis.aclose()
    await close_pool()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    **get_cors_config(get_settings()),
)
app.include_router(api_router)
