"""Mistral client doubles over a mocked API, shared by the test suites."""

import httpx

from app.utils.llm import _RetryingChatMistralAI


def mistral_reply(message: dict | None = None) -> httpx.Response:
    """A chat completion whose assistant message is ``message``, a plain "hola" by default."""
    return httpx.Response(
        200,
        json={
            "id": "respuesta-de-prueba",
            "object": "chat.completion",
            "model": "mistral-small-latest",
            "choices": [
                {
                    "index": 0,
                    "message": message or {"role": "assistant", "content": "hola"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        },
    )


def mistral_client(handler, *, max_retries: int = 2) -> _RetryingChatMistralAI:
    """A Mistral client paced at 2 requests per second whose API answers with ``handler``."""
    return _RetryingChatMistralAI(
        api_key="clave-de-prueba",
        max_retries=max_retries,
        requests_per_second=2.0,
        client=httpx.Client(
            base_url="https://api.mistral.ai/v1",
            transport=httpx.MockTransport(handler),
        ),
    )
