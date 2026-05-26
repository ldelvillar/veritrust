"""Tests unitarios para ensure_ollama_available."""

import urllib.error

import pytest

from app.utils import ollama as ollama_module


class _DummyResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


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

    assert urlopen_calls["count"] == 3
    assert len(sleep_calls) == 2


def test_raises_after_all_retries_fail(monkeypatch):
    def fake_urlopen(*_args, **_kwargs):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(ollama_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(ollama_module.time, "sleep", lambda _: None)

    with pytest.raises(ollama_module.OllamaStartupError) as exc:
        ollama_module.ensure_ollama_available()

    assert "localhost:11434" in str(exc.value)
