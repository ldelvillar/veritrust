"""Tests unitarios para el modulo de entrenamiento del modelo."""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd

from ml.training import train as train_module


def test_git_sha_returns_short_hash_from_git(monkeypatch) -> None:
    monkeypatch.setattr(
        train_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="abc1234\n"),
    )
    assert train_module._git_sha() == "abc1234"


def test_git_sha_returns_unknown_when_git_unavailable(monkeypatch) -> None:
    def _raise(*args, **kwargs):
        raise OSError("git not found")

    monkeypatch.setattr(train_module.subprocess, "run", _raise)
    assert train_module._git_sha() == "unknown"


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


def test_run_training_smoke_with_mocks(monkeypatch, tmp_path) -> None:
    train_df = pd.DataFrame({"text": ["a", "b"], "label": [0, 1]})
    val_df = pd.DataFrame({"text": ["c"], "label": [1]})

    def fake_load_dataset(partition="train"):
        if partition == "validation":
            return val_df
        # 'train' y 'test' devuelven el df de 2 filas para distinguirlos de val (1).
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
    seed_calls = []
    monkeypatch.setattr(train_module, "set_seed", seed_calls.append)

    captured_args: dict = {}

    def _fake_training_args(**kwargs):
        captured_args.update(kwargs)
        return kwargs

    monkeypatch.setattr(train_module, "TrainingArguments", _fake_training_args)

    calls = {"train": 0, "evaluate": 0}

    class _FakeTrainer:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def train(self):
            calls["train"] += 1

        def evaluate(self, eval_dataset=None):
            calls["evaluate"] += 1
            calls["evaluate_dataset"] = eval_dataset
            return {"eval_f1": 0.8}

    monkeypatch.setattr(train_module, "Trainer", _FakeTrainer)

    # Escribir el modelo versionado bajo tmp_path con un SHA determinista.
    monkeypatch.setattr(train_module, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(train_module, "_git_sha", lambda: "testsha")

    train_module.run_training()

    assert calls["train"] == 1
    assert calls["evaluate"] == 1
    # La métrica final se calcula sobre test (2 filas), no sobre validación (1 fila).
    assert len(calls["evaluate_dataset"]) == 2
    # Entrenamiento reproducible: semilla fijada y propagada al Trainer.
    assert seed_calls == [train_module.SEED]
    assert captured_args["seed"] == train_module.SEED
    assert captured_args["data_seed"] == train_module.SEED

    # El modelo se guarda en un único directorio versionado, no sobre OUTPUT_DIR.
    version_dirs = [child for child in tmp_path.iterdir() if child.is_dir()]
    assert len(version_dirs) == 1
    version_dir = version_dirs[0]
    assert version_dir.name.endswith("-testsha")
    assert fake_model.saved_path == version_dir
    assert fake_tokenizer.saved_path == version_dir

    # metadata.json registra procedencia: SHA, tamaños de partición y métricas.
    metadata = json.loads((version_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["git_sha"] == "testsha"
    assert metadata["partition_sizes"] == {"train": 2, "validation": 1, "test": 2}
    assert metadata["test_metrics"] == {"eval_f1": 0.8}
    assert metadata["base_model"] == train_module.MODEL_NAME
