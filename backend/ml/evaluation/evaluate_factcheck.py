"""
Este módulo extrae verificaciones de la API de Google Fact Check Tools y ejecuta
el sistema multiagente para evaluarlas una por una, comparando los resultados
con los datos originales para calcular metricas de precision del modelo.
"""

import logging
import os
import sys
from pathlib import Path
from time import sleep, time

from dotenv import load_dotenv
from google.auth.credentials import AnonymousCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Asegurar que al ejecutar este archivo como script, se use el código local del repositorio.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.tools.model_tool import FakeNewsDetectorTool
from app.utils.ollama import ensure_ollama_available

logger = logging.getLogger(__name__)

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def normalize_veredict(original_veredict: str) -> str:
    """Convierte textos arbitrarios de distintos verificadores a formato binario."""
    text = original_veredict.lower()

    if (
        "false" in text
        or "fake" in text
        or "hoax" in text
        or "misleading" in text
        or "incorrect" in text
        or "untrue" in text
    ):
        return "falsa"
    if (
        "true" in text
        or "truth" in text
        or "correct" in text
        or "accurate" in text
        or "real" in text
    ):
        return "verdadera"

    return "dudosa"


def extract_api_data(search_term: str) -> list:
    """Consulta Google Fact Check Tools a través de su API."""
    statements_list = []
    page_token = None

    try:
        # Inicializar el cliente de la API
        service = build(
            "factchecktools",
            "v1alpha1",
            developerKey=GOOGLE_API_KEY,
            credentials=AnonymousCredentials(),
        )

        while True:
            # Ejecutar peticion de busqueda
            response = (
                service.claims()
                .search(
                    query=search_term,
                    languageCode="en",
                    pageToken=page_token,
                    pageSize=100,
                )
                .execute()
            )

            # Validar existencia de resultados
            if "claims" not in response:
                break

            # Extraer y limpiar datos
            for claim in response["claims"]:
                text = claim.get("text", "")
                reviews = claim.get("claimReview", [])

                # Procesar solo si existe revision formal
                if reviews:
                    veredict = normalize_veredict(reviews[0].get("textualRating", ""))

                    # Descartar etiquetas ambiguas para una evaluacion binaria estricta
                    if veredict != "dudosa":
                        statements_list.append(
                            {
                                "text": text,
                                "label": veredict,
                                "source": reviews[0]
                                .get("publisher", {})
                                .get("name", "Desconocida"),
                            }
                        )
            # Verificar si hay mas paginas de resultados
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return statements_list

    except HttpError:
        logger.exception("Error de infraestructura al conectar con Google")
        if len(statements_list) > 0:
            logger.info(
                "Se han preservado datos recuperados hasta el corte de conexion"
            )

        return statements_list


def evaluate_system(search_terms: list[str]) -> dict[str, float]:
    """
    Extrae afirmaciones de Google Fact Check Tools sobre un conjunto de
    términos de búsqueda y compara el resultado del sistema multiagente
    con los datos originales. Calcula el porcentaje de acierto final.
    """
    start_time = time()
    total_facts = []

    logger.info("Iniciando extraccion de verificaciones...")
    for term in search_terms:
        total_facts.extend(extract_api_data(term))
        # Pausar ejecucion para evitar bloqueo por limite de cuota de API
        sleep(2)

    total_analyzed = len(total_facts)
    if total_analyzed == 0:
        logger.warning("Ausencia de datos para analizar.")
        return {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
        }

    tp = fp = tn = fn = 0
    bert_tool = FakeNewsDetectorTool()

    logger.info("Iniciando inferencia sobre muestras recuperadas...")

    for fact in total_facts:
        text = fact["text"]
        original_label = fact["label"]

        # Ejecutar inferencia local
        result = bert_tool.invoke({"text": text})
        logger.debug("Resultado del detector: %s", result)
        system_label = result.get("label", "")

        # Actualizar matriz de confusion
        if original_label == "falsa":
            if system_label == "falsa":
                tp += 1
            else:
                fn += 1
        elif original_label == "verdadera":
            if system_label == "verdadera":
                tn += 1
            else:
                fp += 1

    # Calcular y reportar metricas
    accuracy = (tp + tn) / (tp + tn + fp + fn)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0

    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )

    execution_time = time() - start_time

    logger.info("Resultados finales:")
    logger.info("Muestras procesadas: %d", tp + tn + fp + fn)
    logger.info("TP: %d, TN: %d, FP: %d, FN: %d", tp, tn, fp, fn)
    logger.info("Accuracy: %.2f", accuracy)
    logger.info("Precision: %.2f", precision)
    logger.info("Recall: %.2f", recall)
    logger.info("F1-score: %.2f", f1)
    logger.info("Tiempo de ejecución: %.2f segundos", execution_time)

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    terms = [
        # Vacunas y Enfermedades Infecciosas
        "vaccine",
        "COVID",
        "mRNA",
        "monkeypox",
        "flu shot",
        "polio",
        "fauci",
        "spike protein",
        # "Curas Milagrosas" y Tóxicos
        "bleach",
        "ivermectin",
        "hydroxychloroquine",
        "miracle cure",
        "parasite cleanse",
        "chlorine dioxide",
        "colloidal silver",
        # Enfermedades Crónicas y Graves
        "cancer cure",
        "chemotherapy",
        "heart attack",
        "diabetes",
        "tumor",
        "cardiac arrest",
        "stroke",
        "blood clot",
        # Nutrición, Dietas y Alimentos
        "seed oils",
        "raw milk",
        "detox",
        "vegan",
        "sugar",
        "aspartame",
        "alkaline water",
        "fasting",
        "superfood",
        # Pseudociencia y Teorías de la Conspiración Sanitarias
        "5G",
        "microchip",
        "chemtrails",
        "fluoride",
        "vaccine shedding",
        "dna alter",
        "immune system boost",
        "homeopathy",
    ]
    ensure_ollama_available()
    evaluate_system(terms)
