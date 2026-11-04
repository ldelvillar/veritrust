"""Tests of the graph invocation wrapper and the translation of transport errors."""

import groq
import httpx
import pytest

from app.agents.errors import OllamaConnectionError, ainvoke_graph

_GROQ_REQUEST = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")


class _FakeGraph:
    """Fake graph that reproduces LangGraph streaming (updates and values modes)."""

    def __init__(self, chunks=(), error=None):
        self._chunks = chunks
        self._error = error
        self.closed = False

    async def astream(self, state, stream_mode=None):
        if self._error is not None:
            raise self._error
        try:
            for chunk in self._chunks:
                yield chunk
        finally:
            self.closed = True


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


async def test_a_stage_callback_that_stops_the_run_closes_the_stream() -> None:
    graph = _FakeGraph(
        [("updates", {"extractor": {}}), ("updates", {"translator": {}})]
    )

    async def on_stage(node: str) -> None:
        raise LookupError(node)

    # This is how the lifecycle stops a deleted Run, so the error arrives intact and the graph does not go on.
    with pytest.raises(LookupError, match="extractor"):
        await ainvoke_graph(graph, {}, on_stage=on_stage)
    assert graph.closed


async def test_ainvoke_graph_translates_connection_error() -> None:
    with pytest.raises(OllamaConnectionError):
        await ainvoke_graph(_FakeGraph(error=ConnectionError("boom")), {})


async def test_ainvoke_graph_translates_httpx_connect_error() -> None:
    with pytest.raises(OllamaConnectionError):
        await ainvoke_graph(_FakeGraph(error=httpx.ConnectError("down")), {})


async def test_ainvoke_graph_translates_httpx_timeout_error() -> None:
    with pytest.raises(OllamaConnectionError):
        await ainvoke_graph(_FakeGraph(error=httpx.ReadTimeout("slow")), {})


async def test_ainvoke_graph_translates_a_dropped_response() -> None:
    # Mistral closing the connection mid-answer is as unreachable as never connecting.
    with pytest.raises(OllamaConnectionError):
        await ainvoke_graph(_FakeGraph(error=httpx.RemoteProtocolError("dropped")), {})


async def test_ainvoke_graph_lets_a_misconfigured_url_through() -> None:
    # A base URL without a scheme is our fault, so it stays an internal error with no Retry to wait for.
    with pytest.raises(httpx.UnsupportedProtocol):
        await ainvoke_graph(
            _FakeGraph(error=httpx.UnsupportedProtocol("no scheme")), {}
        )


async def test_ainvoke_graph_translates_groq_connection_error() -> None:
    error = groq.APIConnectionError(request=_GROQ_REQUEST)

    with pytest.raises(OllamaConnectionError):
        await ainvoke_graph(_FakeGraph(error=error), {})


async def test_ainvoke_graph_translates_groq_timeout_error() -> None:
    error = groq.APITimeoutError(request=_GROQ_REQUEST)

    with pytest.raises(OllamaConnectionError):
        await ainvoke_graph(_FakeGraph(error=error), {})


def _mistral_status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://api.mistral.ai/v1/chat/completions")
    return httpx.HTTPStatusError(
        f"{status}", request=request, response=httpx.Response(status, request=request)
    )


@pytest.mark.parametrize("status", [429, 503])
async def test_ainvoke_graph_translates_a_rate_limit_or_server_error_after_the_retries(
    status,
) -> None:
    # The client already retried them, so the provider is down or limiting us, as with a failed connection.
    with pytest.raises(OllamaConnectionError):
        await ainvoke_graph(_FakeGraph(error=_mistral_status_error(status)), {})


async def test_ainvoke_graph_lets_a_client_error_through() -> None:
    # A 400 is a fault in our request, not an outage, so it stays an internal error.
    with pytest.raises(httpx.HTTPStatusError):
        await ainvoke_graph(_FakeGraph(error=_mistral_status_error(400)), {})
