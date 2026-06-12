"""Reply-sync: match an inbound email back to a prospect and record the reply.

Pure and Gmail-agnostic. The worker (``apps/worker-reply-sync``) fetches mail
read-only and hands each message to :func:`process_reply` as a :class:`ParsedReply`;
this module owns *matching* (by the ``BBW-<6char>`` token first, sender address
second), STOP-intent detection, and the three writes a matched reply makes:

1. advance the lane row to ``replied`` (never downgrading a won/lost/DNC row),
2. log an **inbound** touch in the store (so it never inflates the sent metric),
3. drop a snippet to ``state/prospects/outreach-lane/replies/<place_id>.md`` for
   operator review.

A STOP-intent reply also writes to the suppression registry
(``source="reply_stop"``) and flags the snippet for operator confirmation — the
reply is honored as do-not-contact, but nothing beyond suppression happens
silently. Nothing here sends, labels, moves, or marks mail read.

Idempotency is the worker's job: it dedupes by Gmail thread id + a persisted
``historyId`` cursor before calling :func:`process_reply`. Processing the same
thread twice would append a second touch/snippet section.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from packages.agency import suppression
from packages.agency.outreach import BBW_REF_RE
from packages.agency.outreach_lane import (
    OutreachLaneStatus,
    default_outreach_lane_root,
    load_existing_rows,
    set_row_status,
)
from packages.agency.outreach_store import INBOUND, OutreachStore

# Conservative opt-out phrases. "no thanks" is included because the outbound
# email advertises it verbatim ('Reply "no thanks" and I won\'t email again.'),
# so honoring it is a correctness requirement, not a nicety. Matched case- and
# whitespace-insensitively as a substring of the reply body.
STOP_KEYWORDS = (
    "no thanks",
    "unsubscribe",
    "remove me",
    "do not contact",
    "not interested",
    "stop",
)

# Statuses a reply must never overwrite. A reply can still *arrive* on these rows
# (we log the touch + snippet), but the lane status stays put — a won deal does
# not regress to "replied".
_NO_DOWNGRADE = {
    OutreachLaneStatus.WON,
    OutreachLaneStatus.LOST,
    OutreachLaneStatus.DO_NOT_CONTACT,
}


@dataclass(frozen=True)
class ParsedReply:
    """One inbound message, normalized by the worker from the Gmail payload."""

    thread_id: str
    from_email: str
    subject: str = ""
    body: str = ""
    from_name: str = ""
    received_at: str = ""


@dataclass(frozen=True)
class ReplyOutcome:
    matched: bool
    place_id: str | None = None
    token: str | None = None
    matched_by: str = ""  # "token" | "sender" | ""
    status: str | None = None
    status_changed: bool = False
    suppressed: bool = False
    snippet_path: str | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "matched": self.matched,
            "place_id": self.place_id,
            "token": self.token,
            "matched_by": self.matched_by,
            "status": self.status,
            "status_changed": self.status_changed,
            "suppressed": self.suppressed,
            "snippet_path": self.snippet_path,
            "reason": self.reason,
        }


# ----------------------------------------------------------------- detection
def extract_ref_token(*texts: str) -> str | None:
    """First ``BBW-<6char>`` token found across the given texts (subject, body),
    or ``None``. Case-sensitive: tokens are emitted uppercase."""
    for text in texts:
        match = BBW_REF_RE.search(text or "")
        if match:
            return match.group(0)
    return None


def detect_stop_intent(text: str) -> bool:
    """True if the reply body contains a conservative opt-out phrase."""
    haystack = " ".join((text or "").lower().split())
    return any(keyword in haystack for keyword in STOP_KEYWORDS)


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def _email_index(lane_root: Path, store: OutreachStore) -> dict[str, str]:
    """``{normalized_email: place_id}`` from lane rows + contact overrides, so a
    reply with no token can still be matched by sender address."""
    index: dict[str, str] = {}
    for place_id, row in load_existing_rows(lane_root).items():
        email = _normalize_email(str(row.get("contact_email", "")))
        if email:
            index.setdefault(email, place_id)
    # Overrides are authoritative over the scanned email, so they win.
    for place_id, fields in store.all_overrides().items():
        email = _normalize_email(str(fields.get("contact_email", "")))
        if email:
            index[email] = place_id
    return index


def resolve_place_id(
    reply: ParsedReply, *, store: OutreachStore, lane_root: Path
) -> tuple[str | None, str | None, str]:
    """Resolve ``(place_id, token, matched_by)`` for a reply.

    Token first (only tokens we actually sent resolve), sender address second.
    Returns ``(None, token, "")`` when nothing matches.
    """
    token = extract_ref_token(reply.subject, reply.body)
    if token:
        place_id = store.place_id_for_token(token)
        if place_id:
            return place_id, token, "token"
    sender = _normalize_email(reply.from_email)
    if sender:
        place_id = _email_index(lane_root, store).get(sender)
        if place_id:
            return place_id, token, "sender"
    return None, token, ""


# ------------------------------------------------------------------- process
def process_reply(
    reply: ParsedReply,
    *,
    store: OutreachStore | None = None,
    lane_root: Path | None = None,
) -> ReplyOutcome:
    """Match an inbound reply to a prospect and record it. See module docstring.

    An unmatched reply mutates nothing and returns ``matched=False`` with a
    reason, so the worker can log it for manual review.
    """
    lane_root = lane_root or default_outreach_lane_root()
    store = store or OutreachStore(sqlite_path=lane_root / "outreach.sqlite3")

    place_id, token, matched_by = resolve_place_id(reply, store=store, lane_root=lane_root)
    if not place_id:
        return ReplyOutcome(
            matched=False,
            token=token,
            reason="no token or sender match",
        )

    rows = load_existing_rows(lane_root)
    current = _current_status(rows.get(place_id, {}))

    # 1. Advance to replied, unless the row is in a state a reply must not undo.
    status_changed = False
    status_value = current.value if current else None
    if current not in _NO_DOWNGRADE:
        updated = set_row_status(place_id, OutreachLaneStatus.REPLIED, lane_root=lane_root)
        status_value = updated.status.value
        status_changed = current != OutreachLaneStatus.REPLIED

    # 2. Log an inbound touch (excluded from the sent metric by direction).
    store.append_touch(
        place_id,
        "email",
        via="reply_sync",
        direction=INBOUND,
        sent_at=reply.received_at or None,
        note=(reply.subject or "")[:200],
    )

    # 3. STOP-intent → suppress (do-not-contact floor) + flag for the operator.
    stop = detect_stop_intent(reply.body) or detect_stop_intent(reply.subject)
    if stop:
        record = {
            "place_id": place_id,
            "contact_email": reply.from_email,
        }
        suppression.suppress(record, "reply opt-out", "reply_stop", store=store)

    # 4. Operator-review snippet.
    snippet_path = _write_snippet(
        reply, place_id=place_id, token=token, matched_by=matched_by, stop=stop, lane_root=lane_root
    )

    return ReplyOutcome(
        matched=True,
        place_id=place_id,
        token=token,
        matched_by=matched_by,
        status=status_value,
        status_changed=status_changed,
        suppressed=stop,
        snippet_path=str(snippet_path),
        reason="suppressed: stop intent" if stop else "",
    )


def _current_status(row: dict[str, object]) -> OutreachLaneStatus | None:
    raw = str(row.get("status", "")).strip()
    if not raw:
        return None
    try:
        return OutreachLaneStatus(raw)
    except ValueError:
        return None


def replies_dir(lane_root: Path) -> Path:
    return lane_root / "replies"


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_snippet(
    reply: ParsedReply,
    *,
    place_id: str,
    token: str | None,
    matched_by: str,
    stop: bool,
    lane_root: Path,
) -> Path:
    """Append a reply section to ``replies/<place_id>.md``. Appends (not
    overwrites) so a multi-reply thread keeps its history for the operator."""
    directory = replies_dir(lane_root)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{place_id}.md"
    excerpt = (reply.body or "").strip()
    if len(excerpt) > 500:
        excerpt = excerpt[:500].rstrip() + "…"
    lines = [
        "" if path.exists() else f"# Replies — {place_id}\n",
        f"## {reply.received_at or _now_iso()}",
        "",
        f"- From: {reply.from_name or ''} <{reply.from_email}>".replace(" <>", ""),
        f"- Subject: {reply.subject}",
        f"- Matched by: {matched_by or 'unmatched'}"
        + (f" (token {token})" if token else ""),
    ]
    if stop:
        lines.append(
            "- **STOP intent detected — suppressed; needs operator confirmation**"
        )
    lines += ["", "> " + excerpt.replace("\n", "\n> ") if excerpt else "> (empty body)", ""]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


__all__ = [
    "ParsedReply",
    "ReplyOutcome",
    "STOP_KEYWORDS",
    "extract_ref_token",
    "detect_stop_intent",
    "resolve_place_id",
    "process_reply",
    "replies_dir",
]
