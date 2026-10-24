"""MSRP references and price classes for store listings (plan phase P3).

`msrp.toml` is the source of truth. Evidence rows (basis 1-3) and watches
priced by a Best Buy first-party listing are synced into `msrp_references`;
form defaults and per-pack estimates are computed here and never stored.
Only an evidence-backed MSRP can make a listing alert-eligible.
"""

from __future__ import annotations

import datetime as dt
import re
import sqlite3
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .. import watchlist
from ..config import MSRP_PATH
from . import match

# Strongest first. Ranks 1-3 are evidence; 4-5 are estimates.
BASIS_RANK = {
    "official_listing": 1,
    "big_box_first_party": 2,
    "distributor_or_press": 3,
    "form_default": 4,
    "per_pack_estimate": 5,
}
EVIDENCE_BASES = frozenset(basis for basis, rank in BASIS_RANK.items() if rank <= 3)
BASIS_LABELS = {
    "official_listing": "official",
    "big_box_first_party": "big-box",
    "distributor_or_press": "press",
    "form_default": "est. form",
    "per_pack_estimate": "est. packs",
}

# Price class boundaries, as multiples of MSRP (and of tcgcsv market for marked_up).
BELOW_MSRP_UNDER = 0.95
AT_MSRP_MAX = 1.10
NEAR_MSRP_MAX = 1.25
MARKET_MAX = 1.05
ALERT_CLASSES = frozenset({"below_msrp", "at_msrp"})
CLASS_ORDER = ("below_msrp", "at_msrp", "near_msrp", "market", "marked_up", "no_msrp")

# The forms the P3 "done when" covers.
TARGET_FORMS = ("etb", "booster_bundle", "booster_box")
TARGET_SINCE = "2025-01-01"

_WATCH_BASIS_PREFIX = "best buy first-party"
# "(36 packs)", "with 6 booster packs": a pack count the catalog name states.
_NAME_PACKS = re.compile(r"\b(\d{1,3})\s+(?:booster\s+)?packs?\b", re.IGNORECASE)


@dataclass(frozen=True)
class Reference:
    product_id: int
    msrp_cents: int
    basis: str
    evidence_url: str | None
    checked_on: str
    source: str
    note: str = ""


@dataclass(frozen=True)
class FormDefault:
    form: str
    msrp_cents: int
    since: str
    until: str | None = None
    exclusive: str | None = None  # ref_products.exclusive_retailer; None means "not exclusive"
    note: str = ""

    def applies(self, form: str, exclusive: str | None, release_on: str | None) -> bool:
        if form != self.form or (exclusive or None) != self.exclusive or not release_on:
            return False
        return release_on >= self.since and (self.until is None or release_on < self.until)


@dataclass(frozen=True)
class PackPrice:
    msrp_cents: int
    since: str
    until: str | None = None

    def applies(self, release_on: str | None) -> bool:
        return bool(release_on) and release_on >= self.since and (self.until is None or release_on < self.until)


@dataclass(frozen=True)
class Msrp:
    msrp_cents: int
    basis: str
    evidence_url: str | None = None

    @property
    def is_estimated(self) -> bool:
        return self.basis not in EVIDENCE_BASES

    @property
    def label(self) -> str:
        return BASIS_LABELS[self.basis]


@dataclass(frozen=True)
class Product:
    """What resolution needs to know about a catalog product."""

    product_id: int
    name: str
    product_type: str
    exclusive_retailer: str | None
    release_on: str | None


@dataclass(frozen=True)
class PriceClass:
    name: str
    msrp: Msrp | None
    ratio: float | None  # price / MSRP

    @property
    def is_alert_eligible(self) -> bool:
        return self.name in ALERT_CLASSES and self.msrp is not None and not self.msrp.is_estimated


@dataclass
class Config:
    references: list[Reference]
    form_defaults: list[FormDefault]
    pack_prices: list[PackPrice]
    # Target-set products deliberately left without evidence, with the reason.
    unpriced: dict[int, str]


def _cents(value: float | int) -> int:
    return round(float(value) * 100)


