"""Load the HealthVer partitions (train, test, validation) from Parquet files."""

import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TRAIN_PATH = os.path.join(BASE_DIR, "data", "healthver_train.parquet")
TEST_PATH = os.path.join(BASE_DIR, "data", "healthver_test.parquet")
VALIDATION_PATH = os.path.join(BASE_DIR, "data", "healthver_validation.parquet")

# Hand-written gold set, JSONL so each label can be reviewed in a diff.
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold_es.jsonl")

# Claim and negation pairs over the same literature, which isolate the judge's polarity.
NEGATIONS_PATH = os.path.join(BASE_DIR, "data", "negations_es.jsonl")


def load_dataset(partition: str = "train") -> pd.DataFrame:
    """Load one partition of the dataset."""

    if partition == "train":
        data_path = TRAIN_PATH
    elif partition == "test":
        data_path = TEST_PATH
    elif partition == "validation":
        data_path = VALIDATION_PATH
    elif partition == "gold":
        data_path = GOLD_PATH
    elif partition == "negations":
        data_path = NEGATIONS_PATH
    else:
        raise ValueError(
            "La partición debe ser 'train', 'test', 'validation', 'gold' o 'negations'."
        )

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"No se encontró el archivo en: {data_path}.")

    logger.info("Cargando datos desde: %s", data_path)

    if data_path.endswith(".jsonl"):
        return pd.read_json(data_path, lines=True, encoding="utf-8")

    return pd.read_parquet(data_path)


def load_jsonl(path: str) -> pd.DataFrame:
    """Load a labelled JSONL set from any path, like the held-out one that does not live in the repo."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"No se encontró el archivo en: {path}.")

    logger.info("Cargando datos desde: %s", path)
    return pd.read_json(path, lines=True, encoding="utf-8")
