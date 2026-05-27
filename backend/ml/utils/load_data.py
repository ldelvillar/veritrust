"""
Este módulo contiene la función para cargar los datos de las distintas
particiones (train, test, validation) desde archivos Parquet.
"""

import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)

# Definir la ruta relativa al proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Definir la ruta a los archivos de datos con las distintas particiones
TRAIN_PATH = os.path.join(BASE_DIR, "data", "pubhealth_train.parquet")
TEST_PATH = os.path.join(BASE_DIR, "data", "pubhealth_test.parquet")
VALIDATION_PATH = os.path.join(BASE_DIR, "data", "pubhealth_validation.parquet")


def load_dataset(partition: str = "train") -> pd.DataFrame:
    """Función para cargar una partición del dataset."""

    if partition == "train":
        data_path = TRAIN_PATH
    elif partition == "test":
        data_path = TEST_PATH
    elif partition == "validation":
        data_path = VALIDATION_PATH
    else:
        raise ValueError("La partición debe ser 'train', 'test' o 'validation'.")

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"No se encontró el archivo en: {data_path}.")

    logger.info("Cargando datos desde: %s", data_path)

    return pd.read_parquet(data_path)
