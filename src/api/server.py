"""
API REST para el Sistema Multiagente de Salud.
Conecta el frontend con el flujo de agentes.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.agents.main import create_graph
from src.utils.start_ollama import start_ollama

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
verification_system = create_graph()


class AnalyzeRequest(BaseModel):
    """Modelo de datos para la solicitud de análisis."""

    text: str


@app.get("/")
def read_root():
    """Endpoint de prueba para verificar que el servidor está funcionando."""
    return {"status": "online", "service": "API de Verificacion Medica"}


@app.post("/analisis")
def analyze_news(body: AnalyzeRequest):
    """Endpoint para analizar una noticia utilizando el sistema multiagente."""
    text = body.text
    try:
        initial_state = {
            "input_text": text,
            "extracted_statements": [],
            "translated_statements": [],
            "clinical_explanations": [],
        }

        # Ejecutar el grafo
        result = verification_system.invoke(initial_state)

        # Obtener las explicaciones generadas
        explanations = result.get("clinical_explanations", [])

        if not explanations or "No se detectaron afirmaciones" in explanations[0]:
            return {
                "status": "warning",
                "message": "No se detectaron afirmaciones medicas verificables en el texto.",
                "explanations": [],
            }

        return {"status": "success", "explanations": explanations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
