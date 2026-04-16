"""Archivo principal de la API REST."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.main import create_graph
from app.api.cors import get_cors_config
from app.utils.start_ollama import start_ollama
from app.api.router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Inicializa recursos de IA durante startup sin side effects en import."""
    application.state.verification_system = None

    try:
        start_ollama()
        application.state.verification_system = create_graph()
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


@app.get("/")
def read_root():
    """Endpoint de prueba para verificar que el servidor está funcionando."""
    return {"status": "online", "service": "API de Verificacion Medica"}
