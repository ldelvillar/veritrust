"""Upload the labelled evaluation sets to Langfuse as datasets, so eval runs can be linked to their items."""

import logging
import os
from collections.abc import Callable
from typing import Any, Protocol, TypedDict

import pandas as pd

from app.core.config import get_settings
from app.core.tracing import langfuse
from evaluation.evaluate_pipeline import LABEL_BY_CODE, LANGFUSE_DATASETS
from evaluation.load_data import BASE_DIR, load_dataset, load_jsonl

logger = logging.getLogger(__name__)

STANCES_PATH = os.path.join(BASE_DIR, "data", "judge_stances_es.jsonl")


class DatasetItem(TypedDict):
    """A dataset item keyed by its row's own id within the set."""

    key: object
    input: dict[str, Any]
    expected_output: dict[str, Any]
    metadata: dict[str, Any]


class DatasetClient(Protocol):
    """The part of the Langfuse client that writes datasets."""

    def create_dataset(self, *, name: str, description: str | None = None) -> Any:
        """Create or update a dataset by name."""

    def create_dataset_item(
        self,
        *,
        dataset_name: str,
        input: Any = None,
        expected_output: Any = None,
        metadata: Any = None,
        id: str | None = None,
    ) -> Any:
        """Create or update a dataset item by id."""


def claim_items(df: pd.DataFrame, key: str) -> list[DatasetItem]:
    """Turn a labelled claim set into items, leaving out the claims with no binary label, as the pipeline eval does."""
    df = df[df["label"].isin(LABEL_BY_CODE)]
    return [
        {
            "key": row[key],
            # Same cleanup as load_samples, so a run can match its samples to the items.
            "input": {"text": str(row["claim"]).replace("\xa0", " ").strip()},
            "expected_output": {"label": LABEL_BY_CODE[row["label"]]},
            "metadata": {k: v for k, v in row.items() if k not in ("claim", "label")},
        }
        for row in df.to_dict("records")
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
        lambda: claim_items(load_dataset("gold"), "claim_id"),
    ),
    LANGFUSE_DATASETS["negations"]: (
        "Pares de afirmación y su negación sobre la misma literatura.",
        lambda: claim_items(load_dataset("negations"), "claim_id"),
    ),
    LANGFUSE_DATASETS["test"]: (
        "Partición de test de HealthVer, sin las afirmaciones NEI.",
        lambda: claim_items(load_dataset("test"), "claim_id"),
    ),
    "judge-stances-es": (
        "Posturas etiquetadas a mano de una fuente frente a una afirmación.",
        lambda: stance_items(load_jsonl(STANCES_PATH)),
    ),
}


def upload(
    client: DatasetClient, name: str, description: str, items: list[DatasetItem]
) -> None:
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
