"""The independent store registry (stores.toml)."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from ..config import STORES_PATH

TIERS = frozenset({"first_pass", "explore", "backup", "parked"})
TRUST_LEVELS = frozenset({"unvetted", "checked", "purchased_ok", "avoid"})
PLATFORMS = frozenset(
    {"shopify_json", "shopify_html", "woocommerce", "wix", "ecwid", "crystalcommerce", "challenge", "unknown"}
)
# Only these platforms have an adapter; the rest are recorded until P5.
POLLED_PLATFORMS = frozenset({"shopify_json"})
# Newest-page discovery cadence per tier, in minutes. Parked stores aren't polled.
TIER_DISCOVERY_MINUTES = {"first_pass": 15, "explore": 60, "backup": 60}
_STORE_ID = re.compile(r"^[a-z0-9_]+$")
_DOMAIN = re.compile(r"^[a-z0-9.-]+\.[a-z]{2,}$")


@dataclass(frozen=True)
class Store:
    store_id: str
    name: str
    domain: str
    tier: str
    platform: str = "shopify_json"
    trust: str = "unvetted"
    notes: str = ""
    discovery_every_minutes: int | None = None
    has_newsletter: bool = False

    @property
    def base_url(self) -> str:
        return f"https://{self.domain}"

    @property
    def is_polled(self) -> bool:
        return self.platform in POLLED_PLATFORMS and self.tier != "parked" and self.trust != "avoid"

    @property
    def not_polled_reason(self) -> str | None:
        if self.trust == "avoid":
            return "trust is avoid"
        if self.tier == "parked":
            return "parked"
        if self.platform not in POLLED_PLATFORMS:
            return f"no adapter for {self.platform}"
        return None

    @property
    def discovery_minutes(self) -> int:
        return self.discovery_every_minutes or TIER_DISCOVERY_MINUTES.get(self.tier, 60)


def _store(raw: dict) -> Store:
    store = Store(
        store_id=raw["store_id"],
        name=raw["name"],
        domain=raw["domain"].lower(),
        tier=raw["tier"],
        platform=raw.get("platform", "shopify_json"),
        trust=raw.get("trust", "unvetted"),
        notes=raw.get("notes", ""),
        discovery_every_minutes=raw.get("discovery_every_minutes"),
        has_newsletter=bool(raw.get("newsletter", False)),
    )
    if not _STORE_ID.match(store.store_id):
        raise ValueError(f"store_id must be lowercase snake case: {store.store_id!r}")
    if not _DOMAIN.match(store.domain):
        raise ValueError(f"{store.store_id}: domain must be a bare host name: {store.domain!r}")
    if store.tier not in TIERS:
        raise ValueError(f"{store.store_id}: unknown tier {store.tier!r}")
    if store.trust not in TRUST_LEVELS:
        raise ValueError(f"{store.store_id}: unknown trust {store.trust!r}")
    if store.platform not in PLATFORMS:
        raise ValueError(f"{store.store_id}: unknown platform {store.platform!r}")
    minutes = store.discovery_every_minutes
    if minutes is not None and (not isinstance(minutes, int) or minutes < 5):
        raise ValueError(f"{store.store_id}: discovery_every_minutes must be a whole number of at least 5")
    return store


def load(path: Path = STORES_PATH) -> list[Store]:
    document = tomllib.loads(path.read_text())
    stores = [_store(raw) for raw in document.get("store", [])]
    seen_ids: set[str] = set()
    seen_domains: set[str] = set()
    for store in stores:
        if store.store_id in seen_ids:
            raise ValueError(f"duplicate store_id {store.store_id!r}")
        if store.domain in seen_domains:
            raise ValueError(f"duplicate domain {store.domain!r}")
        seen_ids.add(store.store_id)
        seen_domains.add(store.domain)
    return stores
