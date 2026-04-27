"""PostMortem retention policy tests (Phase 1)."""

from __future__ import annotations

from packages.policies.postmortem_retention import (
    is_stale,
    is_visible,
    severity_for_age,
)
from packages.schemas.postmortem import (
    PostMortem,
    PostMortemSeverity,
    PostMortemStatus,
)


def _make(*, status: PostMortemStatus = PostMortemStatus.OPEN, created_at: str) -> PostMortem:
    return PostMortem(
        id="x",
        created_at=created_at,
        updated_at=created_at,
        failure_code="c",
        lane="engineering",
        status=status,
    )


def test_is_stale_threshold_boundary():
    now = "2026-04-27T10:00:00+00:00"
    just_under = _make(created_at="2026-04-13T10:30:00+00:00")  # ~13.98 days old
    just_over = _make(created_at="2026-04-13T09:00:00+00:00")  # ~14.04 days old
    assert is_stale(just_under, now_iso=now, threshold_days=14) is False
    assert is_stale(just_over, now_iso=now, threshold_days=14) is True


def test_resolved_is_never_stale():
    resolved = _make(
        status=PostMortemStatus.RESOLVED,
        created_at="2025-01-01T10:00:00+00:00",
    )
    assert is_stale(resolved, now_iso="2026-04-27T10:00:00+00:00") is False


def test_in_progress_is_not_stale():
    record = _make(
        status=PostMortemStatus.IN_PROGRESS,
        created_at="2026-01-01T10:00:00+00:00",
    )
    assert is_stale(record, now_iso="2026-04-27T10:00:00+00:00") is False


def test_is_visible_window():
    now = "2026-04-27T10:00:00+00:00"
    inside = _make(created_at="2026-02-01T10:00:00+00:00")
    outside = _make(created_at="2025-12-01T10:00:00+00:00")
    assert is_visible(inside, now_iso=now, window_days=90) is True
    assert is_visible(outside, now_iso=now, window_days=90) is False


def test_severity_for_age_buckets():
    assert severity_for_age(5.0) is PostMortemSeverity.INFO
    assert severity_for_age(20.0) is PostMortemSeverity.WARN
    assert severity_for_age(45.0) is PostMortemSeverity.CRITICAL
