"""Atomic writer for ``skills/registry.yaml``.

Phase 0.5d.2 — every mutation to the registry must go through
``update_registry`` so writers can't leave the file in a truncated
state that a concurrent loader would see mid-parse.

Pattern: load current registry YAML → apply caller's mutator →
serialize to a sibling `.tmp` file in the same directory → fsync
→ `os.replace()` the tmp file over the real registry. `os.replace`
is atomic on POSIX (macOS APFS and Linux ext4), so a reader always
sees either the old file or the new one, never a partial write.

After a successful write this module also calls
``loader.invalidate_registry_cache()`` so in-process callers
immediately see the updated entries without having to wait for the
mtime-based cache key to flip.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from packages.tools.skills import loader as skills_loader


def _default_registry_path() -> Path:
    return Path(__file__).resolve().parents[3] / "skills" / "registry.yaml"


def update_registry(
    mutator: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    path: Path | None = None,
) -> dict[str, Any]:
    """Atomically apply ``mutator`` to the registry file.

    Args:
        mutator: Callable that receives the parsed registry dict
            (the whole YAML document, not just the ``skills`` list)
            and returns a replacement dict. The function is expected
            to be pure — it should not touch the filesystem itself.
        path: Optional override for the registry file path; defaults
            to the real ``skills/registry.yaml``. Primarily for tests.

    Returns:
        The new registry dict that was written.

    Raises:
        OSError: if the tmp-write or rename fails.

    Side effects:
        Invalidates the loader's in-process cache so the next
        ``load_registry()`` call re-reads from disk.
    """
    registry_path = (path or _default_registry_path()).resolve()
    current_raw = yaml.safe_load(registry_path.read_text()) or {}
    new_raw = mutator(current_raw)
    if not isinstance(new_raw, dict):
        raise TypeError(
            f"mutator must return a dict, got {type(new_raw).__name__}"
        )

    # Serialize BEFORE touching the filesystem so a mutator bug can't
    # leave a half-written tmp file behind.
    serialized = yaml.safe_dump(
        new_raw,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )

    # Write-then-rename for atomicity. The tmp file lives in the same
    # directory so `os.replace` stays within one filesystem.
    tmp_path = registry_path.with_suffix(registry_path.suffix + ".tmp")
    tmp_path.write_text(serialized, encoding="utf-8")
    # fsync the tmp file so the rename doesn't commit a write that
    # the OS hasn't durably flushed yet.
    with tmp_path.open("rb") as f:
        os.fsync(f.fileno())
    os.replace(tmp_path, registry_path)

    # Invalidate the loader cache so callers in the same process see
    # the new content without waiting for the mtime-based key to flip.
    skills_loader.invalidate_registry_cache()

    return new_raw


def set_fixture_status(
    skill_id: str,
    status: skills_loader.FixtureStatus,
    *,
    path: Path | None = None,
) -> dict[str, Any]:
    """Convenience helper — flip a single skill's ``fixture_status``.

    Used by Phase 1 PRs when promoting a skill to ``passing`` after
    writing its fixtures. Example::

        set_fixture_status("supervisor-goal-decomposition", "passing")
    """
    def _mutator(raw: dict[str, Any]) -> dict[str, Any]:
        skills_list = list(raw.get("skills", []))
        matched = False
        for entry in skills_list:
            if entry.get("id") == skill_id:
                entry["fixture_status"] = status
                matched = True
                break
        if not matched:
            raise KeyError(
                f"skill {skill_id!r} not found in registry; cannot set "
                f"fixture_status"
            )
        raw["skills"] = skills_list
        return raw

    return update_registry(_mutator, path=path)
