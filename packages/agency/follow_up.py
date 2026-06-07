"""Automated follow-up (Agency layer — `follow_up_automation` service).

Email-first lead follow-up built in the client's CRM (default HubSpot): an
instant new-lead reply, a 2-day reminder, and owner task reminders. Recurring
($39/mo) — the operator reviews/tunes the sequences monthly.

**SMS rule (decision):** the auto-text leg is **email-first / deferred**. Sending
SMS via our own number re-imposes the A2P 10DLC / TCPA burden on us. So
``sms_enabled`` is allowed **only** on a compliant SMS-capable platform (e.g.
GoHighLevel) where the platform / client owns the A2P registration. On HubSpot
(the default) it stays email-only until the client upgrades. We never run our own
Twilio for client follow-up.

See ``docs/agency/runbooks/follow-up-automation.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.db.json_store import JsonStore

_RECORD_ID = "follow_up"

SUPPORTED_PLATFORMS = ("hubspot", "gohighlevel", "zoho", "pipedrive")
# Platforms where the auto-text leg is compliant because the PLATFORM owns the
# A2P 10DLC registration (not us). HubSpot Free is email-first only.
SMS_CAPABLE_PLATFORMS = ("gohighlevel",)
DEFAULT_PLATFORM = "hubspot"
DEFAULT_STEPS = (
    "Instant email reply on new lead",
    "Day 2 reminder email",
    "Owner task: follow up within 1 business day",
)


class FollowUpError(ValueError):
    """Unsupported platform, or an SMS config that isn't compliant here."""


@dataclass(frozen=True)
class FollowUpSetup:
    product_id: str
    platform: str = DEFAULT_PLATFORM
    email_enabled: bool = True
    sms_enabled: bool = False  # gated to SMS_CAPABLE_PLATFORMS (platform owns A2P)
    steps: list[str] = field(default_factory=lambda: list(DEFAULT_STEPS))
    completed_at: str = ""

    def validate(self) -> None:
        if not self.product_id.strip():
            raise FollowUpError("follow_up: product_id is required")
        if self.platform.strip().lower() not in SUPPORTED_PLATFORMS:
            raise FollowUpError(
                f"follow_up: unsupported platform {self.platform!r}; "
                f"supported: {', '.join(SUPPORTED_PLATFORMS)}"
            )
        if not self.email_enabled and not self.sms_enabled:
            raise FollowUpError("follow_up: at least one channel (email) must be enabled")
        if self.sms_enabled and self.platform.strip().lower() not in SMS_CAPABLE_PLATFORMS:
            raise FollowUpError(
                "follow_up: auto-text requires a compliant SMS-capable platform "
                f"({', '.join(SMS_CAPABLE_PLATFORMS)}) that owns the A2P 10DLC registration. "
                "On HubSpot it's email-first until the client upgrades; never run our own SMS."
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "platform": self.platform,
            "email_enabled": self.email_enabled,
            "sms_enabled": self.sms_enabled,
            "steps": list(self.steps),
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "FollowUpSetup":
        steps = [str(s) for s in list(payload.get("steps", []))] or list(DEFAULT_STEPS)
        return cls(
            product_id=str(payload["product_id"]),
            platform=str(payload.get("platform", DEFAULT_PLATFORM)),
            email_enabled=bool(payload.get("email_enabled", True)),
            sms_enabled=bool(payload.get("sms_enabled", False)),
            steps=steps,
            completed_at=str(payload.get("completed_at", "")),
        )


def _store(product_id: str, root: Path | None = None) -> JsonStore:
    base = root or (load_runtime_paths().state_root / "clients" / product_id / "services")
    return JsonStore(base)


def save_follow_up_setup(record: FollowUpSetup, *, root: Path | None = None) -> Path:
    record.validate()
    return _store(record.product_id, root).save(_RECORD_ID, record.to_dict())


def load_follow_up_setup(product_id: str, *, root: Path | None = None) -> FollowUpSetup | None:
    store = _store(product_id, root)
    if not store.path_for(_RECORD_ID).exists():
        return None
    return FollowUpSetup.from_dict(store.load(_RECORD_ID))
