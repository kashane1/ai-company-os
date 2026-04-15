"""Registry-drift detection primitive (ECC Gap Recommendations Phase 2a).

Checks that the `skill-stocktake` validator composes. Three drift
types ship in the first landing (per deepening finding #3; the
originally proposed seven drift types were cut to three because
four of them are either subsumed by the other three or already
enforced by `loader.py` at registry-load time):

1. `orphan_canonical`  — a file at `skills/canonical/<id>/skill.md`
   with no registry entry whose `path` points at it.
2. `dangling_project_skill` — a registry entry with
   `project_skill: <path>` where the path does not exist.
3. `trigger_phrase_drift` — a CLAUDE.md trigger-phrase line that
   references `skills/adapters/claude/<id>.md` but the adapter file
   does not exist. Targets under `docs/` are allowed (see
   `CLAUDE.md:74` which deliberately points at
   `docs/codex-cloud-dispatch.md`) and are NOT flagged.

All paths are resolved via `_safe_paths.safe_join()` against the
skills root or repo root so a malicious registry entry cannot read
outside its sandbox.

Per the primitives convention:
- Stateless module-level.
- No top-level I/O (registry parse happens inside `check_drift()`).
- Typed returns (`StocktakeReport` / `DriftItem` frozen dataclasses).
- No imports from `packages/tools/skills/`.

Validator shape:

    def run(payload: dict) -> dict

is exported for the skill-loader path in `skill-stocktake/validator.py`.
The validator returns `dataclasses.asdict(report)` via the JSON-safe
factory so `json.dumps()` is safe on the result.
"""
from __future__ import annotations

import functools
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from packages.tools.primitives._safe_paths import UnsafePathError, safe_join
from packages.tools.primitives._serialization import json_safe_factory

DriftType = Literal[
    "orphan_canonical",
    "dangling_project_skill",
    "trigger_phrase_drift",
]


@dataclass(frozen=True)
class DriftItem:
    """One drift entry in a stocktake report."""

    drift_type: DriftType
    detail: str
    affected_path: str
    skill_id: str | None = None


@dataclass(frozen=True)
class StocktakeReport:
    """Full stocktake report (per todo 016: includes schema_version +
    known_drift baseline tags so Phase 2a can ship with pre-existing
    drift tagged and not re-flagged on every run)."""

    schema_version: str
    registry_entries_checked: int
    drift_items: tuple[DriftItem, ...]
    known_drift: tuple[str, ...]  # drift_item ids known to be pre-existing
    tokenizer: str | None = None  # unused; reserved for budget-report parity


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _skills_root() -> Path:
    return _repo_root() / "skills"


def _claude_md_path() -> Path:
    return _repo_root() / "CLAUDE.md"


def _load_registry_yaml(registry_path: Path | None) -> list[dict]:
    """Parse the registry YAML directly.

    `skill-stocktake` intentionally does NOT go through
    `packages.tools.skills.loader.load_registry()` because:

    - The loader caches on (mtime, inode, size) which is stale across
      synthetic-fixture tests that use `monkeypatch`.
    - The loader's path-traversal validator raises on malformed
      entries, but stocktake is SPECIFICALLY the tool that detects
      those entries — it must see them to flag them.

    Callers that need the strict loader path should invoke
    `load_registry()` separately.
    """
    path = registry_path or (_skills_root() / "registry.yaml")
    raw = yaml.safe_load(path.read_text()) or {}
    return list(raw.get("skills", []) or [])


def _orphan_canonical_drift(
    skills_root: Path, registry_entries: list[dict]
) -> list[DriftItem]:
    canonical_dir = skills_root / "canonical"
    if not canonical_dir.is_dir():
        return []
    registered_paths = {
        (entry.get("path") or "").strip()
        for entry in registry_entries
    }
    drift: list[DriftItem] = []
    for skill_md in canonical_dir.glob("*/skill.md"):
        rel = f"canonical/{skill_md.parent.name}/skill.md"
        if rel not in registered_paths:
            drift.append(
                DriftItem(
                    drift_type="orphan_canonical",
                    detail=(
                        f"canonical file {rel} has no registry entry; "
                        "either add a registry row or delete the file"
                    ),
                    affected_path=rel,
                    skill_id=skill_md.parent.name,
                )
            )
    return drift


