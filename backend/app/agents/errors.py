"""Typed errors of the agent pipeline and their translation from the transport layer."""

from collections.abc import Awaitable, Callable
from contextlib import aclosing
from typing import Any, Optional

import aiohttp
import groq
import httpx

from app.core.tracing import langfuse, langfuse_handler
from app.utils.llm import LLMUnavailableError


class AgentError(Exception):
    """Base error of the agent pipeline."""


class OllamaConnectionError(AgentError):
    """Could not connect to the Ollama server."""


class EvidenceUnavailable(AgentError):
    """A searched claim's sources all failed, so the Run has no Verdict (ADR-0006)."""


async def ainvoke_graph(
    graph: Any,
    state: dict,
    on_stage: Optional[Callable[[str], Awaitable[None]]] = None,
) -> dict:
    """Stream the graph, report each finished agent and translate connection errors."""
    final_state = state
    try:
        # One current span, so @observe spans and LangChain's land in the same trace.
        with langfuse.start_as_current_observation(name="pipeline", as_type="chain"):
            async with aclosing(
                graph.astream(
                    state,
                    stream_mode=["updates", "values"],
                    config={"callbacks": [langfuse_handler]},
                )
            ) as stream:
                async for mode, chunk in stream:
                    if mode == "values":
                        final_state = chunk
                    elif mode == "updates" and on_stage is not None:
                        await on_stage(next(iter(chunk)))
    except (
        ConnectionError,
        httpx.NetworkError,
        httpx.TimeoutException,
        httpx.RemoteProtocolError,
        aiohttp.ClientError,
        groq.APIConnectionError,
        LLMUnavailableError,
    ) as e:
        raise OllamaConnectionError(str(e)) from e
    return final_state
