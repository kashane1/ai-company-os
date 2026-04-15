"""Phase 0.5 — tests for packages/tools/skills/loader.py."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from packages.tools.skills import loader as skills_loader


@pytest.fixture()
def fake_registry(tmp_path: Path) -> Path:
    skills_root = tmp_path / "skills"
    canonical = skills_root / "canonical"
    canonical.mkdir(parents=True)

    # Validator skill with passing fixtures.
    ok_dir = canonical / "ok-validator"
    ok_dir.mkdir()
    (ok_dir / "validator.py").write_text(
        "def run(payload):\n    return {'ok': True, 'payload': payload}\n"
    )

    # Validator skill that is missing fixtures (status=missing).
    unrated_dir = canonical / "unrated-validator"
    unrated_dir.mkdir()
    (unrated_dir / "validator.py").write_text(
        "def run(payload):\n    return payload\n"
    )

    # Agentic skill, passing.
    agentic_dir = canonical / "ok-agentic"
    agentic_dir.mkdir()
    (agentic_dir / "contract.yaml").write_text("outputs:\n  - name: rewrite\n")

    registry = {
        "skills": [
            {
                "id": "ok-validator",
                "name": "OK Validator",
                "path": "canonical/ok-validator/skill.md",
                "owner_agent": "gtm",
                "target_runtimes": ["claude"],
                "stage": "active",
                "kind": "validator",
                "fixture_status": "passing",
                "source": "internal",
            },
            {
                "id": "unrated-validator",
                "name": "Unrated Validator",
                "path": "canonical/unrated-validator/skill.md",
                "owner_agent": "gtm",
                "target_runtimes": ["claude"],
                "stage": "active",
                "kind": "validator",
                "fixture_status": "missing",
                "source": "internal",
            },
            {
                "id": "ok-agentic",
                "name": "OK Agentic",
                "path": "canonical/ok-agentic/skill.md",
                "owner_agent": "gtm",
                "target_runtimes": ["claude"],
                "stage": "active",
                "kind": "agentic",
                "fixture_status": "passing",
                "source": "internal",
            },
        ]
    }
    (skills_root / "registry.yaml").write_text(yaml.safe_dump(registry))
    return skills_root


def _patch_loader(monkeypatch, skills_root: Path) -> None:
    monkeypatch.setattr(
        skills_loader, "_registry_path", lambda: skills_root / "registry.yaml"
    )
    monkeypatch.setattr(skills_loader, "_skills_root", lambda: skills_root)


def test_load_validator_autonomous_ok(monkeypatch, fake_registry):
    _patch_loader(monkeypatch, fake_registry)
    handle = skills_loader.load_validator("ok-validator", mode="autonomous")
    assert handle.spec.kind == "validator"
    assert handle.run({"x": 1}) == {"ok": True, "payload": {"x": 1}}


def test_load_validator_autonomous_refuses_unrated(monkeypatch, fake_registry):
    _patch_loader(monkeypatch, fake_registry)
    with pytest.raises(skills_loader.SkillNotEvaluated):
        skills_loader.load_validator("unrated-validator", mode="autonomous")


def test_load_validator_manual_allows_unrated(monkeypatch, fake_registry):
    _patch_loader(monkeypatch, fake_registry)
    handle = skills_loader.load_validator("unrated-validator", mode="manual")
    assert handle.spec.fixture_status == "missing"


def test_load_validator_refuses_agentic_kind(monkeypatch, fake_registry):
    _patch_loader(monkeypatch, fake_registry)
    with pytest.raises(skills_loader.SkillKindMismatch):
        skills_loader.load_validator("ok-agentic")


def test_load_agentic_refuses_synchronous(monkeypatch, fake_registry):
    _patch_loader(monkeypatch, fake_registry)
    with pytest.raises(skills_loader.SkillKindMismatch):
        skills_loader.load_agentic("ok-agentic", synchronous=True)


def test_load_agentic_refuses_validator_kind(monkeypatch, fake_registry):
    _patch_loader(monkeypatch, fake_registry)
    with pytest.raises(skills_loader.SkillKindMismatch):
        skills_loader.load_agentic("ok-validator")


def test_load_agentic_autonomous_ok(monkeypatch, fake_registry):
    _patch_loader(monkeypatch, fake_registry)
    handle = skills_loader.load_agentic("ok-agentic", mode="autonomous")
    assert handle.spec.id == "ok-agentic"
    assert handle.prompt_contract == {"outputs": [{"name": "rewrite"}]}
    assert handle.unrated is False


def test_load_missing_skill_raises(monkeypatch, fake_registry):
    _patch_loader(monkeypatch, fake_registry)
    with pytest.raises(skills_loader.SkillNotFound):
        skills_loader.load_validator("nope")


def test_real_registry_loads_without_crash():
    """Phase 0.0 regression guard.

    Before 2026-04-14, the real `skills/registry.yaml` contained a
    `fixture_status: planned` literal that crashed `load_registry()` on
    every call because `planned` isn't in the loader's validated set
    (`passing`|`failing`|`missing`). Every downstream caller was broken.

    This test asserts the real registry loads cleanly and returns
    non-empty. If someone reintroduces an invalid fixture_status, this
    test fails fast instead of every worker crashing at dispatch time.
    """
    specs = skills_loader.load_registry()
    assert len(specs) > 0
    # No entry should have a fixture_status outside the validated literal set.
    valid = {"passing", "failing", "missing"}
    for spec in specs:
        assert spec.fixture_status in valid, (
            f"skill {spec.id!r} has invalid fixture_status "
            f"{spec.fixture_status!r}; must be one of {valid}"
        )


def test_self_evolvable_defaults_to_false_for_existing_skills():
    """Phase 0.5d.1 — X10 allowlist model, default-safe.

    Every existing skill in the registry should have
    `self_evolvable=False` (not opted into skill-evolution). Only
    explicitly opted-in skills can be evolved by the Phase 3 worker.
    """
    specs = skills_loader.load_registry()
    assert all(not spec.self_evolvable for spec in specs), (
        "No existing skill should be self_evolvable without explicit "
        "human review. Only skills flipped to `self_evolvable: true` "
        "in registry.yaml by a human-authored PR may be evolved."
    )


def test_self_evolvable_parses_from_registry(tmp_path):
    """self_evolvable: true parses correctly when set."""
    skills_root = tmp_path / "skills"
    (skills_root / "canonical" / "test-skill").mkdir(parents=True)
    (skills_root / "canonical" / "test-skill" / "validator.py").write_text(
        "def run(payload):\n    return {'ok': True}\n"
    )
    (skills_root / "registry.yaml").write_text(
        yaml.safe_dump(
            {
                "skills": [
                    {
                        "id": "test-skill",
                        "name": "Test",
                        "path": "canonical/test-skill/skill.md",
                        "owner_agent": "gtm",
                        "target_runtimes": ["claude"],
                        "stage": "active",
                        "kind": "validator",
                        "fixture_status": "passing",
                        "source": "internal",
                        "self_evolvable": True,
                    }
                ]
            }
        )
    )
    specs = skills_loader.load_registry(path=skills_root / "registry.yaml")
    assert len(specs) == 1
    assert specs[0].self_evolvable is True


def test_adapter_path_traversal_guard(tmp_path):
    """Phase 0.5d.1 — malicious registry entry must not resolve `../../etc/passwd`.

    The loader's _ADAPTER_PATH_PATTERN rejects any adapters[] value
    that doesn't match `^skills/adapters/[a-z]+/[a-z0-9_-]+\\.md$`.
    """
    skills_root = tmp_path / "skills"
    (skills_root / "canonical" / "test-skill").mkdir(parents=True)

    evil_paths = [
        "../../../etc/passwd",
        "adapters/../../etc/passwd",
        "adapters/claude/../../../secrets.md",
        "/etc/passwd",
        "file:///etc/passwd",
        "adapters/claude/good.md/../../bad",
        "skills/adapters/claude/test.md",  # absolute-ish: must be relative to skills/
    ]

    for evil in evil_paths:
        (skills_root / "registry.yaml").write_text(
            yaml.safe_dump(
                {
                    "skills": [
                        {
                            "id": "test-skill",
                            "name": "Test",
                            "path": "canonical/test-skill/skill.md",
                            "owner_agent": "gtm",
                            "target_runtimes": ["claude"],
                            "stage": "active",
                            "kind": "agentic",
                            "fixture_status": "missing",
                            "source": "internal",
                            "adapters": {"claude": evil},
                        }
                    ]
                }
            )
        )
        with pytest.raises(skills_loader.SkillLoadError, match="path-traversal guard"):
            skills_loader.load_registry(path=skills_root / "registry.yaml")


def test_adapter_path_guard_accepts_valid_entries(tmp_path):
    """Well-formed adapter paths load cleanly."""
    skills_root = tmp_path / "skills"
    (skills_root / "canonical" / "test-skill").mkdir(parents=True)

    valid_paths = [
        "adapters/claude/test-skill.md",
        "adapters/codex/test-skill.md",
        "adapters/acp/test-skill.md",
        "adapters/claude/some_long_name.md",
    ]

    for good in valid_paths:
        (skills_root / "registry.yaml").write_text(
            yaml.safe_dump(
                {
                    "skills": [
                        {
                            "id": "test-skill",
                            "name": "Test",
                            "path": "canonical/test-skill/skill.md",
                            "owner_agent": "gtm",
                            "target_runtimes": ["claude"],
                            "stage": "active",
                            "kind": "agentic",
                            "fixture_status": "missing",
                            "source": "internal",
                            "adapters": {"claude": good},
                        }
                    ]
                }
            )
        )
        specs = skills_loader.load_registry(path=skills_root / "registry.yaml")
        assert specs[0].adapters["claude"] == good
