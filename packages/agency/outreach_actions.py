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
from datetime import UTC, datetime
from pathlib import Path

from packages.agency import outreach_messages as msg
from packages.agency import suppression
from packages.agency.outreach import context_for
from packages.agency.outreach_lane import (
    OutreachClientRow,
    OutreachLaneStatus,
    auto_bump_on_touch,
    default_outreach_lane_root,
    set_row_status,
)
from packages.agency.outreach_store import (
    ALLOWED_CHANNELS,
    DEFAULT_VARIANT,
    KNOWN_VARIANTS,
    OutreachStore,
)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _row_record(row: OutreachClientRow) -> dict[str, object]:
    """A record-like dict carrying just the identifiers suppression reads."""
    return {
        "place_id": row.place_id,
        "contact_email": row.contact_email,
        "phone": row.phone,
        "contact_instagram": row.contact_instagram,
        "contact_facebook": row.contact_facebook,
    }

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
class RowFacts:
    tags: list[str] = field(default_factory=list)
    contact_channels: list[str] = field(default_factory=list)
    sent_channels: list[str] = field(default_factory=list)
    total_sent_count: int = 0
    last_sent_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "tags": self.tags,
            "contact_channels": self.contact_channels,
            "sent_channels": self.sent_channels,
            "total_sent_count": self.total_sent_count,
            "last_sent_at": self.last_sent_at,
        }


@dataclass(frozen=True)
class FacetOption:
    key: str
    label: str
    count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {"key": self.key, "label": self.label, "count": self.count}


@dataclass(frozen=True)
class ActionRow:
    place_id: str
    business_name: str
    city: str
    genre_id: str
    status: str
    next_action: str
    mockup_url: str
    facts: RowFacts = field(default_factory=RowFacts)
    buttons: list[ChannelButton] = field(default_factory=list)
    suppressed: bool = False
    suppression_reason: str = ""
    next_touch_at: str = ""
    due: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "place_id": self.place_id,
            "business_name": self.business_name,
            "city": self.city,
            "genre_id": self.genre_id,
            "status": self.status,
            "next_action": self.next_action,
            "mockup_url": self.mockup_url,
            "facts": self.facts.to_dict(),
            "buttons": [b.to_dict() for b in self.buttons],
            "suppressed": self.suppressed,
            "suppression_reason": self.suppression_reason,
            "next_touch_at": self.next_touch_at,
            "due": self.due,
        }


@dataclass(frozen=True)
class OutreachPanelView:
    rows: list[ActionRow] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)
    facets: list[FacetOption] = field(default_factory=list)
    variants: list[str] = field(default_factory=list)
    default_variant: str = DEFAULT_VARIANT
    due_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "rows": [r.to_dict() for r in self.rows],
            "statuses": self.statuses,
            "facets": [f.to_dict() for f in self.facets],
            "variants": self.variants,
            "default_variant": self.default_variant,
            "due_count": self.due_count,
        }


FACET_LABELS = [
    ("preview", "Preview site"),
    ("email-present", "Email present"),
    ("phone-present", "Phone present"),
    ("social-present", "Social present"),
    ("any-contact", "Any contact"),
    ("no-contact", "No contact"),
    ("no-sends", "No sends"),
    ("any-sent", "Any sent"),
    ("email-not-sent", "Email not sent"),
    ("email-sent-once", "Email sent once"),
    ("email-sent-2plus", "Email sent 2+"),
    ("preview-no-sends", "Preview + no sends"),
    ("preview-email-unsent", "Preview + email unsent"),
    ("preview-email-sent-once", "Preview + email sent once"),
]


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
    *,
    suppressed: bool = False,
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
        # A suppressed prospect can never launch: every button is disabled and
        # its deep-link cleared, even when contact data is present.
        buttons.append(
            ChannelButton(
                channel=channel,
                label=label,
                contact_field=CHANNEL_CONTACT_FIELD[channel],
                contact_value=value,
                enabled=bool(value) and not suppressed,
                url="" if suppressed else url,
                copy=copy,
                sent_count=int(stats.get("count", 0) or 0),
                last_sent_at=str(stats.get("last_sent_at", "")),
            )
        )
    return buttons


def _facts_for_row(row: OutreachClientRow, buttons: list[ChannelButton]) -> RowFacts:
    by_channel = {button.channel: button for button in buttons}
    contact_channels = [button.channel for button in buttons if button.enabled]
    sent_channels = [button.channel for button in buttons if button.sent_count > 0]
    total_sent_count = sum(button.sent_count for button in buttons)
    last_sent_at = max(
        (button.last_sent_at for button in buttons if button.last_sent_at),
        default="",
    )
    email_button = by_channel.get("email")
    email_count = email_button.sent_count if email_button else 0

    tags: set[str] = set()
    tags.add("preview" if row.mockup_url else "no-preview")

    if email_button and email_button.enabled:
        tags.add("email-present")
    else:
        tags.add("email-missing")

    if any(
        by_channel.get(channel) and by_channel[channel].enabled
        for channel in ("sms", "call")
    ):
        tags.add("phone-present")
    else:
        tags.add("phone-missing")

    if any(
        by_channel.get(channel) and by_channel[channel].enabled
        for channel in ("facebook_dm", "instagram_dm")
    ):
        tags.add("social-present")
    else:
        tags.add("social-missing")

    tags.add("any-contact" if contact_channels else "no-contact")
    tags.add("any-sent" if total_sent_count else "no-sends")

    for button in buttons:
        if button.sent_count <= 0:
            tags.add(f"{button.channel}-not-sent")
            continue
        tags.add(f"{button.channel}-sent")
        if button.sent_count == 1:
            tags.add(f"{button.channel}-sent-once")
        else:
            tags.add(f"{button.channel}-sent-2plus")

    if row.mockup_url and total_sent_count == 0:
        tags.add("preview-no-sends")
    if row.mockup_url and email_count == 0:
        tags.add("preview-email-unsent")
    if row.mockup_url and email_count == 1:
        tags.add("preview-email-sent-once")

    return RowFacts(
        tags=sorted(tags),
        contact_channels=contact_channels,
        sent_channels=sent_channels,
        total_sent_count=total_sent_count,
        last_sent_at=last_sent_at,
    )


