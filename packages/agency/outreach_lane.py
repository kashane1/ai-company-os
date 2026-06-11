"""Human-gated outreach operations ledger for deployed prospect demos.

This module is the repo's outreach brain: it drafts, tracks, and reports.
It does not send email, SMS, or social DMs. Outbound contact stays manual or
behind a future approved CRM adapter.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable

from packages.agency.outreach import recommended_channel
from packages.agency.outreach_store import (
    ALLOWED_CHANNELS,
    OutreachStore,
    normalize_channel,
)
from packages.agency.prospect_site import city_label
from packages.config.settings import load_runtime_paths

# Outcomes that mean a message was actually delivered through the channel, so
# they mirror into the SQLite touch store the dashboard reads. Status-only
# outcomes (replied/won/lost/...) update the ledger but are not new sends.
SEND_OUTCOMES = {"sent", "left_voicemail"}


class OutreachLaneStatus(str, Enum):
    NEEDS_BESPOKE = "needs_bespoke"
    READY_TO_DRAFT = "ready_to_draft"
    READY_TO_SEND = "ready_to_send"
    SENT = "sent"
    FOLLOW_UP_DUE = "follow_up_due"
    REPLIED = "replied"
    WON = "won"
    LOST = "lost"
    DO_NOT_CONTACT = "do_not_contact"
    BLOCKED = "blocked"


MANUAL_OUTCOMES_TO_STATUS = {
    "sent": OutreachLaneStatus.SENT,
    "left_voicemail": OutreachLaneStatus.SENT,
    "no_answer": OutreachLaneStatus.FOLLOW_UP_DUE,
    "follow_up_due": OutreachLaneStatus.FOLLOW_UP_DUE,
    "replied": OutreachLaneStatus.REPLIED,
    "won": OutreachLaneStatus.WON,
    "lost": OutreachLaneStatus.LOST,
    "do_not_contact": OutreachLaneStatus.DO_NOT_CONTACT,
    "blocked": OutreachLaneStatus.BLOCKED,
}

STATUS_SORT = {
    OutreachLaneStatus.FOLLOW_UP_DUE: 0,
    OutreachLaneStatus.READY_TO_SEND: 1,
    OutreachLaneStatus.READY_TO_DRAFT: 2,
    OutreachLaneStatus.SENT: 3,
    OutreachLaneStatus.REPLIED: 4,
    OutreachLaneStatus.NEEDS_BESPOKE: 5,
    OutreachLaneStatus.BLOCKED: 6,
    OutreachLaneStatus.WON: 7,
    OutreachLaneStatus.LOST: 8,
    OutreachLaneStatus.DO_NOT_CONTACT: 9,
}


@dataclass(frozen=True)
class OutreachClientRow:
    place_id: str
    business_name: str
    city: str
    genre_id: str
    rating: float | None
    review_count: int
    mockup_url: str
    mockup_version: str
    recommended_channel: str
    status: OutreachLaneStatus
    next_action: str
    phone: str = ""
    contact_email: str = ""
    contact_instagram: str = ""
    contact_facebook: str = ""
    contact_booking_url: str = ""
    manual_channel: str = ""
    last_touch_at: str = ""
    next_follow_up_at: str = ""
    draft_path: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "place_id": self.place_id,
            "business_name": self.business_name,
            "city": self.city,
            "genre_id": self.genre_id,
            "rating": self.rating,
            "review_count": self.review_count,
            "mockup_url": self.mockup_url,
            "mockup_version": self.mockup_version,
            "recommended_channel": self.recommended_channel,
            "status": self.status.value,
            "next_action": self.next_action,
            "phone": self.phone,
            "contact_email": self.contact_email,
            "contact_instagram": self.contact_instagram,
            "contact_facebook": self.contact_facebook,
            "contact_booking_url": self.contact_booking_url,
            "manual_channel": self.manual_channel,
            "last_touch_at": self.last_touch_at,
            "next_follow_up_at": self.next_follow_up_at,
            "draft_path": self.draft_path,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "OutreachClientRow":
        return cls(
            place_id=str(payload["place_id"]),
            business_name=str(payload.get("business_name", "")),
            city=str(payload.get("city", "")),
            genre_id=str(payload.get("genre_id", "")),
            rating=_opt_float(payload.get("rating")),
            review_count=int(payload.get("review_count", 0) or 0),
            mockup_url=str(payload.get("mockup_url", "")),
            mockup_version=str(payload.get("mockup_version", "")),
            recommended_channel=str(payload.get("recommended_channel", "")),
            status=OutreachLaneStatus(str(payload.get("status", "blocked"))),
            next_action=str(payload.get("next_action", "")),
            phone=str(payload.get("phone", "")),
            contact_email=str(payload.get("contact_email", "")),
            contact_instagram=str(payload.get("contact_instagram", "")),
            contact_facebook=str(payload.get("contact_facebook", "")),
            contact_booking_url=str(payload.get("contact_booking_url", "")),
            manual_channel=str(payload.get("manual_channel", "")),
            last_touch_at=str(payload.get("last_touch_at", "")),
            next_follow_up_at=str(payload.get("next_follow_up_at", "")),
            draft_path=str(payload.get("draft_path", "")),
            notes=str(payload.get("notes", "")),
        )


def default_outreach_lane_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).state_root / "prospects" / "outreach-lane"


def default_records_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).state_root / "prospects" / "records"


def load_raw_records(records_root: Path | None = None) -> list[dict[str, object]]:
    root = records_root or default_records_root()
    records: list[dict[str, object]] = []
    for path in sorted(root.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def build_client_rows(
    records: Iterable[dict[str, object]],
    *,
    existing_rows: dict[str, dict[str, object]] | None = None,
    repo_root: Path | None = None,
) -> list[OutreachClientRow]:
    existing_rows = existing_rows or {}
    rows = [
        _row_for_record(record, existing_rows.get(str(record.get("place_id", ""))), repo_root=repo_root)
        for record in records
        if _is_deployed_agold(record)
    ]
    return sorted(rows, key=_row_sort_key)


def refresh_client_status(
    *,
    records_root: Path | None = None,
    lane_root: Path | None = None,
    repo_root: Path | None = None,
) -> list[OutreachClientRow]:
    root = lane_root or default_outreach_lane_root(repo_root)
    existing = load_existing_rows(root)
    rows = build_client_rows(
        load_raw_records(records_root or default_records_root(repo_root)),
        existing_rows=existing,
        repo_root=repo_root,
    )
    write_client_status(rows, lane_root=root)
    return rows


def load_existing_rows(lane_root: Path | None = None) -> dict[str, dict[str, object]]:
    root = lane_root or default_outreach_lane_root()
    path = root / "client-status.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("place_id", "")): row
        for row in rows
        if isinstance(row, dict) and row.get("place_id")
    }


def write_client_status(rows: list[OutreachClientRow], *, lane_root: Path) -> tuple[Path, Path]:
    lane_root.mkdir(parents=True, exist_ok=True)
    json_path = lane_root / "client-status.json"
    md_path = lane_root / "client-status.md"
    payload = {
        "updated_at": _now_iso(),
        "summary": summarize_rows(rows),
        "rows": [row.to_dict() for row in rows],
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    md_path.write_text(render_client_status_markdown(rows, updated_at=str(payload["updated_at"])))
    return json_path, md_path


def summarize_rows(rows: Iterable[OutreachClientRow]) -> dict[str, int]:
    row_list = list(rows)
    counts = Counter(row.status.value for row in row_list)
    summary = {"total": len(row_list)}
    for status in OutreachLaneStatus:
        summary[status.value] = counts.get(status.value, 0)
    return summary


def log_manual_touch(
    place_id: str,
    *,
    channel: str,
    outcome: str,
    lane_root: Path | None = None,
    occurred_at: str = "",
    next_follow_up_at: str = "",
    notes: str = "",
    store: OutreachStore | None = None,
) -> OutreachClientRow:
    root = lane_root or default_outreach_lane_root()
    status_path = root / "client-status.json"
    if not status_path.exists():
        raise FileNotFoundError(f"missing outreach status ledger: {status_path}")
    payload = json.loads(status_path.read_text())
    rows = [OutreachClientRow.from_dict(row) for row in payload.get("rows", [])]
    occurred_at = occurred_at or _now_iso()
    new_status = MANUAL_OUTCOMES_TO_STATUS.get(outcome)
    if new_status is None:
        allowed = ", ".join(sorted(MANUAL_OUTCOMES_TO_STATUS))
        raise ValueError(f"unsupported outreach outcome {outcome!r}; allowed: {allowed}")

    updated_rows: list[OutreachClientRow] = []
    updated_row: OutreachClientRow | None = None
    for row in rows:
        if row.place_id != place_id:
            updated_rows.append(row)
            continue
        merged_notes = _merge_notes(row.notes, notes)
        updated_payload = {
            **row.to_dict(),
            "status": new_status.value,
            "manual_channel": channel,
            "last_touch_at": occurred_at,
            "next_follow_up_at": next_follow_up_at,
            "notes": merged_notes,
            "next_action": _next_action_for_status(new_status, channel),
        }
        updated_row = OutreachClientRow.from_dict(updated_payload)
        updated_rows.append(updated_row)
    if updated_row is None:
        raise KeyError(f"place_id {place_id!r} not found in outreach ledger")

    _append_touch(
        root,
        {
            "place_id": place_id,
            "channel": channel,
            "outcome": outcome,
            "occurred_at": occurred_at,
            "next_follow_up_at": next_follow_up_at,
            "notes": notes,
            "send_boundary": "manual_human_gated",
        },
    )
    # Mirror delivered sends into the SQLite store the dashboard reads, so a CLI
    # `log ... --outcome sent` and the dashboard's "Log sent" produce the same
    # per-channel touch. Status-only outcomes are left to the ledger.
    channel_norm = normalize_channel(channel)
    if outcome in SEND_OUTCOMES and channel_norm in ALLOWED_CHANNELS:
        touch_store = store or OutreachStore(sqlite_path=root / "outreach.sqlite3")
        touch_store.append_touch(
            place_id, channel_norm, via="cli", note=notes, sent_at=occurred_at
        )
    write_client_status(sorted(updated_rows, key=_row_sort_key), lane_root=root)
    return updated_row


# States that count as "before first contact" — a logged send bumps them to SENT.
# Manual states past SENT (replied/won/lost/etc.) are never auto-downgraded.
PRE_SEND_STATUSES = {
    OutreachLaneStatus.NEEDS_BESPOKE,
    OutreachLaneStatus.READY_TO_DRAFT,
    OutreachLaneStatus.READY_TO_SEND,
}


def _mutate_row(
    place_id: str,
    apply: "Callable[[OutreachClientRow], dict[str, object]]",
    *,
    lane_root: Path | None = None,
) -> OutreachClientRow:
    """Load the ledger, replace one row via ``apply``, rewrite atomically."""
    root = lane_root or default_outreach_lane_root()
    status_path = root / "client-status.json"
    if not status_path.exists():
        raise FileNotFoundError(f"missing outreach status ledger: {status_path}")
    payload = json.loads(status_path.read_text())
    rows = [OutreachClientRow.from_dict(row) for row in payload.get("rows", [])]
    updated_row: OutreachClientRow | None = None
    updated_rows: list[OutreachClientRow] = []
    for row in rows:
        if row.place_id != place_id:
            updated_rows.append(row)
            continue
        merged = {**row.to_dict(), **apply(row)}
        updated_row = OutreachClientRow.from_dict(merged)
        updated_rows.append(updated_row)
    if updated_row is None:
        raise KeyError(f"place_id {place_id!r} not found in outreach ledger")
    write_client_status(sorted(updated_rows, key=_row_sort_key), lane_root=root)
    return updated_row


def set_row_status(
    place_id: str,
    new_status: OutreachLaneStatus,
    *,
    lane_root: Path | None = None,
) -> OutreachClientRow:
    """Operator-driven status change (the dashboard dropdown)."""
    return _mutate_row(
        place_id,
        lambda row: {
            "status": new_status.value,
            "next_action": _next_action_for_status(
                new_status, row.manual_channel or row.recommended_channel
            ),
        },
        lane_root=lane_root,
    )


def auto_bump_on_touch(
    place_id: str,
    channel: str,
    *,
    occurred_at: str = "",
    lane_root: Path | None = None,
) -> OutreachClientRow:
    """Record that a manual send happened: stamp the touch time, set the channel,
    and advance a pre-send row to SENT. Rows already past SENT keep their status.
    """
    occurred_at = occurred_at or _now_iso()

    def apply(row: OutreachClientRow) -> dict[str, object]:
        new_status = (
            OutreachLaneStatus.SENT if row.status in PRE_SEND_STATUSES else row.status
        )
        return {
            "status": new_status.value,
            "manual_channel": channel,
            "last_touch_at": occurred_at,
            "next_action": _next_action_for_status(new_status, channel),
        }

    return _mutate_row(place_id, apply, lane_root=lane_root)


def render_client_status_markdown(rows: list[OutreachClientRow], *, updated_at: str) -> str:
    summary = summarize_rows(rows)
    lines = [
        "# Outreach Lane Client Status",
        "",
        f"_Updated: {updated_at}_",
        "",
        "Human-gated outbound lane. This list drafts, tracks, and schedules next actions; it does not send email, SMS, Instagram, or Facebook messages.",
        "",
        "## Summary",
        "",
        f"- Total deployed Cohort A prospects: {summary['total']}",
        f"- Ready to send: {summary[OutreachLaneStatus.READY_TO_SEND.value]}",
        f"- Needs bespoke rebuild before outreach: {summary[OutreachLaneStatus.NEEDS_BESPOKE.value]}",
        f"- Sent / waiting: {summary[OutreachLaneStatus.SENT.value]}",
        f"- Follow-up due: {summary[OutreachLaneStatus.FOLLOW_UP_DUE.value]}",
        f"- Replied: {summary[OutreachLaneStatus.REPLIED.value]}",
        f"- Blocked / recheck needed: {summary[OutreachLaneStatus.BLOCKED.value]}",
        "",
        "## Operator List",
        "",
        "| Status | Business | City | Type | Channel | Next action | URL | Draft |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {status} | {business} | {city} | {genre} | {channel} | {action} | {url} | {draft} |".format(
                status=row.status.value,
                business=_md(row.business_name),
                city=_md(row.city),
                genre=_md(row.genre_id),
                channel=_md(row.manual_channel or row.recommended_channel),
                action=_md(row.next_action),
                url=_link("site", row.mockup_url),
                draft=_draft_link(row.draft_path),
            )
        )
    lines.extend(
        [
            "",
            "## Manual Logging",
            "",
            "After sending by hand, run:",
            "",
            "```bash",
            "python scripts/agency/outreach_lane.py log --place-id <PLACE_ID> --channel email --outcome sent --next-follow-up 2026-06-12 --notes \"sent manually\"",
            "```",
            "",
            "Allowed outcomes: " + ", ".join(sorted(MANUAL_OUTCOMES_TO_STATUS)),
        ]
    )
    return "\n".join(lines) + "\n"


def _row_for_record(
    record: dict[str, object],
    existing: dict[str, object] | None,
    *,
    repo_root: Path | None,
) -> OutreachClientRow:
    place_id = str(record.get("place_id", ""))
    mockup_version = str(record.get("mockup_version", ""))
    channel = recommended_channel(record)
    default_status = (
        OutreachLaneStatus.BLOCKED
        if channel == "recheck_has_site"
        else (
            OutreachLaneStatus.READY_TO_SEND
            if mockup_version == "v2-bespoke"
            else OutreachLaneStatus.NEEDS_BESPOKE
        )
    )
    preserved_status = _preserved_status(existing, default_status)
    manual_channel = str((existing or {}).get("manual_channel", ""))
    return OutreachClientRow(
        place_id=place_id,
        business_name=str(record.get("display_name", "")),
        city=city_label(str(record.get("city_id", ""))),
        genre_id=str(record.get("genre_id", "")),
        rating=_opt_float(record.get("rating")),
        review_count=int(record.get("user_ratings_total", 0) or 0),
        mockup_url=str(record.get("mockup_url", "")),
        mockup_version=mockup_version,
        recommended_channel=channel,
        status=preserved_status,
        next_action=_next_action_for_status(preserved_status, manual_channel or channel),
        phone=str(record.get("phone", "")),
        contact_email=str(record.get("contact_email", "")),
        contact_instagram=str(record.get("contact_instagram", "")),
        contact_facebook=str(record.get("contact_facebook", "")),
        contact_booking_url=str(record.get("contact_booking_url", "")),
        manual_channel=manual_channel,
        last_touch_at=str((existing or {}).get("last_touch_at", "")),
        next_follow_up_at=str((existing or {}).get("next_follow_up_at", "")),
        draft_path=_draft_path(place_id, repo_root),
        notes=str((existing or {}).get("notes", "")),
    )


def _is_deployed_agold(record: dict[str, object]) -> bool:
    return (
        record.get("composite_cohort") == "A_gold"
        and bool(str(record.get("mockup_url", "")).strip())
        and bool(str(record.get("place_id", "")).strip())
    )


def _preserved_status(
    existing: dict[str, object] | None,
    default_status: OutreachLaneStatus,
) -> OutreachLaneStatus:
    if not existing or not existing.get("status"):
        return default_status
    prior = OutreachLaneStatus(str(existing["status"]))
    if default_status == OutreachLaneStatus.BLOCKED and prior in {
        OutreachLaneStatus.NEEDS_BESPOKE,
        OutreachLaneStatus.READY_TO_DRAFT,
        OutreachLaneStatus.READY_TO_SEND,
    }:
        return default_status
    if prior == OutreachLaneStatus.NEEDS_BESPOKE and default_status == OutreachLaneStatus.READY_TO_SEND:
        return default_status
    return prior


def _next_action_for_status(status: OutreachLaneStatus, channel: str) -> str:
    if status == OutreachLaneStatus.NEEDS_BESPOKE:
        return "Rebuild bespoke demo before outreach"
    if status == OutreachLaneStatus.READY_TO_DRAFT:
        return "Generate outreach draft"
    if status == OutreachLaneStatus.READY_TO_SEND:
        return f"Review draft, personalize one line, send manually via {channel}"
    if status == OutreachLaneStatus.SENT:
        return "Wait for reply or log follow-up when due"
    if status == OutreachLaneStatus.FOLLOW_UP_DUE:
        return f"Send manual follow-up via {channel}"
    if status == OutreachLaneStatus.REPLIED:
        return "Reply manually and qualify next step"
    if status == OutreachLaneStatus.WON:
        return "Promote prospect into client intake"
    if status == OutreachLaneStatus.LOST:
        return "No active follow-up"
    if status == OutreachLaneStatus.DO_NOT_CONTACT:
        return "Suppress all outreach"
    if channel == "recheck_has_site":
        return "Recheck owned-site signal before outreach"
    return "Resolve blocker before outreach"


def _draft_path(place_id: str, repo_root: Path | None) -> str:
    if not place_id:
        return ""
    root = repo_root or load_runtime_paths().repo_root
    site_root = root / "state" / "prospects" / "sites" / place_id
    for name in ("outreach.md", "outreach-with-mockup.md"):
        path = site_root / name
        if path.exists():
            return str(path.relative_to(root))
    return ""


def _append_touch(lane_root: Path, payload: dict[str, object]) -> None:
    lane_root.mkdir(parents=True, exist_ok=True)
    with (lane_root / "touches.jsonl").open("a") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _merge_notes(existing: str, new: str) -> str:
    if not new:
        return existing
    if not existing:
        return new
    return f"{existing}\n{new}"


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _row_sort_key(row: OutreachClientRow) -> tuple[int, str, str]:
    return (STATUS_SORT[row.status], row.city, row.business_name.lower())


def _opt_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)  # type: ignore[arg-type]


def _md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _link(label: str, url: str) -> str:
    return f"[{label}]({url})" if url else ""


def _draft_link(path: str) -> str:
    return f"[draft]({path})" if path else ""
