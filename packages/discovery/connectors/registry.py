"""Source registry — load config/sources.yaml and build enabled connectors.

Keeps connector construction in one place so workers/scripts just ask for "the
enabled sources" rather than wiring each one. Unknown source ids are skipped
with their config still returned, so adding a source to the YAML before its
connector class exists is harmless.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import httpx

from packages.discovery.connectors.base import Connector, ConnectorConfig
from packages.discovery.connectors.github import GitHubConnector
from packages.discovery.connectors.hackernews import HackerNewsConnector
from packages.discovery.connectors.rate_limiter import RateLimiter
from packages.discovery.connectors.reddit import RedditConnector

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - pyyaml is a declared dependency
    yaml = None  # type: ignore


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "sources.yaml"

# Maps a source id to a factory. Add new connectors here as they are built.
ConnectorFactory = Callable[[ConnectorConfig, "httpx.Client | None"], Connector]


def _build_hackernews(config: ConnectorConfig, client: httpx.Client | None) -> Connector:
    return HackerNewsConnector(
        config, client=client, rate_limiter=RateLimiter(config.rate_limit.requests_per_minute)
    )


def _build_github(config: ConnectorConfig, client: httpx.Client | None) -> Connector:
    return GitHubConnector(
        config, client=client, rate_limiter=RateLimiter(config.rate_limit.requests_per_minute)
    )


def _build_reddit(config: ConnectorConfig, client: httpx.Client | None) -> Connector:
    return RedditConnector(
        config, client=client, rate_limiter=RateLimiter(config.rate_limit.requests_per_minute)
    )


CONNECTOR_FACTORIES: dict[str, ConnectorFactory] = {
    "hackernews": _build_hackernews,
    "github": _build_github,
    "reddit": _build_reddit,
}


def _merge_defaults(defaults: dict[str, object], source: dict[str, object]) -> dict[str, object]:
    merged: dict[str, object] = {**defaults, **source}
    # Shallow-merge the rate_limit sub-map so a source can override just rpm.
    default_rate = dict(defaults.get("rate_limit", {}) or {})  # type: ignore[arg-type]
    source_rate = dict(source.get("rate_limit", {}) or {})  # type: ignore[arg-type]
    if default_rate or source_rate:
        merged["rate_limit"] = {**default_rate, **source_rate}
    return merged


def load_source_configs(config_path: Path | None = None) -> list[ConnectorConfig]:
    if yaml is None:  # pragma: no cover - guarded import
        raise RuntimeError("pyyaml is required to load sources config")
    raw = yaml.safe_load(Path(config_path or DEFAULT_CONFIG_PATH).read_text()) or {}
    defaults = dict(raw.get("defaults", {}) or {})
    return [
        ConnectorConfig.from_dict(_merge_defaults(defaults, dict(source)))
        for source in raw.get("sources", []) or []
    ]


def build_connectors(
    config_path: Path | None = None,
    *,
    client: httpx.Client | None = None,
    include_disabled: bool = False,
) -> dict[str, Connector]:
    """Instantiate connectors for every enabled, known source."""
    connectors: dict[str, Connector] = {}
    for config in load_source_configs(config_path):
        if not config.enabled and not include_disabled:
            continue
        factory = CONNECTOR_FACTORIES.get(config.id)
        if factory is None:
            continue
        connectors[config.id] = factory(config, client)
    return connectors
