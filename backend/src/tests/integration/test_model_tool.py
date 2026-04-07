"""Tests de integración para el modelo de detección de noticias falsas."""

import types
import pytest
from pathlib import Path
from src.tools.model_tool import FakeNewsDetectorTool


class _Score:
    def __init__(self, value: float) -> None:
        self._value = value

    def item(self) -> float:
        return self._value


def test_resolve_model_path_uses_env_var_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model_dir = tmp_path / "bert_classifier"
    model_dir.mkdir()
    monkeypatch.setenv("FAKE_NEWS_MODEL_PATH", str(model_dir))

    tool = FakeNewsDetectorTool()
    assert tool.model_path == str(model_dir.resolve())


def test_run_returns_label_and_confidence_with_mocked_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_dir = Path("C:/tmp/model")
    monkeypatch.setenv("FAKE_NEWS_MODEL_PATH", str(model_dir))
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)

    class _FakeTokenizer:
        def __call__(self, *args, **kwargs):
            return {"input_ids": [1, 2, 3]}

    class _FakeModel:
        def __call__(self, **kwargs):
            return types.SimpleNamespace(logits="fake_logits")

    monkeypatch.setattr(
        "src.tools.model_tool.BertTokenizer.from_pretrained",
        lambda *args, **kwargs: _FakeTokenizer(),
    )
    monkeypatch.setattr(
        "src.tools.model_tool.BertForSequenceClassification.from_pretrained",
        lambda *args, **kwargs: _FakeModel(),
    )
    monkeypatch.setattr(
        "src.tools.model_tool.F.softmax",
        lambda logits, dim: [[_Score(0.1), _Score(0.9)]],
    )

    tool = FakeNewsDetectorTool()
    out = tool._run("Texto de prueba")

    assert out["label"] == "falsa"
    assert isinstance(out["confidence"], float)
    assert 0.0 <= out["confidence"] <= 1.0


def test_run_returns_error_when_model_loading_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_dir = Path("C:/tmp/model")
    monkeypatch.setenv("FAKE_NEWS_MODEL_PATH", str(model_dir))
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
    monkeypatch.setattr(
        "src.tools.model_tool.BertTokenizer.from_pretrained",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("broken tokenizer")),
    )

    tool = FakeNewsDetectorTool()
    out = tool._run("Texto de prueba")

    assert out == {"label": "error", "confidence": 0.0}


def test_resolve_model_path_raises_when_no_candidates_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FAKE_NEWS_MODEL_PATH", raising=False)
    monkeypatch.setattr("pathlib.Path.exists", lambda self: False)

    with pytest.raises(FileNotFoundError, match="No se encontro el modelo"):
        FakeNewsDetectorTool()
