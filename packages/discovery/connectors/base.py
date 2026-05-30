"""Connector contract + the raw signal shape every source produces.

Every source (Hacker News, GitHub, ...) implements ``Connector`` so the
discovery layer is uniform and the compliance controls are centralized. A
connector turns a query into ``RawSignal``s with mandatory provenance (the
source URL is never stripped).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol

from packages.schemas.opportunity import EvidenceKind


class CompliancePolicyError(RuntimeError):
    """Raised when a connector is asked to do something policy forbids
    (disabled source, unapproved bulk crawl, robots-disallowed path)."""


@dataclass(frozen=True)
class RawSignal:
    """A pain/observation in the source's own words, with provenance."""

    text: str
    url: str  # canonical URL — provenance is mandatory, never strip it
    kind: EvidenceKind = EvidenceKind.OTHER
    quote: str = ""  # short verbatim quote; store the link, not the article
    captured_at: str = ""
    meta: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        return payload


@dataclass(frozen=True)
class RateLimitConfig:
    requests_per_minute: int = 20
    backoff_on: tuple[int, ...] = (429, 503)


@dataclass(frozen=True)
class ConnectorConfig:
    """Runtime config for one source, loaded from config/sources.yaml."""

    id: str
    enabled: bool = True
    kind: str = "api"
    endpoint: str = ""
    auth_env: str = ""  # name of the env var holding the token, if any
    respect_robots: bool = True
    user_agent: str = "ai-company-os-discovery/1.0 (+contact@example.com)"
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    tos: str = ""  # advisory note; if collection is forbidden, the connector refuses
    notes: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ConnectorConfig":
        rate_raw = dict(payload.get("rate_limit", {}) or {})  # type: ignore[arg-type]
        return cls(
            id=str(payload["id"]),
            enabled=bool(payload.get("enabled", True)),
            kind=str(payload.get("kind", "api")),
            endpoint=str(payload.get("endpoint", "")),
            auth_env=str(payload.get("auth_env", "") or payload.get("auth", "")),
            respect_robots=bool(payload.get("respect_robots", True)),
            user_agent=str(payload.get("user_agent", ConnectorConfig.user_agent)),
            rate_limit=RateLimitConfig(
                requests_per_minute=int(rate_raw.get("requests_per_minute", 20)),
                backoff_on=tuple(
                    int(code) for code in rate_raw.get("backoff_on", [429, 503]) or []
                ),
            ),
            tos=str(payload.get("tos", "")),
            notes=str(payload.get("notes", "")),
        )


@dataclass(frozen=True)
class FetchOptions:
    query: str
    limit: int = 25
    # ``bulk`` asks for a crawl beyond normal per-domain limits. Connectors
    # refuse it UNLESS ``authorized`` is also set — and ``authorized`` is only
    # set by a caller that has passed the bulk_crawl approval gate (C1). This is
    # how the gate is enforced at the point of action, not just by convention.
    bulk: bool = False
    authorized: bool = False


class Connector(Protocol):
    """A source that turns a query into raw signals with provenance."""

    id: str
    config: ConnectorConfig

    def fetch(self, options: FetchOptions) -> list[RawSignal]:
        """Return raw signals for a query. Implementations MUST: refuse if
        disabled; check robots.txt for HTML fetches when respect_robots is on;
        apply the rate limiter and back off on configured status codes; never
        touch login/paywall/anti-bot content; attach the source URL to every
        signal."""
        ...

    def healthcheck(self) -> tuple[bool, str]:
        """Cheap reachability/auth check: ``(ok, detail)``."""
        ...