def load(path: Path = MSRP_PATH) -> Config:
    document = tomllib.loads(path.read_text()) if path.exists() else {}
    references = []
    seen: set[tuple[int, str]] = set()
    for raw in document.get("reference", []):
        basis = raw["basis"]
        if basis not in EVIDENCE_BASES:
            raise ValueError(f"msrp.toml: reference {raw.get('product_id')} has basis {basis!r}; use 1-3 evidence bases")
        if not raw.get("evidence_url"):
            raise ValueError(f"msrp.toml: reference {raw['product_id']} needs an evidence_url")
        key = (int(raw["product_id"]), basis)
        if key in seen:
            raise ValueError(f"msrp.toml: duplicate reference {key}")
        seen.add(key)
        references.append(
            Reference(
                product_id=int(raw["product_id"]),
                msrp_cents=_cents(raw["msrp"]),
                basis=basis,
                evidence_url=raw["evidence_url"],
                checked_on=dt.date.fromisoformat(str(raw["checked_on"])).isoformat(),
                source="msrp.toml",
                note=raw.get("note", ""),
            )
        )
    form_defaults = [
        FormDefault(
            form=raw["form"],
            msrp_cents=_cents(raw["msrp"]),
            since=dt.date.fromisoformat(str(raw["since"])).isoformat(),
            until=dt.date.fromisoformat(str(raw["until"])).isoformat() if raw.get("until") else None,
            exclusive=raw.get("exclusive") or None,
            note=raw.get("note", ""),
        )
        for raw in document.get("form_default", [])
    ]
    pack_prices = [
        PackPrice(
            msrp_cents=_cents(raw["msrp"]),
            since=dt.date.fromisoformat(str(raw["since"])).isoformat(),
            until=dt.date.fromisoformat(str(raw["until"])).isoformat() if raw.get("until") else None,
        )
        for raw in document.get("pack_price", [])
    ]
    unpriced = {int(raw["product_id"]): raw["reason"] for raw in document.get("unpriced", [])}
    return Config(references, form_defaults, pack_prices, unpriced)


def watch_references(catalog: match.Catalog, items: list[watchlist.WatchItem]) -> list[Reference]:
    """Watches whose `alert_at` is a Best Buy first-party price, as basis-2 references."""
    references = []
    for item in items:
        identity = getattr(item, "identity", None)  # legacy watches carry no identity
        if identity is None or item.alert_at is None or identity.language != "en" or identity.game != "pokemon":
            continue
        if not identity.ceiling_basis.lower().startswith(_WATCH_BASIS_PREFIX):
            continue
        result = match.match_listing(catalog, item.name)
        if result.status != "exact" or result.catalog_product_id is None:
            continue
        evidence = next((url for url in identity.evidence_urls if "bestbuy.com" in url), None)
        if evidence is None:
            continue
        references.append(
            Reference(
                product_id=result.catalog_product_id,
                msrp_cents=_cents(item.alert_at),
                basis="big_box_first_party",
                evidence_url=evidence,
                checked_on=identity.evidence_date,
                source=f"watchlist:{identity.watch_id}",
            )
        )
    return references


