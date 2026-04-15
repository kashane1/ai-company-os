"""Phase 1.3a — registry ↔ fixture reconciliation test.

Runs `reconcile_registry()` against the real `skills/registry.yaml`
and asserts zero drift. Every skill marked `fixture_status: passing`
must have:

- kind=validator: a loadable validator.py whose run() function
  produces the expected verdict for every fixture on disk (full
  replay).
- kind=agentic: fixture files on disk that parse cleanly as YAML
  and have non-empty `input` and `expected` fields (structural check).

Without this test, the "trust without validation" gap the deepening
review flagged would let a passing skill with broken or missing
fixtures silently ship. With this test, any future regression in
any passing skill's fixtures fails CI on every push.

This test is the hard gate that unlocks Phase 1 PRs 1b/1c/1d —
those PRs flip new skills to `passing`, and this test verifies the
flip is backed by real fixtures.
"""
from __future__ import annotations

from packages.tools.skills import loader as skills_loader
from packages.tools.skills.reconciliation import (
    ReconciliationReport,
    reconcile_registry,
)


def test_real_registry_passes_reconciliation() -> None:
    """Every `fixture_status: passing` skill in the real registry is clean."""
    report = reconcile_registry()
    assert isinstance(report, ReconciliationReport)
    assert report.passing_skills_checked > 0, (
        "Expected some passing skills in the real registry. "
        "Did every skill get downgraded to 'missing'?"
    )
    assert report.is_clean, (
        f"Registry has {len(report.drift_items)} drift item(s):\n"
        f"{report.format()}"
    )


def test_reconciliation_detects_missing_fixtures(monkeypatch, tmp_path):
    """A passing skill with no fixtures on disk triggers drift."""
    # Build a synthetic skill spec marked passing but with no fixtures.
    skills_root = tmp_path / "skills"
    (skills_root / "canonical" / "ghost-skill").mkdir(parents=True)
    monkeypatch.setattr(skills_loader, "_skills_root", lambda: skills_root)

    fake_spec = skills_loader.SkillSpec(
        id="ghost-skill",
        name="Ghost",
        kind="agentic",
        path="canonical/ghost-skill/skill.md",
        owner_agent="gtm",
        target_runtimes=("claude",),
        stage="active",
        fixture_status="passing",
        source="internal",
    )

    report = reconcile_registry(registry=[fake_spec])
    assert not report.is_clean
    assert any(item.drift_type == "missing_fixtures" for item in report.drift_items)
    assert report.drift_items[0].skill_id == "ghost-skill"


def test_reconciliation_detects_malformed_fixture(monkeypatch, tmp_path):
    """A fixture missing the `input` or `expected` field triggers drift."""
    import yaml

    skills_root = tmp_path / "skills"
    skill_dir = skills_root / "canonical" / "broken-skill"
    (skill_dir / "fixtures").mkdir(parents=True)
    (skill_dir / "fixtures" / "happy_path.yaml").write_text(
        yaml.safe_dump({"name": "happy", "description": "missing fields"})
    )
    monkeypatch.setattr(skills_loader, "_skills_root", lambda: skills_root)

    fake_spec = skills_loader.SkillSpec(
        id="broken-skill",
        name="Broken",
        kind="agentic",
        path="canonical/broken-skill/skill.md",
        owner_agent="gtm",
        target_runtimes=("claude",),
        stage="active",
        fixture_status="passing",
        source="internal",
    )

    report = reconcile_registry(registry=[fake_spec])
    assert not report.is_clean
    assert any(
        item.drift_type == "malformed_fixture" for item in report.drift_items
    )


def test_reconciliation_ignores_non_passing_skills(monkeypatch, tmp_path):
    """Skills marked missing/failing are not checked — they're already known bad."""
    skills_root = tmp_path / "skills"
    (skills_root / "canonical" / "missing-skill").mkdir(parents=True)
    monkeypatch.setattr(skills_loader, "_skills_root", lambda: skills_root)

    fake_spec = skills_loader.SkillSpec(
        id="missing-skill",
        name="Missing",
        kind="agentic",
        path="canonical/missing-skill/skill.md",
        owner_agent="gtm",
        target_runtimes=("claude",),
        stage="active",
        fixture_status="missing",
        source="internal",
    )

    report = reconcile_registry(registry=[fake_spec])
    assert report.is_clean  # missing skills are skipped
    assert report.passing_skills_checked == 0
