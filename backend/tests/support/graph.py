"""Compiled graph double of the app tests."""


class FakeGraph:
    """Fake graph that streams like LangGraph (updates and values modes) and records the states it receives."""

    def __init__(self, chunks=(), error=None):
        self._chunks = chunks
        self._error = error
        self.seen: list[dict] = []
        self.closed = False

    async def astream(self, state, stream_mode=None, config=None):
        self.seen.append(state)
        if self._error is not None:
            raise self._error
        try:
            for chunk in self._chunks:
                yield chunk
        finally:
            self.closed = True


def graph_ending_in(final: dict, stages=()) -> FakeGraph:
    """Fake graph that finishes each of ``stages`` and ends with ``final`` as its state."""
    return FakeGraph(
        [*(("updates", {stage: {}}) for stage in stages), ("values", final)]
    )
