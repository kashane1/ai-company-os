"""Contact form + lead routing (Agency layer — `contact_forms` service).

The scaffolded site ships a contact form wired to the ``contact`` Netlify function
(``packages/web/scaffold/astro-landing/netlify/functions/contact.mjs``), which
persists each lead to a Blob and emails the owner. This module records the
per-client routing config and guards the legs we can't deliver yet.

- **form → email** is live (the function + the client's ``LEAD_NOTIFY_EMAIL``).
- **form → SMS** is GATED — it hits the same A2P 10DLC / TCPA gate as review-SMS,
  so ``sms_enabled`` must stay False until that lands.
- **CRM routing** is delivered by the ``crm_setup`` service; ``crm`` names the
  target once one exists.

See ``docs/agency/runbooks/contact-forms-setup.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.db.json_store import JsonStore

_RECORD_ID = "contact_forms"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ContactFormsError(ValueError):
    """Invalid routing config, or a leg that isn't deliverable yet."""


@dataclass(frozen=True)
class ContactFormsSetup:
    product_id: str
    notify_email: str  # where leads go (the client's inbox)
    sms_enabled: bool = False  # form→SMS is gated (A2P 10DLC / TCPA) — keep False
    crm: str = ""  # CRM routing target (via crm_setup); "" = none
    completed_at: str = ""

    def validate(self) -> None:
        if not self.product_id.strip():
            raise ContactFormsError("contact_forms: product_id is required")
        if not _EMAIL_RE.match(self.notify_email.strip()):
            raise ContactFormsError(
                f"contact_forms: notify_email must be an email: {self.notify_email!r}"
            )
        if self.sms_enabled:
            raise ContactFormsError(
                "contact_forms: form→SMS is gated pending A2P 10DLC / TCPA compliance "
                "(same gate as review-SMS). Keep sms_enabled=False until that lands."
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "notify_email": self.notify_email,
            "sms_enabled": self.sms_enabled,
            "crm": self.crm,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ContactFormsSetup":
        return cls(
            product_id=str(payload["product_id"]),
            notify_email=str(payload["notify_email"]),
            sms_enabled=bool(payload.get("sms_enabled", False)),
            crm=str(payload.get("crm", "")),
            completed_at=str(payload.get("completed_at", "")),
        )


def _store(product_id: str, root: Path | None = None) -> JsonStore:
    base = root or (load_runtime_paths().state_root / "clients" / product_id / "services")
    return JsonStore(base)


def save_contact_forms_setup(record: ContactFormsSetup, *, root: Path | None = None) -> Path:
    record.validate()
    return _store(record.product_id, root).save(_RECORD_ID, record.to_dict())


def load_contact_forms_setup(
    product_id: str, *, root: Path | None = None
) -> ContactFormsSetup | None:
    store = _store(product_id, root)
    if not store.path_for(_RECORD_ID).exists():
        return None
    return ContactFormsSetup.from_dict(store.load(_RECORD_ID))
