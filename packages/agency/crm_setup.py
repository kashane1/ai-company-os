"""CRM setup (Agency layer — `crm_setup` service).

Records the per-client CRM configuration the operator builds from the runbook
(``docs/agency/runbooks/crm-setup.md``). We **standardize on HubSpot Free** for
low-friction small-business delivery (pipeline, lead stages, contact properties,
form routing, email templates, handoff doc). **GoHighLevel** is the supported
paid upgrade for clients who need SMS-heavy / advanced automation — where the
platform (or client) owns the A2P 10DLC registration, not us.

This module is a record + guard, not an integration: the operator builds the CRM
in the platform UI per the runbook and stamps the result here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.db.json_store import JsonStore

_RECORD_ID = "crm"

# The CRMs we deliver. HubSpot is the default; GoHighLevel the paid upgrade.
SUPPORTED_PLATFORMS = ("hubspot", "gohighlevel", "zoho", "pipedrive")
DEFAULT_PLATFORM = "hubspot"
# A clean, small-business default pipeline (operator can override per client).
DEFAULT_STAGES = ("New lead", "Contacted", "Quoted", "Won", "Lost")


class CrmSetupError(ValueError):
    """Unsupported platform or invalid CRM config."""


@dataclass(frozen=True)
class CrmSetup:
    product_id: str
    platform: str = DEFAULT_PLATFORM
    pipeline_name: str = ""
    stages: list[str] = field(default_factory=lambda: list(DEFAULT_STAGES))
    handoff_doc: str = ""  # path/URL of the client handoff doc, once written
    completed_at: str = ""

    def validate(self) -> None:
        if not self.product_id.strip():
            raise CrmSetupError("crm_setup: product_id is required")
        if self.platform.strip().lower() not in SUPPORTED_PLATFORMS:
            raise CrmSetupError(
                f"crm_setup: unsupported platform {self.platform!r}; "
                f"supported: {', '.join(SUPPORTED_PLATFORMS)}"
            )
        if not self.stages:
            raise CrmSetupError("crm_setup: at least one pipeline stage is required")

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "platform": self.platform,
            "pipeline_name": self.pipeline_name,
            "stages": list(self.stages),
            "handoff_doc": self.handoff_doc,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "CrmSetup":
        stages = [str(s) for s in list(payload.get("stages", []))] or list(DEFAULT_STAGES)
        return cls(
            product_id=str(payload["product_id"]),
            platform=str(payload.get("platform", DEFAULT_PLATFORM)),
            pipeline_name=str(payload.get("pipeline_name", "")),
            stages=stages,
            handoff_doc=str(payload.get("handoff_doc", "")),
            completed_at=str(payload.get("completed_at", "")),
        )


def _store(product_id: str, root: Path | None = None) -> JsonStore:
    base = root or (load_runtime_paths().state_root / "clients" / product_id / "services")
    return JsonStore(base)


def save_crm_setup(record: CrmSetup, *, root: Path | None = None) -> Path:
    record.validate()
    return _store(record.product_id, root).save(_RECORD_ID, record.to_dict())


def load_crm_setup(product_id: str, *, root: Path | None = None) -> CrmSetup | None:
    store = _store(product_id, root)
    if not store.path_for(_RECORD_ID).exists():
        return None
    return CrmSetup.from_dict(store.load(_RECORD_ID))
