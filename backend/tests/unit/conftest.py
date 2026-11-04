"""Fixtures shared by the unit tests."""

import pytest

from app.utils import llm, pacing, pubmed
from app.utils.pacing import RequestPacer


class FakeClock:
    """Clock for request pacing, where sleeping only moves time forward."""

    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def pacing_clock(monkeypatch):
    """Pace PubMed's and Mistral's requests on a fake clock from fresh pacers, so no test waits in real time."""
    fake = FakeClock()
    monkeypatch.setattr(pacing, "monotonic", fake.monotonic)
    monkeypatch.setattr(pacing, "sleep", fake.sleep)
    monkeypatch.setattr(pubmed, "_pacer", RequestPacer())
    monkeypatch.setattr(llm, "_mistral_pacer", RequestPacer())
    return fake
