"""Inbound website-review requests (Agency layer).

A :class:`WebsiteReviewRequest` is the typed capture of a public funnel
submission ("Request your free website review" on the Better Business Web site).
Peer of :class:`packages.agency.intake.ClientIntake`; persisted via ``JsonStore``
into ``state/prospects/inbound/`` so the platform — not just a human inbox — can
pick it up and run the preview/audit fulfilment (plan §7/§10, todos 068/065).

The ``website`` field is the prospect's *current* site (or "none"); it is
untrusted input and MUST be passed through
``packages.policies.url_guard.assert_safe_public_url`` before any automated
fetch.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.db.json_store import JsonStore


def default_inbound_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).state_root / "prospects" / "inbound"


@dataclass(frozen=True)
class WebsiteReviewRequest:
    submission_id: str
    name: str
    contact: str  # email or phone
    business: str = ""
    website: str = ""  # current site or "none" — UNTRUSTED (guard before fetch)
    received_at: str = ""
    source: str = "netlify-form"

    def validate(self) -> None:
        if not self.submission_id.strip():
            raise ValueError("review request: submission_id is required")
        if not self.name.strip():
            raise ValueError("review request: name is required")
        if not self.contact.strip():
            raise ValueError("review request: contact is required")

    def to_dict(self) -> dict[str, object]:
        return {
            "submission_id": self.submission_id,
            "name": self.name,
            "contact": self.contact,
            "business": self.business,
            "website": self.website,
            "received_at": self.received_at,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "WebsiteReviewRequest":
        return cls(
            submission_id=str(payload["submission_id"]),
            name=str(payload["name"]),
            contact=str(payload["contact"]),
            business=str(payload.get("business", "")),
            website=str(payload.get("website", "")),
            received_at=str(payload.get("received_at", "")),
            source=str(payload.get("source", "netlify-form")),
        )


def _record_id(submission_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in submission_id.strip())
    return safe or hashlib.sha1(submission_id.encode("utf-8")).hexdigest()[:16]


class InboundReviewRepository:
    """JSON persistence for inbound review requests (``state/prospects/inbound/``)."""

    def __init__(self, root: Path | None = None) -> None:
        self._store = JsonStore(root or default_inbound_root())

    @property
    def root(self) -> Path:
        return self._store.root

    def save(self, request: WebsiteReviewRequest) -> WebsiteReviewRequest:
        request.validate()
        self._store.save(_record_id(request.submission_id), request.to_dict())
        return request

    def exists(self, submission_id: str) -> bool:
        return self._store.path_for(_record_id(submission_id)).exists()

    def get(self, submission_id: str) -> WebsiteReviewRequest:
        return WebsiteReviewRequest.from_dict(self._store.load(_record_id(submission_id)))

    def list(self) -> list[WebsiteReviewRequest]:
        return [
            WebsiteReviewRequest.from_dict(self._store.load(path.stem))
            for path in sorted(self._store.root.glob("*.json"))
        ]
