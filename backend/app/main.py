"""Archivo principal de la API REST."""

import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from app.api.router import api_router
from app.core.config import get_settings
from app.core.cors import get_cors_config
from app.core.logging import configure_logging
from app.db.pool import close_pool, get_pool
from app.mcp.server import (
    MCP_METADATA_PATH,
    MCP_PATH,
    build_mcp_http_app,
    build_mcp_server,
)

configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Inicializa los recursos del proceso web."""
    application.state.arq_pool = None
    application.state.redis = None
    application.state.mcp_http_app = None

    settings = get_settings()
    settings.validate_runtime()
    await get_pool()
    application.state.arq_pool = await create_pool(
        RedisSettings.from_dsn(settings.redis_url)
    )
    application.state.redis = aioredis.from_url(settings.redis_url)

    mcp_server = build_mcp_server(
        arq_pool=application.state.arq_pool, redis=application.state.redis
    )
    application.state.mcp_http_app = build_mcp_http_app(mcp_server)
    logger.info("Proceso web listo: pool de Redis y de base de datos abiertos")

    async with mcp_server.session_manager.run():
        yield

    if application.state.arq_pool is not None:
        await application.state.arq_pool.close()
    if application.state.redis is not None:
        await application.state.redis.aclose()
    await close_pool()


class _McpDispatcher:
    """Reenvía las rutas MCP a la app del SDK construida en el lifespan."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Delega en la app MCP o responde 503 si el proceso aún no está listo."""
        mcp_app = getattr(scope["app"].state, "mcp_http_app", None)
        if mcp_app is None:
            response = JSONResponse({"detail": "Service not ready"}, status_code=503)
            await response(scope, receive, send)
            return
        await mcp_app(scope, receive, send)


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    **get_cors_config(get_settings()),
)
app.include_router(api_router)
for _mcp_path in (MCP_PATH, MCP_METADATA_PATH):
    app.router.routes.append(
        Route(_mcp_path, endpoint=_McpDispatcher(), include_in_schema=False)
    )
