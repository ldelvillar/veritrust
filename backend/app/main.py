"""Archivo principal de la API REST."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.main import create_graph
from app.api.router import api_router
from app.core.cors import get_cors_config
from app.prompts.agents import load_prompts
from app.utils.ollama import ensure_ollama_available

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Inicializa recursos de IA durante startup sin side effects en import."""
    application.state.verification_system = None
    application.state.prompts = None

    try:
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
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        logger.exception("No se pudo inicializar el sistema de verificación: %s", exc)

    yield


app = FastAPI(lifespan=lifespan)
cors_config = get_cors_config()

app.add_middleware(
    CORSMiddleware,
    **cors_config,
)
app.include_router(api_router)
