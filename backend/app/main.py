"""Archivo principal de la API REST."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.main import create_graph
from app.api.router import api_router
from app.core.config import get_settings
from app.core.cors import get_cors_config
from app.core.logging import configure_logging
from app.db.main import close_pool, get_pool
from app.prompts.agents import load_prompts
from app.utils.ollama import ensure_ollama_available

configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Inicializa recursos de IA durante startup sin side effects en import."""
    application.state.verification_system = None
    application.state.prompts = None

    try:
        get_settings().validate_runtime()
        ensure_ollama_available()
        application.state.prompts = load_prompts()
        prompts = application.state.prompts
        logger.info(
            "Prompts cargados — extractor: %s, translator: %s, health_expert: %s",
            prompts.extractor.version,
            prompts.translator.version,
            prompts.health_expert.version,
        )
        application.state.verification_system = create_graph(prompts)
        await get_pool()
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        logger.exception("No se pudo inicializar el sistema de verificación: %s", exc)

    yield

    await close_pool()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    **get_cors_config(get_settings()),
)
app.include_router(api_router)
