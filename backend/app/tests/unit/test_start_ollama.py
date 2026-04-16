"""Tests unitarios para la función start_ollama."""

import urllib.error
import pytest

from app.utils import start_ollama as start_ollama_module


class _DummyResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_start_ollama_does_not_spawn_when_server_is_up(monkeypatch):
    popen_calls = []

    monkeypatch.setattr(
        start_ollama_module.urllib.request,
        "urlopen",
        lambda *args, **kwargs: _DummyResponse(),
    )
    monkeypatch.setattr(
        start_ollama_module.subprocess,
        "Popen",
        lambda *args, **kwargs: popen_calls.append((args, kwargs)),
    )

    start_ollama_module.start_ollama()

    assert popen_calls == []


def test_start_ollama_spawns_server_when_connection_fails(monkeypatch):
    popen_calls = []
    sleep_calls = []
    urlopen_calls = {"count": 0}

    def fake_urlopen(*_args, **_kwargs):
        urlopen_calls["count"] += 1
        if urlopen_calls["count"] == 1:
            raise urllib.error.URLError("offline")
        return _DummyResponse()

    def fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(start_ollama_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(start_ollama_module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(start_ollama_module.time, "sleep", fake_sleep)

    start_ollama_module.start_ollama()

    assert len(popen_calls) == 1
    args, kwargs = popen_calls[0]
    assert args[0] == ["ollama", "serve"]
    assert kwargs["stdout"] == start_ollama_module.subprocess.DEVNULL
    assert kwargs["stderr"] == start_ollama_module.subprocess.DEVNULL
    assert sleep_calls == [3]


def test_start_ollama_raises_when_binary_is_missing(monkeypatch):
    def fake_urlopen(*args, **kwargs):
        raise urllib.error.URLError("offline")

    def fake_popen(*args, **kwargs):
        raise FileNotFoundError("not found")

    monkeypatch.setattr(start_ollama_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(start_ollama_module.subprocess, "Popen", fake_popen)

    with pytest.raises(start_ollama_module.OllamaStartupError) as exc:
        start_ollama_module.start_ollama()

    assert "No se encuentra 'Ollama'" in str(exc.value)
