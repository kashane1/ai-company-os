"""Phase 0.5e — dual-layout fixture discovery tests.

Verifies that `packages.tools.skills.loader.discover_fixtures` correctly
resolves fixtures for BOTH canonical layouts per
`docs/adr/2026-04-14-canonical-skill-layout.md`:

1. Per-skill directory layout (Phase 2.5+).
2. Flat Phase 0 layout with `<skill-id>.fixtures.yaml` sibling.
3. Flat Phase 0 layout with shared `fixtures/<skill-id>/` subdir.

D9 hardening: this test uses synthetic fixtures at
`tests/python/fixtures/_discovery/`, NOT any real
`skills/canonical/*/fixtures/` path, so Phase 0.5e has no forward
dependency on Phase 1's fixture writes.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from packages.tools.skills import loader as skills_loader


@pytest.fixture
def synthetic_skills_root(tmp_path: Path, monkeypatch) -> Path:
    """Isolated skills/ tree with both canonical layouts populated."""
    root = tmp_path / "skills"
    canonical = root / "canonical"

    # Layout 1: per-skill directory with fixtures/.
    dir_skill = canonical / "dir-layout-skill"
    (dir_skill / "fixtures").mkdir(parents=True)
    (dir_skill / "skill.md").write_text("# dir-layout-skill\n")
    (dir_skill / "fixtures" / "happy_path.yaml").write_text(
        yaml.safe_dump({"input": {"x": 1}, "expected": {"ok": True}})
    )
    (dir_skill / "fixtures" / "boundary.yaml").write_text(
        yaml.safe_dump({"input": {"x": 0}, "expected": {"ok": True}})
    )
    (dir_skill / "fixtures" / "adversarial.yaml").write_text(
        yaml.safe_dump({"input": {"x": -1}, "expected": {"ok": False}})
    )

    # Layout 2: flat Phase 0 layout with sibling fixture file.
    (canonical / "shared").mkdir()
    (canonical / "shared" / "flat-layout-skill.md").write_text(
        "# flat-layout-skill\n"
    )
    (canonical / "shared" / "flat-layout-skill.fixtures.yaml").write_text(
        yaml.safe_dump(
            [
                {"name": "happy", "input": {"a": 1}, "expected": {"ok": True}},
                {"name": "boundary", "input": {"a": 0}, "expected": {"ok": True}},
                {"name": "adversarial", "input": {"a": -1}, "expected": {"ok": False}},
            ]
        )
    )

    # Layout 3: shared fixtures/<skill-id>/ subdirectory.
    shared_fixture_skill = canonical / "shared"
    (shared_fixture_skill / "shared-fixtures-skill.md").write_text(
        "# shared-fixtures-skill\n"
    )
    (shared_fixture_skill / "fixtures" / "shared-fixtures-skill").mkdir(parents=True)
    (shared_fixture_skill / "fixtures" / "shared-fixtures-skill" / "case1.yaml").write_text(
        yaml.safe_dump({"input": {"y": 1}, "expected": {"ok": True}})
    )

    # Patch the loader to point at this synthetic tree.
    monkeypatch.setattr(skills_loader, "_skills_root", lambda: root)
    return root


def _make_spec(skill_id: str, path: str, kind: str = "validator") -> skills_loader.SkillSpec:
    return skills_loader.SkillSpec(
        id=skill_id,
        name=skill_id,
        kind=kind,  # type: ignore[arg-type]
        path=path,
        owner_agent="gtm",
        target_runtimes=("claude",),
        stage="active",
        fixture_status="passing",
        source="internal",
    )


def test_discover_fixtures_dir_layout(synthetic_skills_root: Path) -> None:
    spec = _make_spec(
        "dir-layout-skill",
        "canonical/dir-layout-skill/skill.md",
    )
    fixtures = skills_loader.discover_fixtures(spec)
    names = sorted(p.name for p in fixtures)
    assert names == ["adversarial.yaml", "boundary.yaml", "happy_path.yaml"]


def test_discover_fixtures_flat_layout_sibling_file(
    synthetic_skills_root: Path,
) -> None:
    spec = _make_spec(
        "flat-layout-skill",
        "canonical/shared/flat-layout-skill.md",
    )
    fixtures = skills_loader.discover_fixtures(spec)
    assert len(fixtures) == 1
    assert fixtures[0].name == "flat-layout-skill.fixtures.yaml"


def test_discover_fixtures_flat_layout_shared_subdir(
    synthetic_skills_root: Path,
) -> None:
    spec = _make_spec(
        "shared-fixtures-skill",
        "canonical/shared/shared-fixtures-skill.md",
    )
    fixtures = skills_loader.discover_fixtures(spec)
    names = [p.name for p in fixtures]
    assert "case1.yaml" in names


def test_discover_fixtures_empty_when_none_present(
    synthetic_skills_root: Path,
) -> None:
    """A skill with no fixtures at all returns []."""
    spec = _make_spec(
        "nonexistent-skill",
        "canonical/nonexistent-skill/skill.md",
    )
    assert skills_loader.discover_fixtures(spec) == []


def test_discover_fixtures_with_missing_path_field(
    synthetic_skills_root: Path,
) -> None:
    """Legacy skills without a `path:` field still get the dir-layout check."""
    spec = _make_spec("dir-layout-skill", "")
    fixtures = skills_loader.discover_fixtures(spec)
    # Dir-layout check fires on the skill id, even without path.
    assert len(fixtures) == 3
