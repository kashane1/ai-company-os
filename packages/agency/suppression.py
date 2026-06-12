"""Fail-closed do-not-contact registry for the outreach lane.

Before volume sending, every prospect and every contact handle must be checked
against a suppression list or BBW accrues CAN-SPAM liability with each batch.
This module is the one gate every send path consults: the dashboard queue, the
outreach draft generator, and (later) the follow-up sequencer and reply-sync.

Design choices:

- **Fail-closed.** ``is_suppressed`` returns ``True`` whenever it cannot prove a
  prospect is safe to contact: an explicit suppression match, a record that
  resolves to *no* identifying key, or any store error. A normal ledger row
  always carries a ``place_id``, so real prospects are never falsely excluded —
  but a degenerate, identity-less record is treated as suppressed.
- **Keyed by place_id *and* every handle.** Suppressing a prospect writes one
  key per channel, so a re-scan that surfaces the same email/phone under a new
  ``place_id`` is still caught.
- **One-way in code.** There is no un-suppress API. Removing a suppression is a
  deliberate manual edit with founder involvement (see
  ``OutreachStore`` / ``state/prospects/outreach-lane/outreach.sqlite3``).

Storage lives in the existing ``outreach.sqlite3`` (``OutreachStore``), not on
``ProspectRecord`` — suppression is runtime state, never source schema.
"""

from __future__ import annotations

from typing import Iterable

from packages.agency.outreach_messages import normalize_phone
from packages.agency.outreach_store import OutreachStore

# How suppression entries were created. ``reply_stop`` is reserved for the
# future reply-sync (item 5) calling ``suppress`` on STOP-intent replies.
SUPPRESSION_SOURCES = ("operator", "reply_stop", "disqualified")

# kind -> the record/row fields that carry that handle. Mirrors the override
# fields the dashboard already edits, so a suppressed handle and a launchable
# contact are the same value.
_HANDLE_FIELDS: dict[str, tuple[str, ...]] = {
    "email": ("contact_email",),
    "phone": ("phone",),
    "instagram": ("contact_instagram",),
    "facebook": ("contact_facebook",),
}


def _normalize(kind: str, value: object) -> str | None:
    """Canonicalize one handle to a stable suppression key fragment, or ``None``
    when the value is blank/unusable."""
    text = str(value or "").strip()
    if not text:
        return None
    if kind == "place_id":
        return text
    if kind == "email":
        return text.lower()
    if kind == "phone":
        digits = normalize_phone(text)
        return digits or None
    if kind in ("instagram", "facebook"):
        handle = text.rsplit("/", 1)[-1].lstrip("@").strip().lower()
        return handle or None
    return text.lower()


def _key(kind: str, value: str) -> str:
    return f"{kind}:{value}"


def keys_for_record(record: dict[str, object]) -> list[tuple[str, str]]:
    """Every ``(kind, key)`` a record can be suppressed under: its place_id plus
    one key per present contact handle."""
    keys: list[tuple[str, str]] = []
    place = _normalize("place_id", record.get("place_id"))
    if place:
        keys.append(("place_id", _key("place", place)))
    for kind, fields in _HANDLE_FIELDS.items():
        for field in fields:
            normalized = _normalize(kind, record.get(field))
            if normalized:
                keys.append((kind, _key(kind, normalized)))
                break
    return keys


def is_suppressed(record: dict[str, object], *, store: OutreachStore | None = None) -> bool:
    """``True`` if any of the record's keys is suppressed — fail-closed.

    A record that resolves to zero keys (no place_id, no handles) cannot be
    proven safe, so it is treated as suppressed. Any store error is likewise
    treated as suppressed: when the registry can't be read, do not contact.
    """
    try:
        keys = keys_for_record(record)
        if not keys:
            return True
        store = store or OutreachStore()
        suppressed = store.suppressed_keys()
        return any(key in suppressed for _kind, key in keys)
    except Exception:
        return True


def suppression_reason(
    record: dict[str, object], *, store: OutreachStore | None = None
) -> str | None:
    """The reason a record is suppressed (first matching key), or ``None``."""
    try:
        keys = {key for _kind, key in keys_for_record(record)}
        if not keys:
            return "no identifying contact data"
        store = store or OutreachStore()
        for entry in store.list_suppressions():
            if str(entry.get("key")) in keys:
                return str(entry.get("reason") or "")
    except Exception:
        return "suppression registry unavailable"
    return None


def suppress(
    record_or_handle: dict[str, object] | tuple[str, str],
    reason: str,
    source: str,
    *,
    store: OutreachStore | None = None,
) -> list[dict[str, object]]:
    """Suppress a record (all of its keys) or a single ``(kind, value)`` handle.

    Returns the rows written. ``source`` should be one of SUPPRESSION_SOURCES.
    """
    store = store or OutreachStore()
    if isinstance(record_or_handle, tuple):
        kind, value = record_or_handle
        normalized = _normalize(kind, value)
        if not normalized:
            raise ValueError(f"cannot suppress empty {kind} handle")
        pairs: Iterable[tuple[str, str]] = [(kind, _key(kind, normalized))]
    else:
        pairs = keys_for_record(record_or_handle)
        if not pairs:
            raise ValueError("record has no identifying keys to suppress")
    return [store.suppress_key(key, kind, reason, source) for kind, key in pairs]


__all__ = [
    "SUPPRESSION_SOURCES",
    "keys_for_record",
    "is_suppressed",
    "suppression_reason",
    "suppress",
]
