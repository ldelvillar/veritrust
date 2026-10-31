"""Typed errors of the agent pipeline and their translation from the transport layer."""

from collections.abc import Awaitable, Callable
from contextlib import aclosing
from typing import Any, Optional

import aiohttp
import groq
import httpx


class AgentError(Exception):
    """Base error of the agent pipeline."""


class OllamaConnectionError(AgentError):
    """Could not connect to the Ollama server."""


async def ainvoke_graph(
    graph: Any,
    state: dict,
    on_stage: Optional[Callable[[str], Awaitable[None]]] = None,
) -> dict:
    """Stream the graph, report each finished agent and translate connection errors."""
    final_state = state
    try:
        # aclosing closes the stream at once when on_stage cuts the Run short.
        async with aclosing(
            graph.astream(state, stream_mode=["updates", "values"])
        ) as stream:
            async for mode, chunk in stream:
                if mode == "values":
                    final_state = chunk
                elif mode == "updates" and on_stage is not None:
                    await on_stage(next(iter(chunk)))
    except (
        ConnectionError,
        httpx.ConnectError,
        httpx.TimeoutException,
        aiohttp.ClientError,
        groq.APIConnectionError,
    ) as e:
        raise OllamaConnectionError(str(e)) from e
    return final_state
