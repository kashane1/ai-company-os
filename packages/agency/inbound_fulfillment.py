"""Inbound lead fulfilment (Agency layer, G2b — minimal).

Operator-triggered: take one captured :class:`WebsiteReviewRequest` and

* **audit** the submitted website with an SSRF-guarded fetch (skipped when the
  prospect has no site), and
* **build a local preview** when the operator supplies the inputs the public
  form doesn't capture (``city`` + ``genre``).

It is idempotent (re-run is a no-op unless ``force``), stamps the record's
``status``/``processed_at``, performs **no deploy and no email**, and never hits
the network in unit tests (the fetch + preview steps are injectable seams).

Deliberately DEFERRED for this slice (tracked, not built):
* the per-contact/global daily cap (todo 074),
* honeypot/``spam`` status handling,
* contact-format validation ([+G2-STATUS]/[A8]).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from packages.agency.inbound import (
    InboundReviewRepository,
    ReviewStatus,
    WebsiteReviewRequest,
    _record_id,
)
from packages.agency.intake import ClientIntake
from packages.config.settings import load_runtime_paths
from packages.policies.url_guard import (
    FetchedPage,
    Opener,
    Resolver,
    UnsafeUrlError,
    fetch_public_url,
)
from packages.web.scaffold import render_landing_html, unfilled_tokens

# Values in the "current website" field that mean "no site to audit".
_NO_WEBSITE = frozenset({"", "none", "n/a", "na", "no", "-", "—"})

# Statuses past which a re-run is a no-op (unless --force). GUARDED is *not*
# terminal: a record audited without city/genre can be advanced to PREVIEWED.
_TERMINAL = frozenset({ReviewStatus.PREVIEWED, ReviewStatus.SKIPPED, ReviewStatus.SPAM})

# Injectable clock seam ([X-CLOCK]) so the stamped timestamp is testable.
Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InboundFulfillmentError(ValueError):
    """Raised for non-recoverable fulfilment input errors."""


@dataclass(frozen=True)
class AuditResult:
    attempted: bool
    ok: bool = False
    status_code: int = 0
    final_url: str = ""
    bytes_read: int = 0
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "attempted": self.attempted,
            "ok": self.ok,
            "status_code": self.status_code,
            "final_url": self.final_url,
            "bytes_read": self.bytes_read,
            "error": self.error,
        }


@dataclass(frozen=True)
class FulfillmentResult:
    submission_id: str
    status: ReviewStatus
    audit: AuditResult
    preview_path: str = ""
    preview_error: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "submission_id": self.submission_id,
            "status": self.status.value,
            "audit": self.audit.to_dict(),
            "preview_path": self.preview_path,
            "preview_error": self.preview_error,
            "detail": self.detail,
        }


def _normalize_website(raw: str) -> str:
    """Return a fetchable URL, or "" if there's no site. One https:// attempt."""
    value = (raw or "").strip()
    if value.lower() in _NO_WEBSITE:
        return ""
    if "://" not in value:
        value = "https://" + value
    return value


# (request, *, city, genre, out_dir) -> path to the built index.html.
PreviewBuilder = Callable[..., Path]


def build_local_preview(
    request: WebsiteReviewRequest, *, city: str, genre: str, out_dir: Path
) -> Path:
    """Render a local preview for the requester via the existing scaffold path.

    The public form doesn't capture city/genre, so the operator supplies them;
    ``ClientIntake.validate`` requires a non-empty city. No deploy, no network.
    """
    intake = ClientIntake(
        business_name=(request.business or request.name).strip() or "Local Business",
        service_category=(genre or "local services").strip() or "local services",
        city=city.strip(),
    )
    intake.validate()  # raises ValueError if city is empty
    html = render_landing_html(intake.to_site_context())
    leftover = unfilled_tokens(html)
    if leftover:  # render guard — never write a page with visible {{TOKENS}}
        raise InboundFulfillmentError(f"unfilled template tokens: {sorted(leftover)}")
    dist = out_dir / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    index = dist / "index.html"
    index.write_text(html, encoding="utf-8")
    return index


def _audit_website(
    website: str,
    *,
    fetcher: Callable[..., FetchedPage],
    resolver: Resolver | None,
    opener: Opener | None,
) -> AuditResult:
    url = _normalize_website(website)
    if not url:
        return AuditResult(attempted=False)  # no site to audit
    kwargs: dict[str, object] = {}
    if resolver is not None:
        kwargs["resolver"] = resolver
    if opener is not None:
        kwargs["opener"] = opener
    try:
        page: FetchedPage = fetcher(url, **kwargs)
    except (UnsafeUrlError, OSError) as exc:  # SSRF refusal or network failure
        return AuditResult(attempted=True, ok=False, error=str(exc))
    return AuditResult(
        attempted=True,
        ok=200 <= page.status < 400,
        status_code=page.status,
        final_url=page.final_url,
        bytes_read=page.bytes_read,
    )


def process_inbound_review(
    submission_id: str,
    *,
    city: str = "",
    genre: str = "",
    force: bool = False,
    inbound_root: Path | None = None,
    repo: InboundReviewRepository | None = None,
    out_root: Path | None = None,
    fetcher: Callable[..., FetchedPage] = fetch_public_url,
    resolver: Resolver | None = None,
    opener: Opener | None = None,
    preview_builder: PreviewBuilder = build_local_preview,
    clock: Clock = _utc_now,
) -> FulfillmentResult:
    """Audit + optionally preview one inbound lead. Idempotent; no deploy/email."""
    repo = repo or InboundReviewRepository(inbound_root)
    if not repo.exists(submission_id):
        raise FileNotFoundError(f"no inbound review request for id {submission_id!r}")
    request = repo.get(submission_id)

    if request.status in _TERMINAL and not force:
        return FulfillmentResult(
            submission_id=request.submission_id,
            status=request.status,
            audit=AuditResult(attempted=False),
            preview_path="",
            detail=f"already processed ({request.status.value}); use --force to re-run",
        )

    audit = _audit_website(request.website, fetcher=fetcher, resolver=resolver, opener=opener)

    preview_path = ""
    preview_error = ""
    if city.strip() and genre.strip():
        base = out_root or (
            load_runtime_paths().state_root / "prospects" / "inbound-previews"
        )
        out_dir = base / _record_id(request.submission_id)
        try:
            built = preview_builder(request, city=city, genre=genre, out_dir=out_dir)
            preview_path = str(built)
        except (ValueError, OSError) as exc:  # missing city, render-guard, IO
            preview_error = str(exc)

    final_status = ReviewStatus.PREVIEWED if preview_path else ReviewStatus.GUARDED
    updated = dataclasses.replace(
        request, status=final_status, processed_at=clock().isoformat()
    )
    repo.save(updated)

    return FulfillmentResult(
        submission_id=request.submission_id,
        status=final_status,
        audit=audit,
        preview_path=preview_path,
        preview_error=preview_error,
        detail="forced re-run" if force else "",
    )
