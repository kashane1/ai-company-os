"""PostMortem schema tests (Phase 1)."""

from __future__ import annotations

from packages.schemas.postmortem import (
    PostMortem,
    PostMortemSeverity,
    PostMortemStatus,
    RootCauseCategory,
)


def _make(**overrides) -> PostMortem:
    base: dict = dict(
        id="abc1234567",
        created_at="2026-04-27T10:00:00+00:00",
        updated_at="2026-04-27T10:00:00+00:00",
        failure_code="lint_failed",
        lane="engineering",
    )
    base.update(overrides)
    return PostMortem(**base)


def test_defaults_match_plan():
    pm = _make()
    assert pm.status is PostMortemStatus.OPEN
    assert pm.severity is PostMortemSeverity.WARN
    assert pm.root_cause_category is RootCauseCategory.UNKNOWN
    assert pm.schema_version == "1"
    assert pm.task_id is None
    assert pm.owner is None


def test_to_dict_round_trip():
    pm = _make(
        owner="founder",
        root_cause_category=RootCauseCategory.POLICY_MISS,
        status=PostMortemStatus.IN_PROGRESS,
        severity=PostMortemSeverity.CRITICAL,
    )
    payload = pm.to_dict()
    assert payload["status"] == "in-progress"
    assert payload["severity"] == "critical"
    assert payload["root_cause_category"] == "policy-miss"
    restored = PostMortem.from_dict(payload)
    assert restored == pm


def test_post_init_redacts_notes_and_remediation():
    pm = _make(
        notes="leaked sk-abcdefghij0123456789ABCDEF",
        remediation_action="bearer ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    )
    assert "sk-abcdefghij" not in pm.notes
    assert "ABCDEFGHIJKLMNOPQRSTUV" not in pm.remediation_action


def test_post_init_redacts_user_dir_in_fixture_path():
    pm = _make(fixture_path="/Users/simons/ai-company-os/state/artifacts/x.json")
    assert "simons" not in (pm.fixture_path or "")
    assert "[REDACTED-USER]" in (pm.fixture_path or "")


def test_post_init_redacts_excerpt():
    pm = _make(excerpt_redacted="token=sk-abcdefghij0123456789ABCDEF")
    assert "sk-abcdefghij" not in (pm.excerpt_redacted or "")


def test_optional_fields_default_to_none_not_empty_string():
    pm = _make()
    assert pm.excerpt_redacted is None
    assert pm.redaction_hits is None
    assert pm.fixture_path is None
