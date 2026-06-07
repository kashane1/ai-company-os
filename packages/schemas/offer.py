"""Agency service-catalog schema (Agency layer, Phase 1).

The catalog is the single typed source of truth for what the agency sells: the
individual services and the productized A/B/C bundles. Downstream consumers — the
launch checklist, the monthly-report generator, the client ``OFFER.md`` render,
and any billing logic — all read this schema so signed terms can never silently
drift from the catalog.

Frozen dataclasses + explicit ``to_dict`` / ``from_dict`` conversion match the
rest of the repo's persisted-state conventions (see
``packages/schemas/prospect.py`` and ``packages/schemas/product.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum


def _half_up(value: Decimal) -> int:
    """Round a Decimal to the nearest integer, half-up (not banker's).

    Money is computed in integer cents so Python and the JS checkout function
    agree to the cent. Python's built-in ``round()`` is round-half-to-even and
    disagrees with JS ``Math.round`` on exact half-cents — never use it for money.
    """
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def to_cents(dollars: float) -> int:
    """Convert a whole/decimal dollar amount to integer cents, half-up."""
    return _half_up(Decimal(str(dollars)) * 100)


class ServiceTier(str, Enum):
    """Where a service sits on the value ladder (see the agency brainstorm)."""

    TIER_1 = "tier_1"  # easy add-ons (GBP, hosting, email, contact forms)
    TIER_2 = "tier_2"  # high value (booking, local SEO, reviews, reporting)
    TIER_3 = "tier_3"  # recurring-revenue goldmine (ads, landing pages, CRM, follow-up)
    TIER_4 = "tier_4"  # fractional-CTO bespoke engagements (quoted per project)


class BillType(str, Enum):
    ONE_TIME = "one_time"
    RECURRING = "recurring"


class CatalogError(ValueError):
    """Raised when the catalog fails referential / value integrity checks."""


@dataclass(frozen=True)
class Service:
    """A single sellable service.

    ``setup_fee`` and ``monthly_fee`` are USD. A ``recurring`` service must carry
    a positive ``monthly_fee``; a ``one_time`` service must carry a positive
    ``setup_fee``. Both must be non-negative.
    """

    service_id: str
    name: str
    tier: ServiceTier
    bill_type: BillType
    setup_fee: float = 0.0
    monthly_fee: float = 0.0
    includes: list[str] = field(default_factory=list)
    edit_limit: str = ""
    ownership: str = "client-owned"
    cancellation: str = "30-day notice, no penalty"
    support_sla: str = "best-effort, 2 business days"
    # Whether the service can be bought instantly via the self-serve builder /
    # buy-now flow. Defaults True; set False for services that need an operator
    # step (account access, spend setup) before they can be executed.
    self_serve: bool = True
    # Variant modelling for "slot" offers (e.g. booking). Services that share a
    # non-empty ``exclusive_group`` are mutually exclusive — a cart may contain at
    # most one. A service with ``requires_group`` set may only be added when the
    # cart already contains a service from that group (a modifier needs its base).
    exclusive_group: str = ""
    requires_group: str = ""

    def validate(self) -> None:
        if self.setup_fee < 0 or self.monthly_fee < 0:
            raise CatalogError(f"service {self.service_id!r}: fees must be non-negative")
        if self.bill_type is BillType.RECURRING and self.monthly_fee <= 0:
            raise CatalogError(
                f"service {self.service_id!r}: recurring service requires a positive monthly_fee"
            )
        if self.bill_type is BillType.ONE_TIME and self.setup_fee <= 0:
            raise CatalogError(
                f"service {self.service_id!r}: one_time service requires a positive setup_fee"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "service_id": self.service_id,
            "name": self.name,
            "tier": self.tier.value,
            "bill_type": self.bill_type.value,
            "setup_fee": self.setup_fee,
            "monthly_fee": self.monthly_fee,
            "includes": list(self.includes),
            "edit_limit": self.edit_limit,
            "ownership": self.ownership,
            "cancellation": self.cancellation,
            "support_sla": self.support_sla,
            "self_serve": self.self_serve,
            "exclusive_group": self.exclusive_group,
            "requires_group": self.requires_group,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Service":
        return cls(
            service_id=str(payload["service_id"]),
            name=str(payload["name"]),
            tier=ServiceTier(str(payload["tier"])),
            bill_type=BillType(str(payload["bill_type"])),
            setup_fee=float(payload.get("setup_fee", 0.0) or 0.0),
            monthly_fee=float(payload.get("monthly_fee", 0.0) or 0.0),
            includes=[str(x) for x in list(payload.get("includes", []))],
            edit_limit=str(payload.get("edit_limit", "")),
            ownership=str(payload.get("ownership", "client-owned")),
            cancellation=str(payload.get("cancellation", "30-day notice, no penalty")),
            support_sla=str(payload.get("support_sla", "best-effort, 2 business days")),
            self_serve=bool(payload.get("self_serve", True)),
            exclusive_group=str(payload.get("exclusive_group", "")),
            requires_group=str(payload.get("requires_group", "")),
        )


@dataclass(frozen=True)
class Bundle:
    """A productized package (A/B/C) — a named set of services sold together.

    ``setup_promo`` (USD, ``0`` = none) is a curated promotional setup price that
    overrides the count-based tier discount when the buyer selects exactly this
    bundle's service set. It is deliberately a little cheaper than the tier
    discount so a named package is always the best deal for that set.
    """

    bundle_id: str
    name: str
    service_ids: list[str]
    description: str = ""
    setup_promo: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "bundle_id": self.bundle_id,
            "name": self.name,
            "service_ids": list(self.service_ids),
            "description": self.description,
            "setup_promo": self.setup_promo,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Bundle":
        return cls(
            bundle_id=str(payload["bundle_id"]),
            name=str(payload["name"]),
            service_ids=[str(x) for x in list(payload.get("service_ids", []))],
            description=str(payload.get("description", "")),
            setup_promo=float(payload.get("setup_promo", 0.0) or 0.0),
        )


@dataclass(frozen=True)
class DiscountTier:
    """One rung of the setup-only bundle discount, keyed by service count.

    ``max_services`` is ``None`` for the open-ended top rung. The discount
    applies to the gross setup total only — never to monthly fees.
    """

    min_services: int
    max_services: int | None
    pct: int

    def matches(self, count: int) -> bool:
        if count < self.min_services:
            return False
        return self.max_services is None or count <= self.max_services

    def to_dict(self) -> dict[str, object]:
        return {
            "min_services": self.min_services,
            "max_services": self.max_services,
            "pct": self.pct,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "DiscountTier":
        raw_max = payload.get("max_services", None)
        return cls(
            min_services=int(payload["min_services"]),
            max_services=None if raw_max is None else int(raw_max),
            pct=int(payload["pct"]),
        )


@dataclass(frozen=True)
class BundleQuote:
    """Resolved pricing for a set of services — what a client signs / is charged.

    All money is integer cents. ``setup_after_cents`` is the price actually
    charged (after the tier discount or the bundle promo override).
    ``savings_cents`` is always ``setup_gross - setup_after`` by subtraction —
    never recompute it from a percentage. There is intentionally no
    ``monthly_after`` field: monthly is never discounted.
    """

    services: list[Service]
    setup_gross_cents: int
    setup_after_cents: int
    monthly_cents: int
    pricing_mode: str  # "tier" | "promo"
    tier_pct: int = 0  # rung applied (0 for a promo override or a 1–2 svc cart)
    bundle_id: str | None = None

    @property
    def savings_cents(self) -> int:
        return self.setup_gross_cents - self.setup_after_cents

    # Dollar convenience views for the markdown renderers (display only).
    @property
    def setup_gross(self) -> float:
        return self.setup_gross_cents / 100

    @property
    def setup_after_discount(self) -> float:
        return self.setup_after_cents / 100

    @property
    def monthly_total(self) -> float:
        return self.monthly_cents / 100

    @property
    def savings(self) -> float:
        return self.savings_cents / 100


@dataclass(frozen=True)
class ServiceCatalog:
    """The whole catalog: services + bundles + the setup-only discount tiers."""

    services: dict[str, Service]
    bundles: dict[str, Bundle]
    discount_tiers: tuple[DiscountTier, ...] = ()

    def validate(self) -> None:
        for service in self.services.values():
            service.validate()
        for bundle in self.bundles.values():
            if not bundle.service_ids:
                raise CatalogError(f"bundle {bundle.bundle_id!r}: has no services")
            for sid in bundle.service_ids:
                if sid not in self.services:
                    raise CatalogError(
                        f"bundle {bundle.bundle_id!r}: references unknown service {sid!r}"
                    )
        for tier in self.discount_tiers:
            if not (0 <= tier.pct <= 100):
                raise CatalogError(f"discount tier pct out of range: {tier.pct}")
            if tier.max_services is not None and tier.max_services < tier.min_services:
                raise CatalogError(
                    f"discount tier max < min: {tier.min_services}..{tier.max_services}"
                )
        # "Packages are always the best value": a bundle's promo must not exceed
        # what the tier discount would charge for the same service set, or the
        # "best value" claim drifts. Guard it at load time.
        for bundle in self.bundles.values():
            if not bundle.setup_promo:
                continue
            tier_quote = self.quote_services(bundle.service_ids)
            promo_cents = to_cents(bundle.setup_promo)
            if promo_cents > tier_quote.setup_after_cents:
                raise CatalogError(
                    f"bundle {bundle.bundle_id!r}: setup_promo "
                    f"({promo_cents}c) exceeds tier-discounted setup "
                    f"({tier_quote.setup_after_cents}c) — packages must be the best value"
                )

    def tier_pct_for(self, count: int) -> int:
        """The setup discount % for a cart of ``count`` services (0 if none match)."""
        for tier in self.discount_tiers:
            if tier.matches(count):
                return tier.pct
        return 0

    def quote_services(
        self, service_ids: list[str], *, setup_promo_cents: int | None = None
    ) -> BundleQuote:
        """Price an arbitrary set of services — the single pricing path.

        With ``setup_promo_cents`` (a preset's curated override) the setup is
        pinned to that promo; otherwise the count-based tier discount applies.
        Monthly is the plain sum, never discounted.
        """
        services: list[Service] = []
        for sid in service_ids:
            if sid not in self.services:
                raise CatalogError(f"unknown service {sid!r}")
            services.append(self.services[sid])

        gross = sum(to_cents(s.setup_fee) for s in services)
        monthly = sum(to_cents(s.monthly_fee) for s in services)

        if setup_promo_cents is not None:
            after = int(setup_promo_cents)
            mode, tier_pct = "promo", 0
        else:
            tier_pct = self.tier_pct_for(len(services))
            discount = _half_up(Decimal(gross) * tier_pct / 100)
            after = gross - discount
            mode = "tier"

        return BundleQuote(
            services=services,
            setup_gross_cents=gross,
            setup_after_cents=after,
            monthly_cents=monthly,
            pricing_mode=mode,
            tier_pct=tier_pct,
        )

    def quote_bundle(self, bundle_id: str) -> BundleQuote:
        if bundle_id not in self.bundles:
            raise CatalogError(f"unknown bundle {bundle_id!r}")
        bundle = self.bundles[bundle_id]
        promo = to_cents(bundle.setup_promo) if bundle.setup_promo else None
        quote = self.quote_services(bundle.service_ids, setup_promo_cents=promo)
        return replace(quote, bundle_id=bundle_id)

    def validate_selection(self, service_ids: list[str]) -> list[str]:
        """Check ``exclusive_group`` (pick-one) + ``requires_group`` (dependency).

        Returns a list of human-readable error messages (empty = valid). The
        builder prevents invalid carts in the UI; the checkout function calls this
        server-side as the authoritative guard.
        """
        errors: list[str] = []
        services = [self.services[s] for s in service_ids if s in self.services]
        present_groups = {s.exclusive_group for s in services if s.exclusive_group}

        # At most one service per exclusive group.
        counts: dict[str, int] = {}
        for s in services:
            if s.exclusive_group:
                counts[s.exclusive_group] = counts.get(s.exclusive_group, 0) + 1
        for group, n in counts.items():
            if n > 1:
                errors.append(f"choose only one option for {group!r} (got {n})")

        # Every dependency satisfied.
        for s in services:
            if s.requires_group and s.requires_group not in present_groups:
                errors.append(
                    f"{s.name!r} requires a {s.requires_group!r} option in the cart"
                )
        return errors

    def to_dict(self) -> dict[str, object]:
        return {
            "services": [s.to_dict() for s in self.services.values()],
            "bundles": [b.to_dict() for b in self.bundles.values()],
            "discount_tiers": [t.to_dict() for t in self.discount_tiers],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ServiceCatalog":
        services = {
            str(item["service_id"]): Service.from_dict(item)
            for item in list(payload.get("services", []))
        }
        bundles = {
            str(item["bundle_id"]): Bundle.from_dict(item)
            for item in list(payload.get("bundles", []))
        }
        discount_tiers = tuple(
            DiscountTier.from_dict(item)
            for item in list(payload.get("discount_tiers", []))
        )
        return cls(services=services, bundles=bundles, discount_tiers=discount_tiers)
