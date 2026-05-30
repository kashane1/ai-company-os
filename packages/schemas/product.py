from dataclasses import asdict, dataclass, field
from enum import Enum


class ProductPlatform(str, Enum):
    IOS = "ios"
    # Section F — web products (landing pages, marketing/SaaS sites). Built by
    # the WEB lane, shipped by the WEBDEPLOY lane. Source lives in
    # products/<product-id>-web/.
    WEB = "web"


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
class ProductConfig:
    id: str
    name: str
    slug: str
    platform: ProductPlatform
    repo_id: str
    source_path: str
    docs_root: str
    phase: ProductPhase = ProductPhase.DISCOVERY


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
            status=ProductArtifactStatus(str(payload.get("status", ProductArtifactStatus.READY.value))),
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
