"""Action layer for the outreach dashboard: turn ledger rows + overrides +
touches into per-channel button specs, and apply operator actions.

Data sources, by cost:
- **Ledger** (``client-status.json``) — already filtered to deployed A_gold and
  materialized, so it is the fast row source (no 28k-record scan per page load).
- **OutreachStore** (SQLite) — operator contact overrides and the touch log.

Effective contact = override-or-scanned, computed here at render time; the
scanned ledger value is never mutated, so a re-scan can't clobber an edit.

Nothing in this module sends. ``record_touch`` writes a *record that the
operator already sent by hand*, and advances the ledger status.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from packages.agency import outreach_messages as msg
from packages.agency.outreach import context_for
from packages.agency.outreach_lane import (
    OutreachClientRow,
    OutreachLaneStatus,
    auto_bump_on_touch,
    default_outreach_lane_root,
    set_row_status,
)
from packages.agency.outreach_store import ALLOWED_CHANNELS, OutreachStore

# channel -> the override/ledger field that enables it.
CHANNEL_CONTACT_FIELD = {
    "email": "contact_email",
    "sms": "phone",
    "call": "phone",
    "facebook_dm": "contact_facebook",
    "instagram_dm": "contact_instagram",
}


@dataclass(frozen=True)
class ChannelButton:
    channel: str  # one of ALLOWED_CHANNELS
    label: str
    contact_field: str  # the field to edit when this button is disabled
    contact_value: str  # effective value (override-or-scanned)
    enabled: bool
    url: str  # deep-link / scheme; empty when disabled
    copy: str  # text to paste as a fallback
    sent_count: int = 0
    last_sent_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "channel": self.channel,
            "label": self.label,
            "contact_field": self.contact_field,
            "contact_value": self.contact_value,
            "enabled": self.enabled,
            "url": self.url,
            "copy": self.copy,
            "sent_count": self.sent_count,
            "last_sent_at": self.last_sent_at,
        }


@dataclass(frozen=True)
class ActionRow:
    place_id: str
    business_name: str
    city: str
    genre_id: str
    status: str
    next_action: str
    mockup_url: str
    buttons: list[ChannelButton] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "place_id": self.place_id,
            "business_name": self.business_name,
            "city": self.city,
            "genre_id": self.genre_id,
            "status": self.status,
            "next_action": self.next_action,
            "mockup_url": self.mockup_url,
            "buttons": [b.to_dict() for b in self.buttons],
        }


@dataclass(frozen=True)
class OutreachPanelView:
    rows: list[ActionRow] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "rows": [r.to_dict() for r in self.rows],
            "statuses": self.statuses,
        }


def _load_ledger_rows(lane_root: Path) -> list[OutreachClientRow]:
    path = lane_root / "client-status.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    return [OutreachClientRow.from_dict(r) for r in payload.get("rows", []) if r.get("place_id")]


def _effective(row: OutreachClientRow, overrides: dict[str, str], field_name: str) -> str:
    scanned = {
        "contact_email": row.contact_email,
        "phone": row.phone,
        "contact_instagram": row.contact_instagram,
        "contact_facebook": row.contact_facebook,
        "contact_booking_url": row.contact_booking_url,
    }
    value = overrides.get(field_name) or scanned.get(field_name, "")
    return value.strip()


def _context_for_row(row: OutreachClientRow):
    """Build message context from a ledger row without re-reading the raw record.

    ``context_for`` resolves city from ``city_id``; the ledger only keeps the
    city *label*, so we patch it back on afterwards.
    """
    pseudo_record = {
        "display_name": row.business_name,
        "genre_id": row.genre_id,
        "user_ratings_total": row.review_count,
        "mockup_url": row.mockup_url,
    }
    ctx = context_for(pseudo_record, {})
    if row.city:
        ctx = type(ctx)(**{**ctx.__dict__, "city": row.city, "neighborhood": row.city})
    return ctx


def _buttons_for_row(
    row: OutreachClientRow,
    overrides: dict[str, str],
    touch_summary: dict[str, dict[str, object]],
) -> list[ChannelButton]:
    ctx = _context_for_row(row)
    messages = msg.build_messages_from_context(ctx)
    email = _effective(row, overrides, "contact_email")
    phone = _effective(row, overrides, "phone")
    facebook = _effective(row, overrides, "contact_facebook")
    instagram = _effective(row, overrides, "contact_instagram")

    specs = [
        (
            "email",
            "Email",
            email,
            msg.gmail_compose_url(
                to=email, subject=messages.email_subject, body=messages.email_body
            )
            if email
            else "",
            messages.email_body,
        ),
        (
            "sms",
            "SMS",
            phone,
            msg.sms_url(phone, messages.sms_body) if phone else "",
            messages.sms_body,
        ),
        (
            "call",
            "Call",
            phone,
            msg.tel_url(phone) if phone else "",
            messages.call_script,
        ),
        (
            "facebook_dm",
            "FB DM",
            facebook,
            msg.facebook_url(facebook) if facebook else "",
            messages.dm_body,
        ),
        (
            "instagram_dm",
            "IG DM",
            instagram,
            msg.instagram_url(instagram) if instagram else "",
            messages.dm_body,
        ),
    ]

    buttons: list[ChannelButton] = []
    for channel, label, value, url, copy in specs:
        stats = touch_summary.get(channel, {})
        buttons.append(
            ChannelButton(
                channel=channel,
                label=label,
                contact_field=CHANNEL_CONTACT_FIELD[channel],
                contact_value=value,
                enabled=bool(value),
                url=url,
                copy=copy,
                sent_count=int(stats.get("count", 0) or 0),
                last_sent_at=str(stats.get("last_sent_at", "")),
            )
        )
    return buttons


def build_outreach_panel(
    *,
    store: OutreachStore | None = None,
    lane_root: Path | None = None,
) -> OutreachPanelView:
    root = lane_root or default_outreach_lane_root()
    store = store or OutreachStore()
    overrides = store.all_overrides()
    touches = store.touch_summary()
    rows = _load_ledger_rows(root)
    action_rows = [
        ActionRow(
            place_id=row.place_id,
            business_name=row.business_name,
            city=row.city,
            genre_id=row.genre_id,
            status=row.status.value,
            next_action=row.next_action,
            mockup_url=row.mockup_url,
            buttons=_buttons_for_row(
                row, overrides.get(row.place_id, {}), touches.get(row.place_id, {})
            ),
        )
        for row in rows
    ]
    return OutreachPanelView(
        rows=action_rows,
        statuses=[s.value for s in OutreachLaneStatus],
    )


# --------------------------------------------------------------- operations
def record_touch(
    place_id: str,
    channel: str,
    *,
    store: OutreachStore | None = None,
    lane_root: Path | None = None,
) -> dict[str, object]:
    """Log a human-confirmed send: append to the store, advance the ledger."""
    if channel not in ALLOWED_CHANNELS:
        raise ValueError(f"unsupported channel {channel!r}")
    store = store or OutreachStore()
    touch = store.append_touch(place_id, channel, via="dashboard")
    row = auto_bump_on_touch(place_id, channel, lane_root=lane_root)
    return {"touch": touch, "status": row.status.value, "place_id": place_id}


def set_contact(
    place_id: str,
    field_name: str,
    value: str,
    *,
    store: OutreachStore | None = None,
) -> dict[str, object]:
    store = store or OutreachStore()
    override = store.set_override(place_id, field_name, value)
    return {"override": override, "place_id": place_id}


def set_status(
    place_id: str,
    status: str,
    *,
    lane_root: Path | None = None,
) -> dict[str, object]:
    row = set_row_status(place_id, OutreachLaneStatus(status), lane_root=lane_root)
    return {"status": row.status.value, "place_id": place_id}


__all__ = [
    "ChannelButton",
    "ActionRow",
    "OutreachPanelView",
    "build_outreach_panel",
    "record_touch",
    "set_contact",
    "set_status",
]
