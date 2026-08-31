"""
Este módulo se encarga de la limpieza y preparación
de los datos para el entrenamiento del modelo BERT.
"""

import logging

import pandas as pd

from ml.utils.text import clean_text

logger = logging.getLogger(__name__)


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """Función principal para procesar los datos para el entrenamiento del modelo BERT."""
    logger.info("Iniciando preprocesado...")
    logger.info("Filas iniciales: %d", len(df))

    # Eliminar columnas innecesarias
    df = df.drop(columns=["claim_id"], errors="ignore")

    # HealthVer ya trae 0=SUPPORT, 1=CONTRADICT y 2=NEI en el orden de CLASS_LABELS
    df["label"] = df["label"].astype(int)

    # Limpiar texto de la columna 'claim' y eliminar filas vacías tras la limpieza
    df["claim"] = df["claim"].apply(clean_text)
    df = df[df["claim"] != ""]

    # Renombrar la columna 'claim' para asegurar compatibilidad con la librería transformers
    df = df.rename(columns={"claim": "text"})

    logger.info("Filas tras el preprocesado: %d", len(df))
    logger.info("Distribución: %s", df["label"].value_counts().to_dict())

    return df
