"""Tests unitarios para el modulo de entrenamiento del modelo."""

from types import SimpleNamespace

import numpy as np
import pandas as pd

from ml.training import train as train_module


def test_pubhealth_dataset_len_and_getitem_returns_expected_tensors() -> None:
    encodings = {
        "input_ids": [[1, 2, 3], [4, 5, 6]],
        "attention_mask": [[1, 1, 1], [1, 1, 0]],
    }
    labels = [0, 1]

    dataset = train_module.PubHealthDataset(encodings, labels)

    assert len(dataset) == 2
    item = dataset[1]
    assert set(item.keys()) == {"input_ids", "attention_mask", "labels"}
    assert item["labels"].item() == 1


def test_compute_metrics_returns_expected_scores() -> None:
    pred = SimpleNamespace(
        label_ids=np.array([0, 1, 1, 0]),
        predictions=np.array(
            [
                [0.9, 0.1],
                [0.1, 0.9],
                [0.8, 0.2],
                [0.7, 0.3],
            ]
        ),
    )

    out = train_module.compute_metrics(pred)

    assert set(out.keys()) == {"accuracy", "f1", "precision", "recall"}
    assert 0.0 <= out["accuracy"] <= 1.0
    assert 0.0 <= out["f1"] <= 1.0
    assert 0.0 <= out["precision"] <= 1.0
    assert 0.0 <= out["recall"] <= 1.0


def test_run_training_smoke_with_mocks(monkeypatch) -> None:
    train_df = pd.DataFrame({"text": ["a", "b"], "label": [0, 1]})
    val_df = pd.DataFrame({"text": ["c"], "label": [1]})

    def fake_load_dataset(partition="train"):
        if partition == "validation":
            return val_df
        return train_df

    monkeypatch.setattr(train_module, "load_dataset", fake_load_dataset)
    monkeypatch.setattr(train_module, "preprocess_data", lambda df: df)

    class _FakeTokenizer:
        def __call__(self, texts, truncation, padding, max_length):
            return {
                "input_ids": [[1, 2, 3] for _ in texts],
                "attention_mask": [[1, 1, 1] for _ in texts],
            }

        def save_pretrained(self, path):
            self.saved_path = path

    class _FakeModel:
        def to(self, device):
            self.device = device

        def save_pretrained(self, path):
            self.saved_path = path

    fake_tokenizer = _FakeTokenizer()
    fake_model = _FakeModel()

    monkeypatch.setattr(
        train_module.BertTokenizer,
        "from_pretrained",
        lambda *args, **kwargs: fake_tokenizer,
    )
    monkeypatch.setattr(
        train_module.BertForSequenceClassification,
        "from_pretrained",
        lambda *args, **kwargs: fake_model,
    )
    monkeypatch.setattr(train_module, "TrainingArguments", lambda **kwargs: kwargs)

    calls = {"train": 0, "evaluate": 0}

    class _FakeTrainer:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def train(self):
            calls["train"] += 1

        def evaluate(self):
            calls["evaluate"] += 1
            return {"eval_f1": 0.8}

    monkeypatch.setattr(train_module, "Trainer", _FakeTrainer)

    train_module.run_training()

    assert calls["train"] == 1
    assert calls["evaluate"] == 1
