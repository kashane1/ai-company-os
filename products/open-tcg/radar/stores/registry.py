"""The independent store registry (stores.toml)."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from ..config import STORES_PATH

TIERS = frozenset({"first_pass", "explore", "backup", "parked"})
TRUST_LEVELS = frozenset({"unvetted", "checked", "purchased_ok", "avoid"})
PLATFORMS = frozenset({"shopify_json"})
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

    @property
    def base_url(self) -> str:
        return f"https://{self.domain}"

    @property
    def is_polled(self) -> bool:
        return self.tier != "parked" and self.trust != "avoid"


def _store(raw: dict) -> Store:
    store = Store(
        store_id=raw["store_id"],
        name=raw["name"],
        domain=raw["domain"].lower(),
        tier=raw["tier"],
        platform=raw.get("platform", "shopify_json"),
        trust=raw.get("trust", "unvetted"),
        notes=raw.get("notes", ""),
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
        raise ValueError(f"{store.store_id}: unsupported platform {store.platform!r}")
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
