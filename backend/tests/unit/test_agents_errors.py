"""Tests del envoltorio de invocación del grafo y la traducción de errores de transporte."""

import httpx
import pytest

from app.agents.errors import OllamaConnectionError, ainvoke_graph


class _FakeGraph:
    """Grafo de mentira que reproduce el streaming de LangGraph (modos updates + values)."""

    def __init__(self, chunks=(), error=None):
        self._chunks = chunks
        self._error = error

    async def astream(self, state, stream_mode=None):
        if self._error is not None:
            raise self._error
        for chunk in self._chunks:
            yield chunk


async def test_ainvoke_graph_returns_last_values_chunk_and_reports_stages() -> None:
    chunks = [
        ("values", {"step": "inicial"}),
        ("updates", {"extractor": {}}),
        ("updates", {"translator": {}}),
        ("values", {"step": "final", "label": "falsa"}),
    ]
    seen: list[str] = []

    async def on_stage(node: str) -> None:
        seen.append(node)

    result = await ainvoke_graph(_FakeGraph(chunks), {}, on_stage=on_stage)

    assert seen == ["extractor", "translator"]
    assert result == {"step": "final", "label": "falsa"}


async def test_ainvoke_graph_works_without_stage_callback() -> None:
    chunks = [("values", {"label": "verdadera"})]

    result = await ainvoke_graph(_FakeGraph(chunks), {})

    assert result == {"label": "verdadera"}


async def test_ainvoke_graph_translates_connection_error() -> None:
    with pytest.raises(OllamaConnectionError):
        await ainvoke_graph(_FakeGraph(error=ConnectionError("boom")), {})


async def test_ainvoke_graph_translates_httpx_connect_error() -> None:
    with pytest.raises(OllamaConnectionError):
        await ainvoke_graph(_FakeGraph(error=httpx.ConnectError("down")), {})
