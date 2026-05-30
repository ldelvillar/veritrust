"""Tests unitarios minimos para evaluacion de fact-checking."""

import importlib
import sys
import types


def _load_eval_module(monkeypatch):
    fake_discovery = types.ModuleType("googleapiclient.discovery")
    fake_discovery.build = lambda *args, **kwargs: None

    fake_errors = types.ModuleType("googleapiclient.errors")

    class _HttpError(Exception):
        pass

    fake_errors.HttpError = _HttpError

    fake_google_credentials = types.ModuleType("google.auth.credentials")

    class _AnonymousCredentials:
        pass

    fake_google_credentials.AnonymousCredentials = _AnonymousCredentials

    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", fake_discovery)
    monkeypatch.setitem(sys.modules, "googleapiclient.errors", fake_errors)
    monkeypatch.setitem(sys.modules, "google.auth.credentials", fake_google_credentials)

    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: None)

    sys.modules.pop("ml.evaluation.evaluate_factcheck", None)
    return importlib.import_module("ml.evaluation.evaluate_factcheck")


def test_normalize_veredict_maps_known_labels(monkeypatch) -> None:
    eval_module = _load_eval_module(monkeypatch)

    assert eval_module.normalize_veredict("This is fake and misleading") == "falsa"
    assert (
        eval_module.normalize_veredict("This claim is true and accurate") == "verdadera"
    )
    assert eval_module.normalize_veredict("Unclear rating") == "dudosa"


def test_evaluate_system_returns_zeros_when_no_facts(monkeypatch) -> None:
    eval_module = _load_eval_module(monkeypatch)

    monkeypatch.setattr(eval_module, "extract_api_data", lambda _term: [])
    monkeypatch.setattr(eval_module, "sleep", lambda _seconds: None)

    out = eval_module.evaluate_system(["covid"])

    assert out == {
        "accuracy": 0.0,
        "precision": 0.0,
        "recall": 0.0,
        "f1_score": 0.0,
    }


def test_evaluate_system_computes_metrics_with_mocked_detector(monkeypatch) -> None:
    eval_module = _load_eval_module(monkeypatch)

    facts = [
        {"text": "falsa_ok", "label": "falsa", "source": "A"},
        {"text": "falsa_fail", "label": "falsa", "source": "B"},
        {"text": "verdadera_ok", "label": "verdadera", "source": "C"},
        {"text": "verdadera_fail", "label": "verdadera", "source": "D"},
    ]

    monkeypatch.setattr(eval_module, "extract_api_data", lambda _term: facts)
    monkeypatch.setattr(eval_module, "sleep", lambda _seconds: None)

    class _FakeTool:
        def invoke(self, payload):
            text = payload["text"]
            if text in {"falsa_ok", "verdadera_fail"}:
                return {"label": "falsa"}
            return {"label": "verdadera"}

    monkeypatch.setattr(eval_module, "FakeNewsDetectorTool", _FakeTool)

    out = eval_module.evaluate_system(["health"])

    assert out["accuracy"] == 0.5
    assert out["precision"] == 0.5
    assert out["recall"] == 0.5
    assert out["f1_score"] == 0.5
