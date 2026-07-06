"""Tests unitarios para ensure_ollama_available."""

import http.client
import json
import logging
import urllib.error

import pytest

from app.utils import ollama as ollama_module


class _FakeSettings:
    ollama_base_url = "http://localhost:11434"
    ollama_extractor_model = "llama3"
    ollama_translator_model = "translategemma"
    ollama_health_expert_model = "llama3.2"
    ollama_judge_model = "llama3.2"


_ALL_MODELS_TAGS = {
    "models": [
        {"name": "llama3:latest"},
        {"name": "translategemma:latest"},
        {"name": "llama3.2:latest"},
    ]
}


class _DummyResponse:
    def __init__(self, payload=None):
        self._payload = payload if payload is not None else _ALL_MODELS_TAGS

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture(autouse=True)
def _fake_settings(monkeypatch):
    monkeypatch.setattr(ollama_module, "get_settings", lambda: _FakeSettings())


def test_returns_immediately_when_server_is_up(monkeypatch):
    sleep_calls = []

    monkeypatch.setattr(
        ollama_module.urllib.request,
        "urlopen",
        lambda *args, **kwargs: _DummyResponse(),
    )
    monkeypatch.setattr(ollama_module.time, "sleep", lambda s: sleep_calls.append(s))

    ollama_module.ensure_ollama_available()

    assert sleep_calls == []


def test_retries_until_server_becomes_available(monkeypatch):
    sleep_calls = []
    urlopen_calls = {"count": 0}

    def fake_urlopen(*_args, **_kwargs):
        urlopen_calls["count"] += 1
        if urlopen_calls["count"] < 3:
            raise urllib.error.URLError("offline")
        return _DummyResponse()

    monkeypatch.setattr(ollama_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(ollama_module.time, "sleep", lambda s: sleep_calls.append(s))

    ollama_module.ensure_ollama_available()

    # Dos esperas de liveness; la consulta de modelos ya no reintenta.
    assert urlopen_calls["count"] == 4
    assert len(sleep_calls) == 2


def test_raises_after_all_retries_fail(monkeypatch):
    def fake_urlopen(*_args, **_kwargs):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(ollama_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(ollama_module.time, "sleep", lambda _: None)

    with pytest.raises(ollama_module.OllamaStartupError) as exc:
        ollama_module.ensure_ollama_available()

    assert "localhost:11434" in str(exc.value)


def test_hung_server_raises_startup_error_instead_of_raw_timeout(monkeypatch):
    """Un servidor que acepta la conexión pero nunca responde no debe filtrar TimeoutError."""

    def fake_urlopen(*_args, **_kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(ollama_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(ollama_module.time, "sleep", lambda _: None)

    with pytest.raises(ollama_module.OllamaStartupError):
        ollama_module.ensure_ollama_available()


def test_logs_error_listing_missing_models_without_raising(monkeypatch, caplog):
    """Sin los modelos configurados el worker arranca igual, pero avisa con su lista."""

    def fake_urlopen(url, *args, **kwargs):
        if str(url).endswith("/api/tags"):
            return _DummyResponse({"models": [{"name": "llama3:latest"}]})
        return _DummyResponse()

    monkeypatch.setattr(ollama_module.urllib.request, "urlopen", fake_urlopen)

    with caplog.at_level(logging.ERROR, logger="app.utils.ollama"):
        ollama_module.ensure_ollama_available()

    assert "llama3.2" in caplog.text
    assert "translategemma" in caplog.text


def test_configured_model_matches_server_tag_variants(monkeypatch, caplog):
    """'llama3' de Settings casa con 'llama3:latest' del servidor sin falso negativo."""

    def fake_urlopen(url, *args, **kwargs):
        if str(url).endswith("/api/tags"):
            return _DummyResponse(_ALL_MODELS_TAGS)
        return _DummyResponse()

    monkeypatch.setattr(ollama_module.urllib.request, "urlopen", fake_urlopen)

    with caplog.at_level(logging.ERROR, logger="app.utils.ollama"):
        ollama_module.ensure_ollama_available()

    assert caplog.text == ""


@pytest.mark.parametrize(
    "tags_error",
    [
        TimeoutError("tags colgado"),
        urllib.error.URLError("tags caído"),
        http.client.BadStatusLine("esto no es HTTP"),
        ValueError("JSON inválido"),
    ],
)
def test_tags_endpoint_failure_does_not_block_startup(monkeypatch, tags_error):
    """El check de modelos es secundario: si /api/tags falla, cuelga o responde basura, el arranque continúa."""

    def fake_urlopen(url, *args, **kwargs):
        if str(url).endswith("/api/tags"):
            raise tags_error
        return _DummyResponse()

    monkeypatch.setattr(ollama_module.urllib.request, "urlopen", fake_urlopen)

    ollama_module.ensure_ollama_available()


def test_corrupt_liveness_response_raises_startup_error(monkeypatch):
    """Bytes no-HTTP en el puerto de Ollama no deben filtrar una excepción cruda."""

    def fake_urlopen(*_args, **_kwargs):
        raise http.client.BadStatusLine("esto no es HTTP")

    monkeypatch.setattr(ollama_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(ollama_module.time, "sleep", lambda _: None)

    with pytest.raises(ollama_module.OllamaStartupError):
        ollama_module.ensure_ollama_available()
