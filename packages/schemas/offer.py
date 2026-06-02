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

from dataclasses import dataclass, field
from enum import Enum


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
        )


@dataclass(frozen=True)
class Bundle:
    """A productized package (A/B/C) — a named set of services sold together."""

    bundle_id: str
    name: str
    service_ids: list[str]
    description: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "bundle_id": self.bundle_id,
            "name": self.name,
            "service_ids": list(self.service_ids),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Bundle":
        return cls(
            bundle_id=str(payload["bundle_id"]),
            name=str(payload["name"]),
            service_ids=[str(x) for x in list(payload.get("service_ids", []))],
            description=str(payload.get("description", "")),
        )


@dataclass(frozen=True)
class BundleQuote:
    """Resolved pricing for a bundle — the setup + monthly a client signs."""

    bundle_id: str
    services: list[Service]
    setup_total: float
    monthly_total: float


@dataclass(frozen=True)
class ServiceCatalog:
    """The whole catalog: services keyed by id + bundles keyed by id."""

    services: dict[str, Service]
    bundles: dict[str, Bundle]

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

    def quote_bundle(self, bundle_id: str) -> BundleQuote:
        if bundle_id not in self.bundles:
            raise CatalogError(f"unknown bundle {bundle_id!r}")
        bundle = self.bundles[bundle_id]
        services = [self.services[sid] for sid in bundle.service_ids]
        return BundleQuote(
            bundle_id=bundle_id,
            services=services,
            setup_total=round(sum(s.setup_fee for s in services), 2),
            monthly_total=round(sum(s.monthly_fee for s in services), 2),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "services": [s.to_dict() for s in self.services.values()],
            "bundles": [b.to_dict() for b in self.bundles.values()],
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
        return cls(services=services, bundles=bundles)
