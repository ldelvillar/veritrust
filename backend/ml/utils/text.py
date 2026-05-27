"""Utilidades de limpieza de texto compartidas entre entrenamiento e inferencia."""

import re

MAX_SEQUENCE_LENGTH = 128


def clean_text(text: str) -> str:
    """Limpia el texto para el entrenamiento del modelo BERT."""
    if not isinstance(text, str):
        return ""

    # Convertir el texto a minúsculas
    text = text.lower()

    # Quitar URLs
    text = re.sub(r"http\S+|www\S+|https\S+", "", text, flags=re.MULTILINE)

    # Reemplazar comillas múltiples por una sola comilla
    text = re.sub(r'"+', '"', text)

    # Normalizar espacios
    text = re.sub(r"\s+", " ", text).strip()

    # Eliminar comillas al inicio y al final del texto
    text = text.strip('"').strip()

    return text
