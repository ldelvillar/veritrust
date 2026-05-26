"""Errores tipados del pipeline de agentes y traducción desde la capa de transporte.

Concentra en un único punto la traducción de excepciones de la capa de
transporte (httpx / cliente de Ollama) a tipos del dominio, de modo que las
capas superiores despachen por **tipo** en lugar de hacer matching de cadenas
sobre ``str(exc)``.

Solo se traducen errores con un discriminador estable (tipo de excepción).
El resto se propagan sin tocar y se mapean a ``INTERNAL`` en la ruta.
"""

import httpx


class AgentError(Exception):
    """Error base del pipeline de agentes."""


class OllamaConnectionError(AgentError):
    """No se pudo conectar al servidor de Ollama."""


async def ainvoke_graph(graph, state: dict) -> dict:
    """Ejecuta el grafo de forma asíncrona y traduce excepciones de conexión.

    LangGraph despacha los nodos síncronos a un threadpool internamente, por
    lo que mantener los agentes en ``def`` no bloquea el event loop.

    - ``ConnectionError`` / ``httpx.ConnectError`` → ``OllamaConnectionError``
    - Resto de excepciones se propagan sin tocar.
    """
    try:
        return await graph.ainvoke(state)
    except (ConnectionError, httpx.ConnectError) as e:
        raise OllamaConnectionError(str(e)) from e
