"""Tests of the graph invocation wrapper and the translation of transport errors."""

import groq
import httpx
import pytest

from app.agents.errors import OllamaConnectionError, ainvoke_graph
from app.utils.llm import LLMUnavailableError

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


_MISTRAL_REQUEST = httpx.Request("POST", "https://api.mistral.ai/v1/chat/completions")


@pytest.mark.parametrize(
    "error",
    [
        ConnectionError("boom"),
        httpx.ConnectError("down"),
        httpx.ReadTimeout("slow"),
        # Mistral closing the connection mid-answer is as unreachable as never connecting.
        httpx.RemoteProtocolError("dropped"),
        groq.APIConnectionError(request=_GROQ_REQUEST),
        groq.APITimeoutError(request=_GROQ_REQUEST),
        # The client gives up on a 429 or 5xx only after its retries, so the provider is down or limiting us.
        LLMUnavailableError("429"),
    ],
    ids=lambda error: type(error).__name__,
)
async def test_ainvoke_graph_translates_an_unreachable_provider(error) -> None:
    with pytest.raises(OllamaConnectionError):
        await ainvoke_graph(_FakeGraph(error=error), {})


@pytest.mark.parametrize(
    "error",
    [
        # A base URL without a scheme is our fault, so there is no Retry to wait for.
        httpx.UnsupportedProtocol("no scheme"),
        # A 400 is a fault in our request, not an outage.
        httpx.HTTPStatusError(
            "400",
            request=_MISTRAL_REQUEST,
            response=httpx.Response(400, request=_MISTRAL_REQUEST),
        ),
    ],
    ids=lambda error: type(error).__name__,
)
async def test_ainvoke_graph_lets_our_own_errors_through_as_internal(error) -> None:
    with pytest.raises(type(error)):
        await ainvoke_graph(_FakeGraph(error=error), {})
