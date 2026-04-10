"""
API REST para el Sistema Multiagente de Salud.
Conecta el frontend con el flujo de agentes.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from src.agents.main import create_graph
from src.utils.start_ollama import start_ollama
from src.utils.extract_text_from_url import extract_text_from_url, URLExtractionError
from src.api.schemas import AnalyzeRequest
from src.api.utils import check_rate_limit, get_current_user
from src.api.messages import (
    ERROR_MEMORY_LIMIT,
    ERROR_CONNECTION,
    ERROR_INTERNAL,
    ERROR_NO_MEDICAL_CLAIMS,
)

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


@app.get("/")
def read_root():
    """Endpoint de prueba para verificar que el servidor está funcionando."""
    return {"status": "online", "service": "API de Verificacion Medica"}


@app.post("/analisis")
def analyze_news(body: AnalyzeRequest, user=Depends(get_current_user)):
    """Endpoint para analizar una noticia utilizando el sistema multiagente."""
    user_id = user["sub"]

    check_rate_limit(user_id)

    try:
        text = extract_text_from_url(str(body.url)) if body.url else body.text
    except URLExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    initial_state = {
        "input_text": text,
        "extracted_statements": [],
        "translated_statements": [],
        "label": "",
        "confidence": "",
        "medical_explanation": "",
    }

    try:
        # Ejecutar el grafo
        result = verification_system.invoke(initial_state)

        # Obtener los resultados
        label = result.get("label", "Indefinida")
        confidence = result.get("confidence", "Indefinida")
        explanation = result.get(
            "medical_explanation", "No se pudo obtener la explicación médica."
        )

        if not explanation:
            return {
                "status": "error",
                "message": ERROR_NO_MEDICAL_CLAIMS,
                "explanations": "",
            }

        return {
            "status": "success",
            "label": label,
            "confidence": confidence,
            "explanation": explanation,
        }
    except Exception as e:
        error_msg = str(e).lower()
        print(f"Error al analizar la noticia: {error_msg}")

        # Traducir errores a mensajes para el usuario
        if "model requires more system memory" in error_msg:
            friendly_msg = ERROR_MEMORY_LIMIT
        elif "connection refused" in error_msg or "connect call failed" in error_msg:
            friendly_msg = ERROR_CONNECTION
        else:
            friendly_msg = ERROR_INTERNAL

        raise HTTPException(status_code=500, detail=friendly_msg) from e
