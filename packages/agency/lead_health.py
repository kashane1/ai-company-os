"""Client-site lead-pipeline monitoring (Agency layer — the `hosting` SLA).

The $49/mo hosting plan promises "contact-form monitoring". Each client site's
contact form (``netlify/functions/contact.mjs``) persists every submission to
that client's own Netlify Blobs ``inbound-leads`` store FIRST, then best-effort
emails the owner via Resend and stamps ``notified_at`` only on success.

The dangerous failure is silent: a misconfigured/expired ``RESEND_API_KEY`` (or
``LEAD_NOTIFY_EMAIL``) means leads keep landing in the store with
``notified_at = null`` while the owner hears nothing. This module turns the
drained lead records into a health verdict the monthly ``check_lead_health``
retainer action acts on — so an undelivered lead is caught in days, not when the
client churns.

Pure + clock-free: the caller passes ``as_of`` (no ambient ``date.today()``), so
the assessment is deterministic and testable. Draining the Blobs store into
``state/`` is a separate Node step (mirrors ``scripts/web/pull-inbound.mjs``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path


class LeadHealthStatus(str, Enum):
    OK = "ok"          # leads flowing and delivered (or a quiet but healthy month)
    WARN = "warn"      # nothing alarming, but worth a glance (e.g. a long dry spell)
    ALERT = "alert"    # action needed now (undelivered leads / store unreachable)


def _to_date(value: object) -> date | None:
    """Parse an ISO timestamp/date to a ``date``; ``None`` if unparseable.

    Lead records are written by the cross-language JS function, so be defensive:
    a garbage ``received_at`` must not crash the monthly health check.
    """
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _delivered(lead: dict[str, object]) -> bool:
    """A lead is delivered once the owner notification was stamped.

    Works for both stores: client contact-form leads carry ``notified_at`` (set by
    contact.mjs on send); the agency's own website-review funnel records may instead
    carry ``status == "notified"`` after processing — either counts as delivered.
    """
    return bool(lead.get("notified_at")) or str(lead.get("status", "")) == "notified"


@dataclass(frozen=True)
class LeadHealth:
    product_id: str
    as_of: str
    window_days: int
    total_leads: int
    leads_in_window: int
    undelivered_in_window: int
    days_since_last_lead: int | None
    status: LeadHealthStatus
    alerts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "as_of": self.as_of,
            "window_days": self.window_days,
            "total_leads": self.total_leads,
            "leads_in_window": self.leads_in_window,
            "undelivered_in_window": self.undelivered_in_window,
            "days_since_last_lead": self.days_since_last_lead,
            "status": self.status.value,
            "alerts": list(self.alerts),
        }


def assess_lead_health(
    leads: list[dict[str, object]],
    *,
    product_id: str,
    as_of: date,
    window_days: int = 30,
    store_reachable: bool = True,
    dry_spell_days: int = 45,
    lead_capture_expected: bool = True,
) -> LeadHealth:
    """Turn drained lead records into a health verdict for the month.

    * ``store_reachable=False`` (the drain couldn't read the Blobs store) → ALERT:
      we can't prove the form is capturing anything.
    * any lead in-window with ``notified_at`` unset → ALERT: leads captured but the
      owner was never emailed (the silent Resend-misconfig failure).
    * no lead for longer than ``dry_spell_days`` → WARN: maybe normal, maybe the
      form is broken upstream — worth an operator glance.

    ``lead_capture_expected`` is the form-aware switch: many small-business sites
    don't depend on a lead form, so a quiet month is normal, not a problem. When
    ``False``, the absence-of-leads signals (dry spell / none-ever) are suppressed —
    only the always-valid failures (undelivered, unreachable) remain. The undelivered
    ALERT always fires regardless, because a captured-but-undelivered lead is a real
    failure for any business that *did* receive one.
    """
    if not store_reachable:
        return LeadHealth(
            product_id=product_id,
            as_of=as_of.isoformat(),
            window_days=window_days,
            total_leads=0,
            leads_in_window=0,
            undelivered_in_window=0,
            days_since_last_lead=None,
            status=LeadHealthStatus.ALERT,
            alerts=["lead store unreachable — cannot confirm the contact form is capturing leads"],
        )

    cutoff = date.fromordinal(as_of.toordinal() - window_days)
    dates = [d for d in (_to_date(lead.get("received_at")) for lead in leads) if d is not None]
    in_window = [
        lead
        for lead in leads
        if (d := _to_date(lead.get("received_at"))) is not None and d >= cutoff
    ]
    undelivered = [lead for lead in in_window if not _delivered(lead)]
    last = max(dates) if dates else None
    days_since = (as_of.toordinal() - last.toordinal()) if last else None

    alerts: list[str] = []
    status = LeadHealthStatus.OK
    if undelivered:
        status = LeadHealthStatus.ALERT
        alerts.append(
            f"{len(undelivered)} lead(s) captured but the owner was never emailed — "
            "check RESEND_API_KEY / LEAD_NOTIFY_EMAIL / LEAD_FROM_EMAIL for this site"
        )
    if lead_capture_expected and days_since is not None and days_since > dry_spell_days:
        if status is LeadHealthStatus.OK:
            status = LeadHealthStatus.WARN
        alerts.append(
            f"no leads in {days_since} days — confirm the contact form still submits"
        )
    if lead_capture_expected and last is None:
        if status is LeadHealthStatus.OK:
            status = LeadHealthStatus.WARN
        alerts.append("no leads on record yet — verify the form end-to-end with a test submission")

    return LeadHealth(
        product_id=product_id,
        as_of=as_of.isoformat(),
        window_days=window_days,
        total_leads=len(leads),
        leads_in_window=len(in_window),
        undelivered_in_window=len(undelivered),
        days_since_last_lead=days_since,
        status=status,
        alerts=alerts,
    )


def load_leads_from_dir(leads_dir: Path) -> list[dict[str, object]]:
    """Load drained lead JSON files (one record per file) from a directory."""
    if not leads_dir.is_dir():
        return []
    leads: list[dict[str, object]] = []
    for path in sorted(leads_dir.glob("*.json")):
        try:
            leads.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return leads
