"""Token-bucket rate limiter with exponential backoff.

Per-domain throttling is a compliance control, not a nicety — hammering a host
gets your IP range blocked and ends the discovery loop. Connectors share one
limiter per source.

The clock and sleep are injectable so the limiter is fully deterministic under
test (no real waiting, no flakiness).
"""

from __future__ import annotations

import time
from typing import Callable


class RateLimiter:
    def __init__(
        self,
        requests_per_minute: int,
        *,
        now: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.capacity = max(1, requests_per_minute)
        self._tokens = float(self.capacity)
        self._refill_per_second = self.capacity / 60.0
        self._now = now or time.monotonic
        self._sleep = sleep or time.sleep
        self._last = self._now()
        self._backoff_until = 0.0
        self._backoff_seconds = 1.0

    def _refill(self) -> None:
        current = self._now()
        elapsed = current - self._last
        self._tokens = min(self.capacity, self._tokens + elapsed * self._refill_per_second)
        self._last = current

    def acquire(self) -> None:
        """Block (via the injected sleep) until a token is available and any
        active backoff window has elapsed."""
        wait_for_backoff = self._backoff_until - self._now()
        if wait_for_backoff > 0:
            self._sleep(wait_for_backoff)

        self._refill()
        if self._tokens >= 1:
            self._tokens -= 1
            return

        needed_seconds = (1 - self._tokens) / self._refill_per_second
        self._sleep(needed_seconds)
        self._refill()
        self._tokens = max(0.0, self._tokens - 1)

    def backoff(self, max_seconds: float = 60.0) -> None:
        """Call after a 429/503. Doubles the backoff window up to a ceiling."""
        self._backoff_until = self._now() + self._backoff_seconds
        self._backoff_seconds = min(max_seconds, self._backoff_seconds * 2)

    def reset_backoff(self) -> None:
        """Reset backoff after a clean run."""
        self._backoff_seconds = 1.0
        self._backoff_until = 0.0

    @property
    def available_tokens(self) -> float:
        self._refill()
        return self._tokens
