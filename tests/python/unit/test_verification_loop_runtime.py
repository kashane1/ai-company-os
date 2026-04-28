"""verification-loop-runtime runner tests (Phase 4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, ensure_runtime_directories
from packages.db.postmortem_store import PostMortemStore
from packages.schemas.postmortem import (
    PostMortem,
    PostMortemStatus,
)
from packages.tools.primitives import verification_loop_runtime_runner as rt


@pytest.fixture
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    return tmp_path


def _pm(id: str, *, status: PostMortemStatus = PostMortemStatus.OPEN, created_at: str = "2026-04-27T10:00:00+00:00") -> PostMortem:
    return PostMortem(
        id=id,
        created_at=created_at,
        updated_at=created_at,
        failure_code="lint_failed",
        lane="engineering",
        status=status,
    )


def test_empty_store_returns_pass_with_info(isolated_state: Path):
    report = rt.run(now_iso="2026-04-27T10:00:00+00:00")
    assert report.verdict == "pass"
    assert len(report.sub_checks) == 1
    assert report.sub_checks[0].severity == "info"
    assert "No open postmortems" in report.sub_checks[0].summary


def test_fresh_open_postmortem_does_not_warn(isolated_state: Path):
    PostMortemStore().save(_pm("fresh11111", created_at="2026-04-26T10:00:00+00:00"))
    report = rt.run(now_iso="2026-04-27T10:00:00+00:00")
    assert report.verdict == "pass"
    assert report.sub_checks[0].severity == "info"


def test_stale_open_postmortem_triggers_soft_fail(isolated_state: Path):
    PostMortemStore().save(_pm("staleopen1", created_at="2026-04-01T10:00:00+00:00"))
    report = rt.run(now_iso="2026-04-27T10:00:00+00:00", threshold_days=14)
    assert report.verdict == "soft_fail"
    sub = report.sub_checks[0]
    assert sub.severity == "warn"
    assert "staleopen1" in sub.detail["stale_ids"]


def test_resolved_postmortem_without_audit_triggers_warn(isolated_state: Path):
    """H1 mitigation: a RESOLVED postmortem with no audit-log entry is suspicious."""
    store = PostMortemStore()
    store.save(_pm("ghost00000", status=PostMortemStatus.RESOLVED))
    report = rt.run(now_iso="2026-04-27T10:00:00+00:00")
    sub = report.sub_checks[0]
    assert sub.severity == "warn"
    assert "ghost00000" in sub.detail["resolved_without_audit_ids"]


def test_resolved_postmortem_with_audit_does_not_warn(isolated_state: Path):
    """RESOLVED via update_status writes audit; should not warn."""
    store = PostMortemStore()
    store.save(_pm("legit11111"))
    store.update_status(
        "legit11111",
        status=PostMortemStatus.RESOLVED,
        now_iso="2026-04-27T10:00:00+00:00",
        caller_identity="founder@local",
    )
    report = rt.run(now_iso="2026-04-27T10:00:00+00:00")
    assert report.verdict == "pass"
    assert report.sub_checks[0].severity == "info"


def test_runner_never_raises_on_corrupt_input(isolated_state: Path):
    paths = ensure_runtime_directories()
    (paths.postmortems_root / "corrupt.json").write_text("{not json")
    report = rt.run(now_iso="2026-04-27T10:00:00+00:00")
    # Corrupt files are skipped; runner does not crash.
    assert report.verdict in ("pass", "soft_fail")


def test_critical_age_is_surfaced_in_detail(isolated_state: Path):
    PostMortemStore().save(_pm("ancient111", created_at="2026-02-01T10:00:00+00:00"))
    report = rt.run(now_iso="2026-04-27T10:00:00+00:00")
    sub = report.sub_checks[0]
    assert sub.severity == "warn"
    assert "ancient111" in sub.detail["stale_over_critical_ids"]
