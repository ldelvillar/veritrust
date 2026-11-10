"""Unit tests for uploading the evaluation sets to Langfuse."""

from typing import Any

import pandas as pd
import pytest

from evaluation import upload_datasets
from evaluation.upload_datasets import claim_items, stance_items, upload


class FakeLangfuse:
    """Record the datasets and items written, keyed as Langfuse upserts them."""

    def __init__(self) -> None:
        self.datasets: dict[str, str | None] = {}
        self.items: dict[str, dict[str, Any]] = {}

    def create_dataset(self, *, name: str, description: str | None = None) -> None:
        self.datasets[name] = description

    def create_dataset_item(
        self, *, dataset_name: str, id: str | None = None, **fields: Any
    ) -> None:
        assert dataset_name in self.datasets
        assert id is not None
        self.items[id] = {"dataset": dataset_name, **fields}


def test_claim_items_keep_only_binary_labels_with_the_pipeline_eval_labels() -> None:
    df = pd.DataFrame(
        {
            "claim_id": [7, 8, 9],
            "claim": ["Verdad\xa0cierta ", "Bulo", "No se sabe"],
            "label": [0, 1, 2],
            "topic": ["a", "b", "c"],
        }
    )

    items = claim_items(df)

    assert [(i["key"], i["input"], i["expected_output"]) for i in items] == [
        (7, {"text": "Verdad cierta"}, {"label": "verdadera"}),
        (8, {"text": "Bulo"}, {"label": "falsa"}),
    ]
    assert items[0]["metadata"] == {"claim_id": 7, "topic": "a"}


def test_stance_items_ask_for_the_labelled_stance_of_a_source() -> None:
    df = pd.DataFrame(
        [
            {
                "pair_id": 3,
                "set": "gold",
                "claim": "Afirmación",
                "label": "falsa",
                "url": "https://doi.org/x",
                "title": "Título",
                "stance": "refutes",
                "reason": "direct",
                "note": "Nota",
            }
        ]
    )

    [item] = stance_items(df)

    assert item["input"] == {
        "claim": "Afirmación",
        "url": "https://doi.org/x",
        "title": "Título",
    }
    assert item["expected_output"] == {"stance": "refutes"}
    assert item["metadata"] == {
        "pair_id": 3,
        "set": "gold",
        "label": "falsa",
        "reason": "direct",
        "note": "Nota",
    }


def test_uploading_again_updates_the_same_items_without_clashing_across_sets() -> None:
    client = FakeLangfuse()
    df = pd.DataFrame({"claim_id": [1], "claim": ["Bulo"], "label": [1]})

    upload(client, "gold-es", "Oro", claim_items(df))
    upload(client, "gold-es", "Oro", claim_items(df))
    upload(client, "negations-es", "Negaciones", claim_items(df))

    assert set(client.items) == {"gold-es-1", "negations-es-1"}
    assert client.items["gold-es-1"]["expected_output"] == {"label": "falsa"}


def test_every_repo_set_loads_into_items() -> None:
    for _description, load_items in upload_datasets.DATASETS.values():
        assert load_items()


def test_main_refuses_to_run_without_langfuse_keys() -> None:
    with pytest.raises(SystemExit, match="LANGFUSE_PUBLIC_KEY"):
        upload_datasets.main()
