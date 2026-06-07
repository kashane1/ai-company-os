from dataclasses import asdict, dataclass, field
from enum import Enum


class ProductPlatform(str, Enum):
    IOS = "ios"
    # Section F — web products (landing pages, marketing/SaaS sites). Built by
    # the WEB lane, shipped by the WEBDEPLOY lane. Source lives in
    # products/<product-id>-web/.
    WEB = "web"


# Agency layer (Phase 2) — discriminates an owned product from a client
# engagement. Strictly additive; ``PRODUCT`` is the default so every existing
# record keeps its current meaning.
class ProductType(str, Enum):
    PRODUCT = "product"  # owned product (iOS apps, our own web products)
    CLIENT_SITE = "client-site"  # a client we operate but do not own


class ClientOwnership(str, Enum):
    CLIENT_OWNED = "client-owned"  # we operate, the client owns the asset
    AGENCY_HELD = "agency-held"  # we hold the asset on the client's behalf


class BillingStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    # Additive (G1). A dispute/refund is a work-stopping, money-out state.
    DISPUTED = "disputed"
    REFUNDED = "refunded"

    @classmethod
    def coerce(cls, value: object) -> "BillingStatus":
        """Decode a persisted status, falling back to a WORK-STOPPING state.

        [MIG-P0] The strict registry loader routes every ``client`` block through
        ``ClientConfig.from_dict``. A value an older reader can't parse (e.g. a
        future status) must NOT abort the whole registry load, and must NOT fall
        back to an *entitled* state (``active``/``trial``) — that would let a
        disputed/refunded client keep receiving paid work. Fall back to
        ``CANCELLED`` (stops work) instead, loudly-safe rather than silently-wrong.
        """
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value))
        except ValueError:
            return cls.CANCELLED


class ProductStatus(str, Enum):
    DISCOVERY = "discovery"
    READY_FOR_IMPLEMENTATION = "ready_for_implementation"
    IN_DEVELOPMENT = "in_development"


# Phase 5.3 — product lifecycle phase. Strictly additive; existing
# ProductStatus remains untouched for backwards compatibility.
class ProductPhase(str, Enum):
    DISCOVERY = "discovery"
    MVP_BUILD = "mvp-build"
    APP_STORE_SUBMISSION = "app-store-submission"
    LIVE = "live"
    MAINTENANCE = "maintenance"


class ProductArtifactType(str, Enum):
    FOUNDER_BRIEF = "founder_brief"
    PRODUCT_BRIEF = "product_brief"
    MVP_SPEC = "mvp_spec"
    BACKLOG = "backlog"
    IOS_ARCHITECTURE = "ios_architecture"
    # Section F — web product architecture (framework, pages, deploy target).
    WEB_ARCHITECTURE = "web_architecture"
    APPSTORE_POSITIONING = "appstore_positioning"
    INSIGHT_RULES = "insight_rules"
    INSIGHT_ACCEPTANCE_CASES = "insight_acceptance_cases"


class ProductArtifactStatus(str, Enum):
    IMPORTED = "imported"
    READY = "ready"


