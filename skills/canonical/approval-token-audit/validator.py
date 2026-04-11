"""approval-token-audit — pure-Python validator.

Replays the magic-link HMAC approval contract. The store is injected so
this module does not import the live approval store (keeps it testable).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


P0_SECOND_FACTOR_WINDOW = timedelta(seconds=60)
DEFAULT_TTL = timedelta(minutes=30)
P0_TTL = timedelta(minutes=5)


def _now(_clock) -> datetime:
    return _clock() if _clock else datetime.now(timezone.utc)


def run(payload: dict) -> dict:
    approval_id = payload["approval_id"]
    expected_action = payload["expected_action"]
    expected_subject_id = payload["expected_subject_id"]
    store = payload["store"]
    clock = payload.get("clock")

    try:
        record: dict[str, Any] = store.load(approval_id)
    except Exception as exc:
        # Store/adapter errors are infrastructure failures, not verdict mismatches.
        return {
            "verdict": "fail",
            "reason": f"exception:adapter_{type(exc).__name__}",
            "detail": str(exc),
            "events": [],
        }

    events: list[str] = []
    if record.get("action") != expected_action:
        return _fail("action_mismatch", events)
    if record.get("subject_id") != expected_subject_id:
        return _fail("subject_mismatch", events)

    status = record.get("status")
    if status != "approved":
        return _fail(f"not_approved:{status}", events)

    is_p0 = bool(record.get("p0"))
    ttl = P0_TTL if is_p0 else DEFAULT_TTL

    issued = record.get("issued_at")
    approved = record.get("approved_at")
    if not issued or not approved:
        return _fail("missing_timestamps", events)
    if approved - issued > ttl:
        return _fail("ttl_exceeded", events)
    events.append("ttl_ok")

    burn_count = int(record.get("burn_count", 0))
    if burn_count != 1:
        return _fail(f"burn_count={burn_count}", events)
    events.append("single_use_ok")

    if is_p0:
        sf = record.get("second_factor_at")
        if not sf:
            return _fail("second_factor_missing", events)
        if abs((sf - approved).total_seconds()) > P0_SECOND_FACTOR_WINDOW.total_seconds():
            return _fail("second_factor_out_of_window", events)
        events.append("second_factor_ok")

    expected_device = record.get("expected_device_fingerprint")
    actual_device = record.get("device_fingerprint")
    if expected_device and expected_device != actual_device:
        return _fail("device_mismatch", events)
    events.append("device_ok")

    transitions = list(record.get("transitions", []))
    if "approved" not in transitions:
        return _fail("no_approved_transition", events)
    events.append("audit_trail_ok")

    return {"verdict": "ok", "reason": "", "events": events}


def _fail(reason: str, events: list[str]) -> dict:
    return {"verdict": "fail", "reason": reason, "events": events}
