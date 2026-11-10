"""Upload the labelled evaluation sets to Langfuse as datasets, so eval runs can be linked to their items."""

import logging
from collections.abc import Callable
from typing import Any, TypedDict

import pandas as pd

from app.core.config import get_settings
from app.core.tracing import langfuse
from evaluation.evaluate_pipeline import LANGFUSE_DATASETS, binary_claims
from evaluation.load_data import STANCES_PATH, load_dataset, load_jsonl

logger = logging.getLogger(__name__)


class DatasetItem(TypedDict):
    """A dataset item keyed by its row's own id within the set."""

    key: object
    input: dict[str, Any]
    expected_output: dict[str, Any]
    metadata: dict[str, Any]


def claim_items(df: pd.DataFrame) -> list[DatasetItem]:
    """Turn a labelled claim set into items, keeping the same claims and text the pipeline eval samples."""
    return [
        {
            "key": row["claim_id"],
            "input": {"text": row["text"]},
            "expected_output": {"label": row["expected"]},
            "metadata": {
                k: v
                for k, v in row.items()
                if k not in ("claim", "label", "text", "expected")
            },
        }
        for row in binary_claims(df).to_dict("records")
    ]


def stance_items(df: pd.DataFrame) -> list[DatasetItem]:
    """Turn the hand-labelled Stances into items of a claim and a Source to judge."""
    return [
        {
            "key": row["pair_id"],
            "input": {"claim": row["claim"], "url": row["url"], "title": row["title"]},
            "expected_output": {"stance": row["stance"]},
            "metadata": {
                k: v
                for k, v in row.items()
                if k not in ("claim", "url", "title", "stance")
            },
        }
        for row in df.to_dict("records")
    ]


DATASETS: dict[str, tuple[str, Callable[[], list[DatasetItem]]]] = {
    LANGFUSE_DATASETS["gold"]: (
        "Afirmaciones médicas en español escritas y etiquetadas a mano.",
        lambda: claim_items(load_dataset("gold")),
    ),
    LANGFUSE_DATASETS["negations"]: (
        "Pares de afirmación y su negación sobre la misma literatura.",
        lambda: claim_items(load_dataset("negations")),
    ),
    LANGFUSE_DATASETS["test"]: (
        "Partición de test de HealthVer, sin las afirmaciones NEI.",
        lambda: claim_items(load_dataset("test")),
    ),
    "judge-stances-es": (
        "Posturas etiquetadas a mano de una fuente frente a una afirmación.",
        lambda: stance_items(load_jsonl(STANCES_PATH)),
    ),
}


def upload(client: Any, name: str, description: str, items: list[DatasetItem]) -> None:
    """Create the dataset and upsert its items, so uploading again updates them instead of duplicating."""
    client.create_dataset(name=name, description=description)
    for item in items:
        client.create_dataset_item(
            dataset_name=name,
            # Item ids are unique across every dataset, so the set's name prefixes the row's.
            id=f"{name}-{item['key']}",
            input=item["input"],
            expected_output=item["expected_output"],
            metadata=item["metadata"],
        )


def main() -> None:
    """Script entry point that uploads every evaluation set to the configured Langfuse project."""
    logging.basicConfig(level=logging.INFO)
    if not get_settings().langfuse_enabled():
        raise SystemExit(
            "Configura LANGFUSE_PUBLIC_KEY y LANGFUSE_SECRET_KEY para subir los datasets."
        )

    for name, (description, load_items) in DATASETS.items():
        items = load_items()
        upload(langfuse, name, description, items)
        logger.info("Dataset %s: %d ítems", name, len(items))


if __name__ == "__main__":
    main()
