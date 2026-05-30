"""Tests de integración para el modelo de detección de noticias falsas."""

import types
from pathlib import Path

import pytest

from app.agents.errors import BertInferenceError
from app.core.config import Settings
from app.tools.model_tool import FakeNewsDetectorTool


class _Score:
    def __init__(self, value: float) -> None:
        self._value = value

    def item(self) -> float:
        return self._value


def _patch_model_path(monkeypatch: pytest.MonkeyPatch, model_path: str | None) -> None:
    """Inyecta una configuración con la ruta del modelo deseada."""
    settings = Settings(_env_file=None, fake_news_model_path=model_path)  # type: ignore[call-arg]
    monkeypatch.setattr("app.tools.model_tool.get_settings", lambda: settings)


def test_resolve_model_path_uses_configured_path_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model_dir = tmp_path / "bert_classifier"
    model_dir.mkdir()
    _patch_model_path(monkeypatch, str(model_dir))

    tool = FakeNewsDetectorTool()
    assert tool.model_path == str(model_dir.resolve())


def test_run_returns_label_and_confidence_with_mocked_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_model_path(monkeypatch, "C:/tmp/model")
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)

    class _FakeTokenizer:
        def __call__(self, *args, **kwargs):
            return {"input_ids": [1, 2, 3]}

    class _FakeModel:
        def __call__(self, **kwargs):
            return types.SimpleNamespace(logits="fake_logits")

    monkeypatch.setattr(
        "app.tools.model_tool.BertTokenizer.from_pretrained",
        lambda *args, **kwargs: _FakeTokenizer(),
    )
    monkeypatch.setattr(
        "app.tools.model_tool.BertForSequenceClassification.from_pretrained",
        lambda *args, **kwargs: _FakeModel(),
    )
    monkeypatch.setattr(
        "app.tools.model_tool.F.softmax",
        lambda logits, dim: [[_Score(0.1), _Score(0.9)]],
    )

    tool = FakeNewsDetectorTool()
    out = tool._run("Texto de prueba")

    assert out["label"] == "falsa"
    assert isinstance(out["confidence"], float)
    assert 0.0 <= out["confidence"] <= 1.0


def test_run_raises_bert_inference_error_when_model_loading_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_model_path(monkeypatch, "C:/tmp/model")
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
    monkeypatch.setattr(
        "app.tools.model_tool.BertTokenizer.from_pretrained",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("broken tokenizer")),
    )

    tool = FakeNewsDetectorTool()

    # Un fallo de carga del modelo no debe degradar a una etiqueta inventada:
    # se propaga como error tipado para que el análisis acabe en 'failed'.
    with pytest.raises(BertInferenceError):
        tool._run("Texto de prueba")


def test_resolve_model_path_raises_when_no_candidates_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_model_path(monkeypatch, None)
    monkeypatch.setattr("pathlib.Path.exists", lambda self: False)

    with pytest.raises(FileNotFoundError, match="No se encontro el modelo"):
        FakeNewsDetectorTool()


def test_ensure_bert_detector_ready_fails_fast_without_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El warm-up del worker falla pronto si no hay modelo local resoluble."""
    from app.agents import health_expert

    # El detector se cachea por clase; limpiamos para forzar la resolución.
    health_expert._build_bert_tool.cache_clear()
    _patch_model_path(monkeypatch, None)
    monkeypatch.setattr("pathlib.Path.exists", lambda self: False)

    with pytest.raises(FileNotFoundError, match="No se encontro el modelo"):
        health_expert.ensure_bert_detector_ready()

    health_expert._build_bert_tool.cache_clear()
