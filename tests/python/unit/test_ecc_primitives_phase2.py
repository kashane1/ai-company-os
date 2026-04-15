"""Phase 2a — unit tests for the new ECC primitives.

Covers:

- _safe_paths.safe_join happy path and rejection modes
- _serialization.json_safe_factory coercion matrix
- _state_writer.atomic_write_json + new_run_id + RunIdCollision
- followup_issue_writer.make_entry + write round trip
- registry_drift.check_drift on a synthetic repo
"""
from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path

import pytest
import yaml

from packages.tools.primitives import (
    _safe_paths,
    _serialization,
    _state_writer,
    followup_issue_writer,
    registry_drift,
)


# --- _safe_paths ---


def test_safe_join_happy(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.md").write_text("hi")
    resolved = _safe_paths.safe_join(tmp_path, "sub/a.md")
    assert resolved == (tmp_path / "sub" / "a.md").resolve()


def test_safe_join_rejects_absolute() -> None:
    with pytest.raises(_safe_paths.UnsafePathError):
        _safe_paths.safe_join(Path("/tmp"), "/etc/passwd")


def test_safe_join_rejects_escape(tmp_path: Path) -> None:
    with pytest.raises(_safe_paths.UnsafePathError):
        _safe_paths.safe_join(tmp_path, "../outside.md")


def test_safe_join_rejects_empty(tmp_path: Path) -> None:
    with pytest.raises(_safe_paths.UnsafePathError):
        _safe_paths.safe_join(tmp_path, "")


def test_is_adapter_path_positive() -> None:
    assert _safe_paths.is_adapter_path("adapters/claude/my-skill.md")


def test_is_adapter_path_negative() -> None:
    assert not _safe_paths.is_adapter_path("../etc/passwd")
    assert not _safe_paths.is_adapter_path("adapters/claude/../evil.md")
    assert not _safe_paths.is_adapter_path("")
    assert not _safe_paths.is_adapter_path(None)  # type: ignore[arg-type]


# --- _serialization ---


class _SampleEnum(Enum):
    A = "alpha"
    B = "beta"


def test_json_safe_factory_coerces_types() -> None:
    from dataclasses import asdict, dataclass

    @dataclass(frozen=True)
    class Sample:
        path: Path
        created: datetime
        kind: _SampleEnum
        tags: tuple[str, ...]

    sample = Sample(
        path=Path("/tmp/x.md"),
        created=datetime(2026, 4, 15, 12, 0, 0),
        kind=_SampleEnum.A,
        tags=("one", "two"),
    )
    out = asdict(sample, dict_factory=_serialization.json_safe_factory)
    # Must be JSON-serializable.
    dumped = json.dumps(out)
    loaded = json.loads(dumped)
    assert loaded["path"] == "/tmp/x.md"
    assert loaded["kind"] == "alpha"
    assert loaded["created"].startswith("2026-04-15T12:00:00")
    assert loaded["tags"] == ["one", "two"]


# --- _state_writer ---


def test_new_run_id_format() -> None:
    rid = _state_writer.new_run_id()
    assert len(rid) >= 20
    assert "Z-" in rid


def test_atomic_write_json_bootstraps_parent(tmp_path: Path) -> None:
    target = tmp_path / "health" / "skill-estate" / "report.json"
    _state_writer.atomic_write_json(target, {"hello": "world"})
    assert target.exists()
    data = json.loads(target.read_text())
    assert data["hello"] == "world"
    assert data["schema_version"] == "1"


def test_atomic_write_json_collision(tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    _state_writer.atomic_write_json(target, {"one": 1})
    with pytest.raises(_state_writer.RunIdCollision):
        _state_writer.atomic_write_json(target, {"two": 2})
    # Explicit overwrite is allowed.
    _state_writer.atomic_write_json(
        target, {"two": 2}, allow_overwrite=True
    )
    data = json.loads(target.read_text())
    assert data["two"] == 2


# --- followup_issue_writer ---


def test_followup_writer_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        followup_issue_writer, "_repo_root", lambda: tmp_path
    )
    entry = followup_issue_writer.make_entry(
        source="skill-stocktake",
        severity="warn",
        title="Orphan canonical ghost-skill",
        body="canonical/ghost-skill/skill.md has no registry entry",
        affected_files=("canonical/ghost-skill/skill.md",),
    )
    path = followup_issue_writer.write(entry)
    assert path.exists()
    assert path.parent == tmp_path / "state" / "followups"
    loaded = yaml.safe_load(path.read_text())
    assert loaded["source"] == "skill-stocktake"
    assert loaded["severity"] == "warn"
    assert loaded["title"].startswith("Orphan canonical")
    assert loaded["affected_files"] == ["canonical/ghost-skill/skill.md"]
    assert loaded["captured_at"]  # non-empty ISO timestamp


# --- registry_drift synthetic repo ---


def test_registry_drift_clean_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "skills" / "canonical" / "my-skill").mkdir(parents=True)
    (tmp_path / "skills" / "canonical" / "my-skill" / "skill.md").write_text("#")
    (tmp_path / "CLAUDE.md").write_text("# empty\n")
    registry = {
        "skills": [
            {
                "id": "my-skill",
                "name": "My Skill",
                "path": "canonical/my-skill/skill.md",
                "owner_agent": "any",
                "target_runtimes": ["claude"],
                "stage": "active",
                "kind": "agentic",
                "fixture_status": "missing",
                "source": "internal",
            }
        ]
    }
    reg_path = tmp_path / "skills" / "registry.yaml"
    reg_path.write_text(yaml.safe_dump(registry))

    monkeypatch.setattr(registry_drift, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        registry_drift, "_skills_root", lambda: tmp_path / "skills"
    )
    monkeypatch.setattr(
        registry_drift, "_claude_md_path", lambda: tmp_path / "CLAUDE.md"
    )
    report = registry_drift.check_drift(registry_path=reg_path)
    assert report.drift_items == ()
    assert report.registry_entries_checked == 1
