"""Tests for the shared compliance controls: rate limiter + robots policy.

Both inject their clock / fetcher so the tests are deterministic and offline.
"""

from __future__ import annotations

from packages.discovery.connectors.rate_limiter import RateLimiter
from packages.discovery.connectors.robots import RobotsDisallowed, RobotsPolicy


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += max(0.0, seconds)


def test_rate_limiter_allows_burst_up_to_capacity() -> None:
    clock = FakeClock()
    limiter = RateLimiter(2, now=clock.now, sleep=clock.sleep)  # capacity 2
    limiter.acquire()
    limiter.acquire()
    assert clock.t == 0.0  # two tokens available immediately, no waiting


def test_rate_limiter_waits_when_exhausted() -> None:
    clock = FakeClock()
    limiter = RateLimiter(2, now=clock.now, sleep=clock.sleep)  # refill 2/60 per sec
    limiter.acquire()
    limiter.acquire()
    limiter.acquire()  # third must wait for a refill
    assert clock.t > 0.0


def test_rate_limiter_backoff_doubles_and_blocks() -> None:
    clock = FakeClock()
    limiter = RateLimiter(60, now=clock.now, sleep=clock.sleep)
    limiter.backoff()
    before = clock.t
    limiter.acquire()  # must sleep through the backoff window
    assert clock.t > before
    limiter.reset_backoff()
    assert limiter.available_tokens >= 0


ROBOTS_TXT = "User-agent: *\nDisallow: /private\nAllow: /\n"


def test_robots_allows_and_disallows_paths() -> None:
    policy = RobotsPolicy(lambda host: ROBOTS_TXT)
    assert policy.can_fetch("https://example.com/public", "bot") is True
    assert policy.can_fetch("https://example.com/private/x", "bot") is False


def test_robots_missing_file_allows() -> None:
    policy = RobotsPolicy(lambda host: None)  # no robots.txt
    assert policy.can_fetch("https://example.com/anything", "bot") is True


def test_robots_fetch_error_fails_closed() -> None:
    def boom(host: str) -> str:
        raise RuntimeError("network down")

    policy = RobotsPolicy(boom, fail_closed_on_error=True)
    assert policy.can_fetch("https://example.com/x", "bot") is False


def test_robots_caches_per_host() -> None:
    calls: list[str] = []

    def fetcher(host: str) -> str:
        calls.append(host)
        return ROBOTS_TXT

    policy = RobotsPolicy(fetcher)
    policy.can_fetch("https://example.com/a", "bot")
    policy.can_fetch("https://example.com/b", "bot")
    assert calls == ["https://example.com"]  # fetched once, then cached


def test_robots_assert_raises() -> None:
    policy = RobotsPolicy(lambda host: ROBOTS_TXT)
    try:
        policy.assert_can_fetch("https://example.com/private/x", "bot")
        raise AssertionError("expected RobotsDisallowed")
    except RobotsDisallowed:
        pass


def test_robots_rejects_relative_url() -> None:
    policy = RobotsPolicy(lambda host: ROBOTS_TXT)
    assert policy.can_fetch("/no-scheme", "bot") is False
