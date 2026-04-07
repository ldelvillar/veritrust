"""Tests unitarios para la función start_ollama."""

import urllib.error
import pytest
from src.utils import start_ollama as start_ollama_module


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

    def fake_urlopen(*args, **kwargs):
        raise urllib.error.URLError("offline")

    def fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))

    monkeypatch.setattr(start_ollama_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(start_ollama_module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        start_ollama_module.time, "sleep", lambda s: sleep_calls.append(s)
    )

    start_ollama_module.start_ollama()

    assert len(popen_calls) == 1
    args, kwargs = popen_calls[0]
    assert args[0] == ["ollama", "serve"]
    assert kwargs["stdout"] == start_ollama_module.subprocess.DEVNULL
    assert kwargs["stderr"] == start_ollama_module.subprocess.DEVNULL
    assert sleep_calls == [3]


def test_start_ollama_exits_when_binary_is_missing(monkeypatch, capsys):
    def fake_urlopen(*args, **kwargs):
        raise urllib.error.URLError("offline")

    def fake_popen(*args, **kwargs):
        raise FileNotFoundError("not found")

    monkeypatch.setattr(start_ollama_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(start_ollama_module.subprocess, "Popen", fake_popen)

    with pytest.raises(SystemExit) as exc:
        start_ollama_module.start_ollama()

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert "No se encuentra 'Ollama'" in captured.out
