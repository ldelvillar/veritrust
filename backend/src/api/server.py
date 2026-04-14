"""
API REST para el Sistema Multiagente de Salud.
Conecta el frontend con el flujo de agentes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.agents.main import create_graph
from src.utils.start_ollama import start_ollama
from src.api.router import api_router

app = FastAPI()

# Configurar CORS para solo permitir conexiones desde el frontend y en local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar el sistema
start_ollama()
app.state.verification_system = create_graph()


@app.get("/")
def read_root():
    """Endpoint de prueba para verificar que el servidor está funcionando."""
    return {"status": "online", "service": "API de Verificacion Medica"}


app.include_router(api_router)
