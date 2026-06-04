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
from enum import Enum
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.db.json_store import JsonStore


def default_inbound_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).state_root / "prospects" / "inbound"


class ReviewStatus(str, Enum):
    """Lifecycle of an inbound review request as it moves through fulfilment."""

    NEW = "new"            # captured, not yet acted on
    NOTIFIED = "notified"  # operator emailed (stamped by the Netlify function)
    GUARDED = "guarded"    # website audited (SSRF-guarded), preview pending inputs
    PREVIEWED = "previewed"  # a preview was built
    SKIPPED = "skipped"    # intentionally not fulfilled
    SPAM = "spam"          # honeypot / flagged

    @classmethod
    def coerce(cls, value: object) -> "ReviewStatus":
        """Defensive decode — an unknown/garbage value loads as NEW, never raises.

        The writer is cross-language (the Netlify JS function), so legacy or
        unexpected strings must not break ``from_dict``.
        """
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value))
        except ValueError:
            return cls.NEW


@dataclass(frozen=True)
class WebsiteReviewRequest:
    submission_id: str
    name: str
    contact: str  # email or phone
    business: str = ""
    website: str = ""  # current site or "none" — UNTRUSTED (guard before fetch)
    received_at: str = ""
    source: str = "netlify-form"
    status: ReviewStatus = ReviewStatus.NEW
    processed_at: str = ""
    notified_at: str = ""  # set when the operator email was sent (un-notified list)

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
            "status": self.status.value,
            "processed_at": self.processed_at,
            "notified_at": self.notified_at,
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
            # Defaulted so legacy records (written before these fields existed)
            # load unchanged: missing status -> NEW, missing timestamps -> "".
            status=ReviewStatus.coerce(payload.get("status", ReviewStatus.NEW.value)),
            processed_at=str(payload.get("processed_at", "")),
            notified_at=str(payload.get("notified_at", "")),
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
        record_id = _record_id(request.submission_id)
        # Collision guard: _record_id sanitizes to alnum/-/_, so two distinct
        # submission_ids can map to the same filename. Refuse to silently
        # overwrite a *different* lead (data loss); same submission_id is an
        # idempotent update.
        path = self._store.path_for(record_id)
        if path.exists():
            existing = WebsiteReviewRequest.from_dict(self._store.load(record_id))
            if existing.submission_id != request.submission_id:
                raise ValueError(
                    f"record id {record_id!r} collision: "
                    f"{existing.submission_id!r} vs {request.submission_id!r}"
                )
        self._store.save(record_id, request.to_dict())
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