@dataclass(frozen=True)
class ClientConfig:
    """Client-engagement metadata attached to a ``client-site`` product.

    ``bundle`` is a foreign key into the agency service catalog
    (``packages/agency/catalog.yaml``); ``from_prospect`` backlinks to the
    originating prospect record in ``state/prospects/``.
    """

    ownership: ClientOwnership = ClientOwnership.CLIENT_OWNED
    bundle: str = ""
    services: list[str] = field(default_factory=list)
    from_prospect: str = ""
    billing_status: BillingStatus = BillingStatus.TRIAL
    # Acceptance audit (G3) — stamped once on the first paid invoice. Immutable
    # audit facts, independent of entitlement (a later dispute changes
    # ``billing_status`` but never these). Defaulted so legacy records load.
    accepted_by: str = ""
    accepted_at: str = ""
    # The client's own Netlify site id (their site, their account). Stamped at
    # launch; lets the lead-health drain target their `inbound-leads` Blobs store.
    netlify_site_id: str = ""
    # The client's Plausible site id (domain) — lets the monthly-report executor
    # pull real traffic/lead numbers without an operator passing --site-id.
    plausible_site_id: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "ownership": self.ownership.value,
            "bundle": self.bundle,
            "services": list(self.services),
            "from_prospect": self.from_prospect,
            "billing_status": self.billing_status.value,
            "accepted_by": self.accepted_by,
            "accepted_at": self.accepted_at,
            "netlify_site_id": self.netlify_site_id,
            "plausible_site_id": self.plausible_site_id,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ClientConfig":
        return cls(
            ownership=ClientOwnership(
                str(payload.get("ownership", ClientOwnership.CLIENT_OWNED.value))
            ),
            bundle=str(payload.get("bundle", "")),
            services=[str(x) for x in list(payload.get("services", []))],
            from_prospect=str(payload.get("from_prospect", "")),
            # [MIG-P0] guarded decode — an unknown status loads as CANCELLED
            # (work-stopping), never aborts the registry load.
            billing_status=BillingStatus.coerce(
                payload.get("billing_status", BillingStatus.TRIAL.value)
            ),
            accepted_by=str(payload.get("accepted_by", "")),
            accepted_at=str(payload.get("accepted_at", "")),
            netlify_site_id=str(payload.get("netlify_site_id", "")),
            plausible_site_id=str(payload.get("plausible_site_id", "")),
        )


@dataclass(frozen=True)
class ProductConfig:
    id: str
    name: str
    slug: str
    platform: ProductPlatform
    repo_id: str
    source_path: str
    docs_root: str
    phase: ProductPhase = ProductPhase.DISCOVERY
    # Agency layer (Phase 2) — additive. ``type`` defaults to ``product`` so
    # existing iOS/web records are unchanged; ``client`` is populated only for
    # ``client-site`` records.
    type: ProductType = ProductType.PRODUCT
    client: ClientConfig | None = None


@dataclass(frozen=True)
class ProductArtifactRecord:
    artifact_type: ProductArtifactType
    path: str
    derived_from: ProductArtifactType | None = None
    source_origin: str | None = None
    status: ProductArtifactStatus = ProductArtifactStatus.READY

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_type": self.artifact_type.value,
            "path": self.path,
            "derived_from": self.derived_from.value if self.derived_from else None,
            "source_origin": self.source_origin,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ProductArtifactRecord":
        derived_from = payload.get("derived_from")
        return cls(
            artifact_type=ProductArtifactType(str(payload["artifact_type"])),
            path=str(payload["path"]),
            derived_from=ProductArtifactType(str(derived_from)) if derived_from else None,
            source_origin=str(payload["source_origin"]) if payload.get("source_origin") else None,
            status=ProductArtifactStatus(
                str(payload.get("status", ProductArtifactStatus.READY.value))
            ),
        )


@dataclass(frozen=True)
class ProductRecord:
    id: str
    name: str
    slug: str
    platform: ProductPlatform
    repo_id: str
    source_path: str
    docs_root: str
    status: ProductStatus
    artifacts: list[ProductArtifactRecord] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["platform"] = self.platform.value
        payload["status"] = self.status.value
        payload["artifacts"] = [artifact.to_dict() for artifact in self.artifacts]
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ProductRecord":
        return cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            slug=str(payload["slug"]),
            platform=ProductPlatform(str(payload["platform"])),
            repo_id=str(payload["repo_id"]),
            source_path=str(payload["source_path"]),
            docs_root=str(payload["docs_root"]),
            status=ProductStatus(str(payload["status"])),
            artifacts=[
                ProductArtifactRecord.from_dict(item)
                for item in list(payload.get("artifacts", []))
            ],
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
        )
