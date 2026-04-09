"""
API REST para el Sistema Multiagente de Salud.
Conecta el frontend con el flujo de agentes.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.agents.main import create_graph
from src.utils.start_ollama import start_ollama
from src.utils.extract_text_from_url import extract_text_from_url, URLExtractionError
from src.api.schemas import AnalyzeRequest

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
def analyze_news(body: AnalyzeRequest):
    """Endpoint para analizar una noticia utilizando el sistema multiagente."""
    if not body.text and not body.url:
        raise HTTPException(
            status_code=400,
            detail="Se debe proporcionar un texto o una URL para analizar.",
        )

    if body.text and body.url:
        raise HTTPException(
            status_code=400,
            detail="Se debe proporcionar solo uno de los campos: 'text' o 'url', pero no ambos.",
        )

    try:
        text = extract_text_from_url(str(body.url)) if body.url else body.text
    except URLExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        initial_state = {
            "input_text": text,
            "extracted_statements": [],
            "translated_statements": [],
            "label": "",
            "confidence": "",
            "medical_explanation": "",
        }

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
                "status": "warning",
                "message": "No se detectaron afirmaciones medicas verificables en el texto.",
                "explanations": "",
            }

        return {
            "status": "success",
            "label": label,
            "confidence": confidence,
            "explanation": explanation,
        }
    except Exception as e:
        print(f"Error al analizar la noticia: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e
