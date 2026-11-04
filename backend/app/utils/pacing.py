"""Spacing of the requests to an API that limits how many start per second."""

import threading
from time import monotonic, sleep


class RequestPacer:
    """Book each request a start slot, shared by every thread of the process."""

    def __init__(self) -> None:
        # Earliest instant the next request may start.
        self._next_slot = 0.0
        self._lock = threading.Lock()

    def wait(self, rate: float) -> None:
        """Wait until the next request may start at ``rate`` requests per second."""
        with self._lock:
            now = monotonic()
            slot = max(now, self._next_slot)
            self._next_slot = slot + 1 / rate
        # Sleeps outside the lock, so the other threads can book the following slots.
        sleep(slot - now)
