"""Errores tipados del pipeline de agentes y traducción desde la capa de transporte."""

import httpx


class AgentError(Exception):
    """Error base del pipeline de agentes."""


class OllamaConnectionError(AgentError):
    """No se pudo conectar al servidor de Ollama."""


class BertInferenceError(AgentError):
    """Falló la carga o la inferencia del modelo BERT clasificador."""


async def ainvoke_graph(graph, state: dict) -> dict:
    """Ejecuta el grafo de forma asíncrona y traduce excepciones de conexión."""
    try:
        return await graph.ainvoke(state)
    except (ConnectionError, httpx.ConnectError) as e:
        raise OllamaConnectionError(str(e)) from e
