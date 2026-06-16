"""Errores tipados del pipeline de agentes y traducción desde la capa de transporte."""

from collections.abc import Awaitable, Callable
from typing import Optional

import httpx


class AgentError(Exception):
    """Error base del pipeline de agentes."""


class OllamaConnectionError(AgentError):
    """No se pudo conectar al servidor de Ollama."""


class BertInferenceError(AgentError):
    """Falló la carga o la inferencia del modelo BERT clasificador."""


async def ainvoke_graph(
    graph,
    state: dict,
    on_stage: Optional[Callable[[str], Awaitable[None]]] = None,
) -> dict:
    """Ejecuta el grafo por streaming, notifica cada agente terminado y traduce errores de conexión."""
    final_state = state
    try:
        async for mode, chunk in graph.astream(
            state, stream_mode=["updates", "values"]
        ):
            if mode == "values":
                final_state = chunk
            elif mode == "updates" and on_stage is not None:
                await on_stage(next(iter(chunk)))
    except (ConnectionError, httpx.ConnectError, httpx.TimeoutException) as e:
        raise OllamaConnectionError(str(e)) from e
    return final_state