def _facet_options(rows: list[ActionRow]) -> list[FacetOption]:
    counts = {key: 0 for key, _label in FACET_LABELS}
    for row in rows:
        row_tags = set(row.facts.tags)
        for key in counts:
            if key in row_tags:
                counts[key] += 1
    return [FacetOption(key=key, label=label, count=counts[key]) for key, label in FACET_LABELS]


def build_outreach_panel(
    *,
    store: OutreachStore | None = None,
    lane_root: Path | None = None,
    now: str | None = None,
) -> OutreachPanelView:
    root = lane_root or default_outreach_lane_root()
    store = store or OutreachStore()
    overrides = store.all_overrides()
    touches = store.touch_summary()
    now = now or _now_iso()
    suppressed_keys = store.suppressed_keys()
    reason_by_key = {
        str(entry.get("key")): str(entry.get("reason") or "")
        for entry in (store.list_suppressions() if suppressed_keys else [])
    }
    rows = _load_ledger_rows(root)
    action_rows: list[ActionRow] = []
    due_count = 0
    for row in rows:
        keys = [key for _kind, key in suppression.keys_for_record(_row_record(row))]
        suppressed = bool(suppressed_keys) and any(key in suppressed_keys for key in keys)
        reason = next((reason_by_key[k] for k in keys if k in reason_by_key), "") if suppressed else ""
        buttons = _buttons_for_row(
            row,
            overrides.get(row.place_id, {}),
            touches.get(row.place_id, {}),
            suppressed=suppressed,
        )
        due = bool(row.next_touch_at) and row.next_touch_at <= now and not suppressed
        if due:
            due_count += 1
        action_rows.append(
            ActionRow(
                place_id=row.place_id,
                business_name=row.business_name,
                city=row.city,
                genre_id=row.genre_id,
                status=row.status.value,
                next_action=row.next_action,
                mockup_url=row.mockup_url,
                facts=_facts_for_row(row, buttons),
                buttons=buttons,
                suppressed=suppressed,
                suppression_reason=reason,
                next_touch_at=row.next_touch_at,
                due=due,
            )
        )
    return OutreachPanelView(
        rows=action_rows,
        statuses=[s.value for s in OutreachLaneStatus],
        facets=_facet_options(action_rows),
        variants=list(KNOWN_VARIANTS),
        default_variant=DEFAULT_VARIANT,
        due_count=due_count,
    )


# --------------------------------------------------------------- operations
def record_touch(
    place_id: str,
    channel: str,
    *,
    variant: str = DEFAULT_VARIANT,
    store: OutreachStore | None = None,
    lane_root: Path | None = None,
) -> dict[str, object]:
    """Log a human-confirmed send: append to the store, advance the ledger.

    Refuses to log against a suppressed prospect — the do-not-contact floor
    holds even though the actual send is manual.
    """
    if channel not in ALLOWED_CHANNELS:
        raise ValueError(f"unsupported channel {channel!r}")
    store = store or OutreachStore()
    if suppression.is_suppressed({"place_id": place_id}, store=store):
        raise ValueError(f"prospect {place_id!r} is suppressed; cannot log a send")
    touch = store.append_touch(place_id, channel, via="dashboard", variant=variant)
    row = auto_bump_on_touch(place_id, channel, lane_root=lane_root)
    return {
        "touch": touch,
        "status": row.status.value,
        "place_id": place_id,
        "variant": touch["variant"],
    }


def disqualify(
    place_id: str,
    reason: str,
    *,
    store: OutreachStore | None = None,
    lane_root: Path | None = None,
) -> dict[str, object]:
    """Operator "disqualify": suppress the prospect (by place_id and every
    contact handle) and close the ledger row to do_not_contact."""
    store = store or OutreachStore()
    root = lane_root or default_outreach_lane_root()
    row = next((r for r in _load_ledger_rows(root) if r.place_id == place_id), None)
    record = _row_record(row) if row else {"place_id": place_id}
    suppression.suppress(record, reason or "disqualified by operator", "disqualified", store=store)
    updated = set_row_status(place_id, OutreachLaneStatus.DO_NOT_CONTACT, lane_root=lane_root)
    return {"place_id": place_id, "status": updated.status.value, "suppressed": True}


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
    "FacetOption",
    "ActionRow",
    "OutreachPanelView",
    "RowFacts",
    "build_outreach_panel",
    "record_touch",
    "set_contact",
    "set_status",
    "disqualify",
]