def _dangling_project_skill_drift(
    skills_root: Path,
    registry_entries: list[dict],
    repo_root: Path,
) -> list[DriftItem]:
    drift: list[DriftItem] = []
    for entry in registry_entries:
        project_skill = entry.get("project_skill")
        if not project_skill:
            continue
        full = repo_root / project_skill
        if not full.exists():
            drift.append(
                DriftItem(
                    drift_type="dangling_project_skill",
                    detail=(
                        f"registry entry {entry.get('id')!r} points at "
                        f"{project_skill} which does not exist on disk"
                    ),
                    affected_path=project_skill,
                    skill_id=entry.get("id"),
                )
            )
    return drift


# Trigger-phrase lines look like:
#   - "phrase" / "phrase 2" → `skills/adapters/claude/<id>.md`
# We want to extract the target path (the single ` … ` span after the
# arrow). Docs targets like `docs/codex-cloud-dispatch.md` are
# deliberately valid.
#
# The pattern is lazily compiled via lru_cache to respect the
# primitives convention that forbids module-level `re.compile()`.
@functools.lru_cache(maxsize=1)
def _trigger_target_re() -> re.Pattern[str]:
    return re.compile(r"→\s*`([^`]+)`")


def _trigger_phrase_drift(
    skills_root: Path, claude_md_path: Path
) -> list[DriftItem]:
    if not claude_md_path.exists():
        return []
    text = claude_md_path.read_text()
    drift: list[DriftItem] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        match = _trigger_target_re().search(stripped)
        if not match:
            continue
        target = match.group(1).strip()
        if target.startswith("docs/"):
            continue  # docs targets are valid
        if not target.startswith("skills/adapters/"):
            continue  # other targets not in scope for this check
        # The target is relative to the repo root, not the skills root.
        # Strip the `skills/` prefix and resolve under skills_root.
        rel_to_skills = target[len("skills/"):]
        try:
            resolved = safe_join(skills_root, rel_to_skills)
        except UnsafePathError:
            drift.append(
                DriftItem(
                    drift_type="trigger_phrase_drift",
                    detail=(
                        f"CLAUDE.md trigger phrase target {target!r} is "
                        "an unsafe path (traversal or empty)"
                    ),
                    affected_path=target,
                    skill_id=None,
                )
            )
            continue
        if not resolved.exists():
            drift.append(
                DriftItem(
                    drift_type="trigger_phrase_drift",
                    detail=(
                        f"CLAUDE.md trigger phrase target {target!r} "
                        "does not exist on disk"
                    ),
                    affected_path=target,
                    skill_id=None,
                )
            )
    return drift


def check_drift(
    registry_path: Path | None = None,
    *,
    known_drift: tuple[str, ...] = (),
) -> StocktakeReport:
    """Run all three MVP drift checks and return a StocktakeReport.

    Pure-function contract: given the same repo state + registry it
    returns the same report. No I/O beyond reading the registry,
    scanning `skills/canonical/**/skill.md`, and reading CLAUDE.md.
    """
    repo_root = _repo_root()
    skills_root = _skills_root()
    claude_md = _claude_md_path()
    entries = _load_registry_yaml(registry_path)

    drift: list[DriftItem] = []
    drift.extend(_orphan_canonical_drift(skills_root, entries))
    drift.extend(
        _dangling_project_skill_drift(skills_root, entries, repo_root)
    )
    drift.extend(_trigger_phrase_drift(skills_root, claude_md))

    return StocktakeReport(
        schema_version="1",
        registry_entries_checked=len(entries),
        drift_items=tuple(drift),
        known_drift=tuple(known_drift),
    )


def run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validator entry point for the skill-loader path.

    Returns a `dict[str, Any]` with a `verdict` key matching the
    existing convention (see `approval-token-audit/validator.py:run`
    and sibling modules). Internally constructs the typed
    `StocktakeReport`, then serializes via `json_safe_factory`.
    """
    payload = payload or {}
    registry_path = payload.get("registry_path")
    if isinstance(registry_path, str):
        registry_path = Path(registry_path)
    known_drift = tuple(payload.get("known_drift", ()))
    report = check_drift(registry_path=registry_path, known_drift=known_drift)
    report_dict = asdict(report, dict_factory=json_safe_factory)
    verdict = "pass" if not report.drift_items else "fail"
    return {
        "verdict": verdict,
        "report": report_dict,
        "drift_count": len(report.drift_items),
    }
