"""
Este módulo contiene la función para cargar los datos de las distintas
particiones (train, test, validation) de HealthVer desde archivos Parquet.
"""

import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)

# Definir la ruta relativa al proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Definir la ruta a los archivos de datos con las distintas particiones
TRAIN_PATH = os.path.join(BASE_DIR, "data", "healthver_train.parquet")
TEST_PATH = os.path.join(BASE_DIR, "data", "healthver_test.parquet")
VALIDATION_PATH = os.path.join(BASE_DIR, "data", "healthver_validation.parquet")

# Conjunto oro escrito a mano: JSONL para poder revisar cada etiqueta en un diff
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold_es.jsonl")


def load_dataset(partition: str = "train") -> pd.DataFrame:
    """Función para cargar una partición del dataset."""

    if partition == "train":
        data_path = TRAIN_PATH
    elif partition == "test":
        data_path = TEST_PATH
    elif partition == "validation":
        data_path = VALIDATION_PATH
    elif partition == "gold":
        data_path = GOLD_PATH
    else:
        raise ValueError(
            "La partición debe ser 'train', 'test', 'validation' o 'gold'."
        )

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"No se encontró el archivo en: {data_path}.")

    logger.info("Cargando datos desde: %s", data_path)

    if data_path.endswith(".jsonl"):
        return pd.read_json(data_path, lines=True, encoding="utf-8")

    return pd.read_parquet(data_path)