def sync(connection: sqlite3.Connection, config: Config, catalog: match.Catalog | None = None,
         items: list[watchlist.WatchItem] | None = None) -> int:
    """Replace `msrp_references` with msrp.toml rows plus watchlist-derived rows."""
    catalog = catalog or match.Catalog.from_db(connection)
    items = watchlist.load() if items is None else items
    rows: dict[tuple[int, str], Reference] = {}
    for reference in watch_references(catalog, items):
        rows.setdefault((reference.product_id, reference.basis), reference)
    # An explicit msrp.toml row wins over a watch for the same basis.
    for reference in config.references:
        rows[(reference.product_id, reference.basis)] = reference
    connection.execute("DELETE FROM msrp_references")
    connection.executemany(
        """
        INSERT INTO msrp_references (product_id, basis, msrp_cents, evidence_url, checked_on, source, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (r.product_id, r.basis, r.msrp_cents, r.evidence_url, r.checked_on, r.source, r.note or None)
            for r in rows.values()
        ],
    )
    connection.commit()
    return len(rows)


class Resolver:
    """Resolves each catalog product's MSRP: evidence, then form default, then per-pack estimate."""

    def __init__(self, evidence: dict[int, list[Reference]], config: Config):
        self.evidence = evidence
        self.config = config

    @classmethod
    def from_db(cls, connection: sqlite3.Connection, config: Config | None = None) -> "Resolver":
        evidence: dict[int, list[Reference]] = {}
        for row in connection.execute("SELECT * FROM msrp_references"):
            evidence.setdefault(row["product_id"], []).append(
                Reference(row["product_id"], row["msrp_cents"], row["basis"], row["evidence_url"],
                          row["checked_on"], row["source"], row["note"] or "")
            )
        return cls(evidence, config or load())

    def resolve(self, product: Product) -> Msrp | None:
        references = self.evidence.get(product.product_id)
        if references:
            best = min(references, key=lambda r: (BASIS_RANK[r.basis], _negated(r.checked_on)))
            return Msrp(best.msrp_cents, best.basis, best.evidence_url)
        defaults = [
            rule for rule in self.config.form_defaults
            if rule.applies(product.product_type, product.exclusive_retailer, product.release_on)
        ]
        if defaults:
            rule = max(defaults, key=lambda r: r.since)
            return Msrp(rule.msrp_cents, "form_default")
        packs = name_pack_count(product.name)
        prices = [rule for rule in self.config.pack_prices if rule.applies(product.release_on)]
        if packs and prices:
            rule = max(prices, key=lambda r: r.since)
            return Msrp(packs * rule.msrp_cents, "per_pack_estimate")
        return None


def _negated(day: str) -> tuple[int, ...]:
    """Sort key that puts the newest date first under min()."""
    return tuple(-int(part) for part in day.split("-"))


def name_pack_count(name: str) -> int | None:
    found = _NAME_PACKS.search(name)
    if not found:
        return None
    count = int(found.group(1))
    return count if 1 < count <= 500 else None


def classify(price_cents: int, msrp: Msrp | None, market_cents: int | None) -> PriceClass:
    if msrp is None or msrp.msrp_cents <= 0:
        return PriceClass("no_msrp", None, None)
    ratio = price_cents / msrp.msrp_cents
    if ratio < BELOW_MSRP_UNDER:
        name = "below_msrp"
    elif ratio <= AT_MSRP_MAX:
        name = "at_msrp"
    elif ratio <= NEAR_MSRP_MAX:
        name = "near_msrp"
    elif market_cents is None or price_cents <= market_cents * MARKET_MAX:
        name = "market"
    else:
        name = "marked_up"
    return PriceClass(name, msrp, ratio)


def products(connection: sqlite3.Connection, *, forms=TARGET_FORMS, since: str = TARGET_SINCE) -> list[Product]:
    placeholders = ",".join("?" for _ in forms)
    rows = connection.execute(
        f"""
        SELECT p.product_id, p.name, p.product_type, p.exclusive_retailer,
               COALESCE(p.release_on, g.published_on) AS release_on
        FROM ref_products p JOIN ref_groups g USING (group_id)
        WHERE p.product_type IN ({placeholders}) AND COALESCE(p.release_on, g.published_on) >= ?
        ORDER BY release_on, p.product_type, p.name
        """,
        (*forms, since),
    ).fetchall()
    return [Product(r["product_id"], r["name"], r["product_type"], r["exclusive_retailer"], r["release_on"]) for r in rows]


def product(connection: sqlite3.Connection, product_id: int) -> Product | None:
    row = connection.execute(
        """
        SELECT p.product_id, p.name, p.product_type, p.exclusive_retailer,
               COALESCE(p.release_on, g.published_on) AS release_on
        FROM ref_products p JOIN ref_groups g USING (group_id) WHERE p.product_id = ?
        """,
        (product_id,),
    ).fetchone()
    return Product(*row) if row else None


def _money(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def render_coverage(connection: sqlite3.Connection, resolver: Resolver, *, forms=TARGET_FORMS,
                    since: str = TARGET_SINCE, missing_only: bool = False) -> str:
    target = products(connection, forms=forms, since=since)
    counts: dict[str, int] = {}
    missing: list[tuple[Product, Msrp | None]] = []
    for item in target:
        msrp = resolver.resolve(item)
        basis = msrp.basis if msrp else "none"
        counts[basis] = counts.get(basis, 0) + 1
        if msrp is None or msrp.is_estimated:
            missing.append((item, msrp))
    lines = []
    if not missing_only:
        lines.append(f"MSRP coverage: {len(target)} products ({', '.join(forms)}) released since {since}")
        for basis in [*BASIS_RANK, "none"]:
            if counts.get(basis):
                lines.append(f"  {counts[basis]:>4}  {basis}")
        lines.append("")
    lines.append(f"Without evidence (basis 1-3): {len(missing)}")
    for item, msrp in missing:
        estimate = f"{_money(msrp.msrp_cents)} {msrp.label}" if msrp else "no estimate"
        reason = resolver.config.unpriced.get(item.product_id)
        suffix = f"  [{reason}]" if reason else ""
        lines.append(
            f"  {item.product_id:>7}  {item.release_on or '?':<10}  {item.product_type:<15} {item.name[:70]:<70} {estimate}{suffix}"
        )
    return "\n".join(lines) + "\n"
