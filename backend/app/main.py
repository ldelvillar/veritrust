"""Entry point of the REST API."""

import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from app.api.dependencies.analysis_intake import refusal_response
from app.api.router import api_router
from app.core.analysis_jobs import ArqAnalysisQueue
from app.core.analysis_lifecycle import AnalysisIntake, AnalysisRefused
from app.core.config import get_settings
from app.core.cors import get_cors_config
from app.core.errors import make_error_detail
from app.core.logging import configure_logging
from app.db.history import HiddenAnalysis
from app.db.pool import close_pool, get_pool
from app.mcp.server import (
    MCP_METADATA_PATH,
    MCP_PATH,
    build_mcp_http_app,
    build_mcp_server,
)
from app.schemas.errors import ErrorCode

configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Set up the web process's resources."""
    application.state.arq_pool = None
    application.state.redis = None
    application.state.analysis_intake = None
    application.state.mcp_http_app = None

    settings = get_settings()
    settings.validate_runtime()
    await get_pool()
    application.state.arq_pool = await create_pool(
        RedisSettings.from_dsn(settings.redis_url)
    )
    application.state.redis = aioredis.from_url(settings.redis_url)
    application.state.analysis_intake = AnalysisIntake(
        ArqAnalysisQueue(application.state.arq_pool),
        max_file_bytes=settings.max_file_bytes,
    )

    mcp_server = build_mcp_server(
        arq_pool=application.state.arq_pool,
        redis=application.state.redis,
        analysis_intake=application.state.analysis_intake,
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
    """Forward the MCP routes to the SDK app built in the lifespan."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Delegate to the MCP app or answer 503 if the process is not ready yet."""
        mcp_app = getattr(scope["app"].state, "mcp_http_app", None)
        if mcp_app is None:
            response = JSONResponse({"detail": "Service not ready"}, status_code=503)
            await response(scope, receive, send)
            return
        await mcp_app(scope, receive, send)


app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def _validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Answer validation 422s with the structured detail, quoting the first error."""
    errors = exc.errors()
    message = str(errors[0]["msg"]) if errors else None
    return JSONResponse(
        status_code=422,
        content={"detail": make_error_detail(ErrorCode.VALIDATION, message)},
    )


@app.exception_handler(AnalysisRefused)
async def _analysis_refused(request: Request, exc: AnalysisRefused) -> JSONResponse:
    """Answer a lifecycle refusal with its HTTP status and the contract detail."""
    return refusal_response(exc)


@app.exception_handler(HiddenAnalysis)
async def _hidden_analysis(request: Request, exc: HiddenAnalysis) -> JSONResponse:
    """Answer an Analysis outside the History window with 403, so the frontend shows the upsell and not a 404."""
    return JSONResponse(
        status_code=403,
        content={"detail": make_error_detail(ErrorCode.PLAN_REQUIRED)},
    )


app.add_middleware(
    CORSMiddleware,
    **get_cors_config(get_settings()),
)
app.include_router(api_router)
for _mcp_path in (MCP_PATH, MCP_METADATA_PATH):
    app.router.routes.append(
        Route(_mcp_path, endpoint=_McpDispatcher(), include_in_schema=False)
    )
