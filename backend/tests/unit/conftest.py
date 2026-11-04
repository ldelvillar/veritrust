"""Fixtures shared by the unit tests."""

import pytest

from app.utils import pubmed


class FakeClock:
    """Clock for PubMed's request pacing, where sleeping only moves time forward."""

    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def pubmed_clock(monkeypatch):
    """Pace PubMed's requests on a fake clock, so no test waits in real time."""
    fake = FakeClock()
    monkeypatch.setattr(pubmed, "monotonic", fake.monotonic)
    monkeypatch.setattr(pubmed, "sleep", fake.sleep)
    monkeypatch.setattr(pubmed, "_next_slot", 0.0)
    return fake
