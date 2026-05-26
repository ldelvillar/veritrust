"""Tests unitarios para el módulo de carga de datos."""

import pandas as pd
import pytest

from ml.utils import load_data


def test_load_dataset_raises_for_invalid_partition() -> None:
    with pytest.raises(ValueError, match="partición"):
        load_data.load_dataset("dev")


def test_load_dataset_raises_when_file_does_not_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(load_data, "TRAIN_PATH", "C:/tmp/train.parquet")
    monkeypatch.setattr(load_data.os.path, "exists", lambda _path: False)

    with pytest.raises(FileNotFoundError, match="No se encontró el archivo"):
        load_data.load_dataset("train")


def test_load_dataset_reads_expected_partition_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_path = "C:/tmp/test.parquet"
    fake_df = pd.DataFrame({"text": ["a"], "label": [1]})

    monkeypatch.setattr(load_data, "TEST_PATH", expected_path)
    monkeypatch.setattr(load_data.os.path, "exists", lambda _path: True)

    captured = {"path": None}

    def fake_read_parquet(path: str) -> pd.DataFrame:
        captured["path"] = path
        return fake_df

    monkeypatch.setattr(load_data.pd, "read_parquet", fake_read_parquet)

    out = load_data.load_dataset("test")

    assert captured["path"] == expected_path
    pd.testing.assert_frame_equal(out, fake_df)


def test_load_dataset_reads_validation_partition_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_path = "C:/tmp/validation.parquet"
    fake_df = pd.DataFrame({"text": ["valid"], "label": [0]})

    monkeypatch.setattr(load_data, "VALIDATION_PATH", expected_path)
    monkeypatch.setattr(load_data.os.path, "exists", lambda _path: True)

    captured = {"path": None}

    def fake_read_parquet(path: str) -> pd.DataFrame:
        captured["path"] = path
        return fake_df

    monkeypatch.setattr(load_data.pd, "read_parquet", fake_read_parquet)

    out = load_data.load_dataset("validation")

    assert captured["path"] == expected_path
    pd.testing.assert_frame_equal(out, fake_df)


def test_load_dataset_uses_train_partition_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_path = "C:/tmp/train-default.parquet"
    fake_df = pd.DataFrame({"text": ["train"], "label": [1]})

    monkeypatch.setattr(load_data, "TRAIN_PATH", expected_path)
    monkeypatch.setattr(load_data.os.path, "exists", lambda _path: True)

    captured = {"path": None}

    def fake_read_parquet(path: str) -> pd.DataFrame:
        captured["path"] = path
        return fake_df

    monkeypatch.setattr(load_data.pd, "read_parquet", fake_read_parquet)

    out = load_data.load_dataset()

    assert captured["path"] == expected_path
    pd.testing.assert_frame_equal(out, fake_df)
