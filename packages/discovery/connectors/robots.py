"""robots.txt policy.

Connectors that fetch HTML check this before requesting a path. Disallowed
paths are not crawled. The result is cached per host so we fetch robots.txt at
most once per host per process.

The robots fetcher is injectable so tests never hit the network. If robots.txt
cannot be retrieved we FAIL OPEN for ``allow`` only on a clean 404 (no rules);
any other fetch error fails CLOSED (treated as disallowed) because the safe
default for a compliance control is to not crawl.
"""

from __future__ import annotations

from typing import Callable
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


class RobotsDisallowed(RuntimeError):
    """Raised when a URL is disallowed by the host's robots.txt."""


# A fetcher returns the robots.txt body for a host, or None if there is no
# robots.txt (HTTP 404 / empty), or raises to signal a hard fetch failure.
RobotsFetcher = Callable[[str], "str | None"]


class RobotsPolicy:
    def __init__(self, fetcher: RobotsFetcher, *, fail_closed_on_error: bool = True) -> None:
        self._fetcher = fetcher
        self._fail_closed_on_error = fail_closed_on_error
        self._cache: dict[str, RobotFileParser | None] = {}

    def _robots_for(self, host_root: str) -> RobotFileParser | None:
        if host_root in self._cache:
            return self._cache[host_root]
        body = self._fetcher(host_root)
        if body is None:
            # No robots.txt at all => nothing is disallowed.
            self._cache[host_root] = None
            return None
        parser = RobotFileParser()
        parser.parse(body.splitlines())
        self._cache[host_root] = parser
        return parser

    def can_fetch(self, url: str, user_agent: str) -> bool:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        host_root = f"{parsed.scheme}://{parsed.netloc}"
        try:
            parser = self._robots_for(host_root)
        except Exception:
            # Hard fetch failure: fail closed (don't crawl) unless told otherwise.
            return not self._fail_closed_on_error
        if parser is None:
            return True  # no robots.txt => allowed
        return parser.can_fetch(user_agent, url)

    def assert_can_fetch(self, url: str, user_agent: str) -> None:
        if not self.can_fetch(url, user_agent):
            raise RobotsDisallowed(f"robots.txt disallows {user_agent} from {url}")

    @classmethod
    def from_httpx(
        cls,
        *,
        client: "object | None" = None,
        user_agent: str = "ai-company-os-discovery/1.0",
        timeout: float = 10.0,
        fail_closed_on_error: bool = True,
    ) -> "RobotsPolicy":
        """Build a policy whose fetcher actually retrieves ``/robots.txt`` over
        HTTP. This is what an HTML connector wires up; the API connectors that
        ship today don't need it. The httpx client is injectable so it can be
        tested with ``httpx.MockTransport``."""
        return cls(
            httpx_robots_fetcher(client=client, user_agent=user_agent, timeout=timeout),
            fail_closed_on_error=fail_closed_on_error,
        )


def httpx_robots_fetcher(
    *,
    client: "object | None" = None,
    user_agent: str = "ai-company-os-discovery/1.0",
    timeout: float = 10.0,
) -> RobotsFetcher:
    """Return a fetcher that GETs ``{host_root}/robots.txt``.

    Returns the body on 200, ``None`` on 404 (no robots.txt => allowed), and
    raises on other failures so :class:`RobotsPolicy` can fail closed.
    """
    import httpx

    http = client or httpx.Client(timeout=timeout)

    def fetch(host_root: str) -> str | None:
        response = http.get(f"{host_root}/robots.txt", headers={"User-Agent": user_agent})
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.text

    return fetch
