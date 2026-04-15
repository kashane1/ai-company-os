"""Phase 0.5d.2 — atomic registry writer tests."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from packages.tools.skills import loader as skills_loader
from packages.tools.skills.registry_writer import (
    set_fixture_status,
    update_registry,
)


@pytest.fixture
def temp_registry(tmp_path: Path) -> Path:
    registry = {
        "skills": [
            {
                "id": "foo",
                "name": "Foo",
                "path": "canonical/foo/skill.md",
                "owner_agent": "gtm",
                "target_runtimes": ["claude"],
                "stage": "active",
                "kind": "validator",
                "fixture_status": "missing",
                "source": "internal",
            },
            {
                "id": "bar",
                "name": "Bar",
                "path": "canonical/bar/skill.md",
                "owner_agent": "gtm",
                "target_runtimes": ["claude"],
                "stage": "active",
                "kind": "agentic",
                "fixture_status": "passing",
                "source": "internal",
            },
        ]
    }
    registry_file = tmp_path / "registry.yaml"
    registry_file.write_text(yaml.safe_dump(registry))
    return registry_file


def test_update_registry_is_atomic(temp_registry: Path) -> None:
    """After an update, the file exists and parses cleanly."""
    def mutator(raw: dict) -> dict:
        # Flip foo to passing.
        for entry in raw["skills"]:
            if entry["id"] == "foo":
                entry["fixture_status"] = "passing"
        return raw

    result = update_registry(mutator, path=temp_registry)
    assert result["skills"][0]["fixture_status"] == "passing"

    # Re-read from disk — the tmp file must be gone, the real file must
    # contain the new content.
    assert not temp_registry.with_suffix(".yaml.tmp").exists()
    reloaded = yaml.safe_load(temp_registry.read_text())
    assert reloaded["skills"][0]["fixture_status"] == "passing"


def test_update_registry_preserves_other_entries(temp_registry: Path) -> None:
    """A targeted mutation doesn't disturb sibling entries."""
    def mutator(raw: dict) -> dict:
        for entry in raw["skills"]:
            if entry["id"] == "foo":
                entry["fixture_status"] = "passing"
        return raw

    update_registry(mutator, path=temp_registry)
    reloaded = yaml.safe_load(temp_registry.read_text())
    bar = [e for e in reloaded["skills"] if e["id"] == "bar"][0]
    assert bar["fixture_status"] == "passing"
    assert bar["kind"] == "agentic"


def test_set_fixture_status_convenience_helper(temp_registry: Path) -> None:
    set_fixture_status("foo", "passing", path=temp_registry)
    reloaded = yaml.safe_load(temp_registry.read_text())
    foo = [e for e in reloaded["skills"] if e["id"] == "foo"][0]
    assert foo["fixture_status"] == "passing"


def test_set_fixture_status_raises_on_missing_skill(temp_registry: Path) -> None:
    with pytest.raises(KeyError, match="nonexistent"):
        set_fixture_status("nonexistent", "passing", path=temp_registry)


def test_update_registry_invalidates_loader_cache(temp_registry: Path) -> None:
    """In-process loader callers see the updated entry without waiting for mtime."""
    # Prime the loader cache with the initial content.
    before = skills_loader.load_registry(path=temp_registry)
    assert any(s.fixture_status == "missing" for s in before if s.id == "foo")

    # Mutate via the writer.
    set_fixture_status("foo", "passing", path=temp_registry)

    # A second loader call in the SAME process must see the new value,
    # not a stale cache entry keyed on the pre-write mtime.
    after = skills_loader.load_registry(path=temp_registry)
    foo = [s for s in after if s.id == "foo"][0]
    assert foo.fixture_status == "passing"


def test_update_registry_rejects_non_dict_mutator(temp_registry: Path) -> None:
    with pytest.raises(TypeError, match="mutator must return a dict"):
        update_registry(lambda raw: ["not", "a", "dict"], path=temp_registry)  # type: ignore[return-value]
