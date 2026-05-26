"""
Este módulo se encarga de la limpieza y preparación
de los datos para el entrenamiento del modelo BERT.
"""

import re

import pandas as pd

from ml.utils.text import clean_text


def clean_list_string(text: str) -> str:
    """
    Normaliza listas de entidades separadas por '&', 'and' o ','
    a un formato estándar separado por comas.
    Ej: "David Biller And Mauricio Savarese" -> "David Biller, Mauricio Savarese"
    """
    if not isinstance(text, str):
        return ""

    # Reemplazar '&' y ' and ' por comas
    text = re.sub(r"\s*(&|\band\b)\s*", ",", text, flags=re.IGNORECASE)

    # Dividir por comas y limpiar espacios extra en cada elemento
    items = [item.strip() for item in text.split(",") if item.strip()]

    # Unir de nuevo con una coma y espacio estándar
    return ", ".join(items)


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """Función principal para procesar los datos para el entrenamiento del modelo BERT."""
    print("Iniciando preprocesado...")
    print(f"Filas inciales: {len(df)}")

    # Eliminar columnas innecesarias
    df = df.drop(columns=["claim_id", "subjects"], errors="ignore")

    # Descartar noticias con la etiqueta 'unproven'
    df = df[df["label"].isin([0, 1, 3])].copy()

    # Convertir la etiqueta 'mixture' en 'false'
    df["label"] = df["label"].replace(
        {
            3: 1,
        }
    )

    # Limpiar texto de las columnas 'explanation' y 'main_text'
    df["explanation"] = df["explanation"].fillna("").apply(clean_text)
    df["main_text"] = df["main_text"].fillna("").apply(clean_text)

    # Limpiar texto de la columna 'claim' y eliminar filas vacías tras la limpieza
    df["claim"] = df["claim"].apply(clean_text)
    df = df[df["claim"] != ""]

    # Renombrar la columna 'claim' para asegurar compatibilidad con la librería transformers
    df = df.rename(columns={"claim": "text"})

    # Estandarizar la fecha a formato datetime
    df["date_published"] = pd.to_datetime(
        df["date_published"], format="%B %d, %Y", errors="coerce"
    )

    # Estandarizar las listas de 'fact_checkers' y 'sources'
    df["fact_checkers"] = df["fact_checkers"].apply(clean_list_string)
    df["sources"] = df["sources"].apply(clean_list_string)

    print(f"Filas tras el preprocesado: {len(df)}")
    print(f"Distribución: {df['label'].value_counts().to_dict()}")

    return df
