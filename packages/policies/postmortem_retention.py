"""PostMortem retention & staleness policy (Phase 1).

Pure functions over ``PostMortem`` records — no I/O. Used by:
- ``packages/db/postmortem_store.py:list_recent`` for visibility filtering
- ``packages/tools/primitives/verification_loop_runtime_runner.py:_stale_postmortems_check``
"""

from __future__ import annotations

from datetime import datetime, timezone

from packages.schemas.postmortem import PostMortem, PostMortemSeverity, PostMortemStatus


VISIBILITY_WINDOW_DAYS = 90
STALE_THRESHOLD_DAYS = 14
CRITICAL_AGE_DAYS = 30


def _parse_iso(value: str) -> datetime:
    """Tolerant ISO-8601 parser; mirrors failure-mode-regression validator."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _age_days(record: PostMortem, *, now_iso: str) -> float:
    now = _parse_iso(now_iso)
    created = _parse_iso(record.created_at)
    return (now - created).total_seconds() / 86400.0


def is_visible(record: PostMortem, *, now_iso: str, window_days: int = VISIBILITY_WINDOW_DAYS) -> bool:
    """True if the record is within the visibility window from ``now_iso``."""
    return _age_days(record, now_iso=now_iso) <= window_days


def is_stale(
    record: PostMortem,
    *,
    now_iso: str,
    threshold_days: int = STALE_THRESHOLD_DAYS,
) -> bool:
    """A postmortem is stale only if it is still OPEN and older than the
    threshold. RESOLVED / WONT_FIX / IN_PROGRESS records are never stale."""
    if record.status is not PostMortemStatus.OPEN:
        return False
    return _age_days(record, now_iso=now_iso) > threshold_days


def severity_for_age(
    age_days: float,
    *,
    stale_threshold_days: int = STALE_THRESHOLD_DAYS,
    critical_age_days: int = CRITICAL_AGE_DAYS,
) -> PostMortemSeverity:
    """Bucket a record's age into a severity used by the runtime sub-check."""
    if age_days < stale_threshold_days:
        return PostMortemSeverity.INFO
    if age_days < critical_age_days:
        return PostMortemSeverity.WARN
    return PostMortemSeverity.CRITICAL


def now_utc_iso() -> str:
    """Helper for callers that don't already have a clock."""
    return datetime.now(timezone.utc).isoformat()
