"""Skill loader with autonomous/manual gate (Phase 0.5).

Enforces two invariants:

1. A skill with ``kind: validator`` is pure Python (no LLM round-trip) and is
   safe to call from synchronous hot paths (``ControlPlaneService``,
   ``release_readiness.py``). It must not attempt an LLM call.
2. A skill with ``kind: agentic`` is LLM-backed. It must only be loaded from
   contexts that are already LLM-driven. Synchronous callers are refused.

The loader also enforces the eval gate: ``mode="autonomous"`` requires
``fixture_status == passing`` in ``skills/registry.yaml``. ``mode="manual"``
allows unrated skills but tags every output with ``skill_unrated=true``.
"""

from __future__ import annotations

import functools
import importlib.util
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

import yaml


SkillKind = Literal["validator", "agentic"]
SkillMode = Literal["autonomous", "manual"]
FixtureStatus = Literal["passing", "failing", "missing"]

# Phase 0.5d.1: path-traversal guard on registry adapter entries.
# Any `adapters:` map value must match this pattern to prevent a
# malicious registry entry from resolving `../../../etc/passwd`.
#
# The registry stores adapter paths as `adapters/<runtime>/<skill-id>.md`
# — the paths are relative to `skills/`, not the repo root, because the
# loader resolves them via `_skills_root() / adapter_path`. The runtime
# slug and skill id must both be kebab-case identifiers with no dots or
# slashes beyond the two structural separators.
_ADAPTER_PATH_PATTERN = re.compile(
    r"^adapters/[a-z][a-z0-9_]*/[a-z0-9][a-z0-9_-]*\.md$"
)


class SkillLoadError(RuntimeError):
    pass


class SkillKindMismatch(SkillLoadError):
    pass


class SkillNotEvaluated(SkillLoadError):
    pass


class SkillNotFound(SkillLoadError):
    pass


@dataclass(frozen=True)
class SkillSpec:
    id: str
    name: str
    kind: SkillKind
    path: str
    owner_agent: str
    target_runtimes: tuple[str, ...]
    stage: str
    fixture_status: FixtureStatus
    source: str  # "internal" or "external:<repo>@<commit>"
    # Phase 0.5d.1: skill-self-evolution allowlist flag (X10). Default
    # is False — only skills that explicitly opt in can be proposed by
    # the Phase 3 skill-evolution worker. Forget-proof by construction:
    # new skills inherit the safe default automatically.
    self_evolvable: bool = False
    # Phase 0.5d.1: per-runtime adapter path map. Optional today; empty
    # dict means "use the legacy hard-coded adapters/claude/<id>.md path".
    # Phase 0.5d.2 softens the loader to honor this map when populated.
    # Keys are runtime slugs (claude, codex, acp); values are repo-relative
    # paths matching the _ADAPTER_PATH_PATTERN traversal guard.
    adapters: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidatorSkill:
    spec: SkillSpec
    run: Callable[..., Any]


@dataclass(frozen=True)
class AgenticSkillHandle:
    """Opaque handle passed back to LLM-context callers.

    The handle carries the prompt file path + contract. The loader never
    executes the prompt itself — that is the calling runner's job.
    """

    spec: SkillSpec
    adapter_path: str
    prompt_contract: dict[str, Any]
    unrated: bool


def _registry_path() -> Path:
    return Path(__file__).resolve().parents[3] / "skills" / "registry.yaml"


def _skills_root() -> Path:
    return Path(__file__).resolve().parents[3] / "skills"


@functools.lru_cache(maxsize=None)
def _load_registry_cached(
    path_key: str, mtime_ns: int, inode: int, size: int
) -> tuple[SkillSpec, ...]:
    """Phase 0.5d.2 — cached registry parse.

    Parses `registry.yaml` exactly once per (resolved path, mtime_ns,
    inode, size) tuple. The inode + size belt-and-braces catches the
    rare path where mtime didn't update (fast consecutive writes) and
    the atomic `os.replace()` writer from `registry_writer.py` always
    produces a new inode so the cache correctly invalidates on writes.

    Returns an immutable `tuple[SkillSpec, ...]` — NOT a `list` —
    because `lru_cache` hands back the same object on every hit. A
    mutable list return would let one caller's `.sort()` or `.append()`
    corrupt every subsequent reader.
    """
    registry_file = Path(path_key)
    raw = yaml.safe_load(registry_file.read_text()) or {}
    out: list[SkillSpec] = []
    for entry in raw.get("skills", []):
        skill_id = entry.get("id")
        kind = entry.get("kind", "agentic")
        if kind not in ("validator", "agentic"):
            raise SkillLoadError(
                f"skill {skill_id!r}: invalid kind {kind!r}"
            )
        status = entry.get("fixture_status", "missing")
        if status not in ("passing", "failing", "missing"):
            raise SkillLoadError(
                f"skill {skill_id!r}: invalid fixture_status {status!r}"
            )

        # Phase 0.5d.1: parse the optional `adapters:` map and validate
        # every value against _ADAPTER_PATH_PATTERN. Any entry that
        # doesn't match the regex is a hard load error — prevents a
        # malicious registry entry from resolving outside skills/adapters/.
        adapters_raw = entry.get("adapters") or {}
        if not isinstance(adapters_raw, dict):
            raise SkillLoadError(
                f"skill {skill_id!r}: adapters must be a mapping, "
                f"got {type(adapters_raw).__name__}"
            )
        adapters_validated: dict[str, str] = {}
        for runtime_slug, adapter_path in adapters_raw.items():
            if not isinstance(adapter_path, str):
                raise SkillLoadError(
                    f"skill {skill_id!r}: adapters[{runtime_slug!r}] must "
                    f"be a string, got {type(adapter_path).__name__}"
                )
            if not _ADAPTER_PATH_PATTERN.match(adapter_path):
                raise SkillLoadError(
                    f"skill {skill_id!r}: adapters[{runtime_slug!r}] "
                    f"value {adapter_path!r} does not match "
                    f"{_ADAPTER_PATH_PATTERN.pattern!r} "
                    "(path-traversal guard)"
                )
            adapters_validated[runtime_slug] = adapter_path

        # Phase 0.5d.1: self_evolvable defaults to False. Only explicit
        # `self_evolvable: true` opts the skill into the skill-evolution
        # worker's allowlist. Forget-proof by construction.
        self_evolvable = bool(entry.get("self_evolvable", False))

        out.append(
            SkillSpec(
                id=entry["id"],
                name=entry.get("name", entry["id"]),
                kind=kind,
                path=entry.get("path", ""),
                owner_agent=entry.get("owner_agent", "any"),
                target_runtimes=tuple(entry.get("target_runtimes", [])),
                stage=entry.get("stage", "active"),
                fixture_status=status,
                source=entry.get("source", "internal"),
                self_evolvable=self_evolvable,
                adapters=adapters_validated,
            )
        )
    return tuple(out)


def load_registry(path: Path | None = None) -> list[SkillSpec]:
    """Public loader entry point — returns a fresh list on every call.

    The parsing is cached internally via `_load_registry_cached` on
    `(resolved path, mtime_ns, inode, size)`. Callers get a fresh
    `list` wrapping the cached immutable tuple so any `.sort()` /
    `.append()` on their copy does NOT corrupt the cache.
    """
    p = (path or _registry_path()).resolve()
    st = p.stat()
    cached = _load_registry_cached(
        os.fspath(p), st.st_mtime_ns, st.st_ino, st.st_size
    )
    return list(cached)


def invalidate_registry_cache() -> None:
    """Force a re-parse on the next load_registry call.

    Used by `registry_writer.update_registry()` after an atomic write
    so in-process callers immediately see the updated entries without
    waiting for the mtime-based cache key to flip.
    """
    _load_registry_cached.cache_clear()


def _find(skill_id: str, registry: list[SkillSpec] | None = None) -> SkillSpec:
    registry = registry if registry is not None else load_registry()
    for spec in registry:
        if spec.id == skill_id:
            return spec
    raise SkillNotFound(f"skill {skill_id!r} not in registry")


def discover_fixtures(spec: SkillSpec) -> list[Path]:
    """Phase 0.5e — resolve every fixture file belonging to a skill.

    Dual-layout discovery per `docs/adr/2026-04-14-canonical-skill-layout.md`:

    1. Per-skill-directory layout:
       `skills/canonical/<skill-id>/fixtures/*.{yaml,yml,json}`

    2. Flat Phase 0 layout with sibling fixture file:
       `skills/canonical/<parent-dir>/<skill-id>.fixtures.yaml`

    3. Flat Phase 0 layout with shared fixtures subdir (future escape
       hatch, supported so a parent dir like `canonical/shared/` can
       opt into a shared `fixtures/` pool):
       `skills/canonical/<parent-dir>/fixtures/<skill-id>/*.{yaml,yml,json}`

    Returns a sorted list of absolute paths. Empty list means no
    fixtures found — the reconciliation check from Phase 1 flags
    `passing` skills with zero discovered fixtures as drift.

    This function does NOT parse or validate the fixture files. It
    only locates them. The caller is responsible for YAML/JSON parse.
    """
    skills_root = _skills_root()

    # Layout 1: per-skill dir.
    dir_layout_fixtures = skills_root / "canonical" / spec.id / "fixtures"
    found: list[Path] = []
    if dir_layout_fixtures.is_dir():
        for ext in ("yaml", "yml", "json"):
            found.extend(dir_layout_fixtures.glob(f"*.{ext}"))

    # Layout 2 + 3: flat file with sibling fixture(s). The parent dir
    # is derived from `spec.path` — e.g. `canonical/shared/product-artifact-chain.md`
    # has parent `canonical/shared/`.
    if spec.path:
        flat_skill_file = skills_root / spec.path
        parent_dir = flat_skill_file.parent
        sibling = parent_dir / f"{spec.id}.fixtures.yaml"
        if sibling.exists():
            found.append(sibling)
        shared_fixtures = parent_dir / "fixtures" / spec.id
        if shared_fixtures.is_dir():
            for ext in ("yaml", "yml", "json"):
                found.extend(shared_fixtures.glob(f"*.{ext}"))

    # Deduplicate (dir-layout fixtures can also be picked up by
    # layout-2 scan if someone puts the per-skill dir under
    # canonical/shared/, which isn't valid but is cheap to handle).
    seen: set[Path] = set()
    deduped: list[Path] = []
    for path in found:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(path)
    return sorted(deduped)


def load_validator(
    skill_id: str,
    *,
    mode: SkillMode = "autonomous",
    registry: list[SkillSpec] | None = None,
) -> ValidatorSkill:
    """Load a validator skill and return its ``run`` callable.

    Refuses agentic skills. Refuses autonomous mode unless fixtures pass.
    """
    spec = _find(skill_id, registry=registry)
    if spec.kind != "validator":
        raise SkillKindMismatch(
            f"skill {skill_id!r} has kind={spec.kind!r}; validator required"
        )
    if mode == "autonomous" and spec.fixture_status != "passing":
        raise SkillNotEvaluated(
            f"skill {skill_id!r} fixture_status={spec.fixture_status!r}; "
            "refuse to load in mode='autonomous'"
        )

    skill_dir = _skills_root() / Path(spec.path).parent
    module_file = skill_dir / "validator.py"
    if not module_file.exists():
        # Fallback: some validators live under skills/canonical/<id>/validator.py
        alt = _skills_root() / "canonical" / skill_id / "validator.py"
        if alt.exists():
            module_file = alt
        else:
            raise SkillLoadError(
                f"skill {skill_id!r}: validator.py not found at {module_file}"
            )

    module_spec = importlib.util.spec_from_file_location(
        f"skills._validator_{skill_id.replace('-', '_')}", module_file
    )
    if module_spec is None or module_spec.loader is None:
        raise SkillLoadError(f"skill {skill_id!r}: cannot import {module_file}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    run = getattr(module, "run", None)
    if not callable(run):
        raise SkillLoadError(
            f"skill {skill_id!r}: validator module must expose run(...)"
        )

    return ValidatorSkill(spec=spec, run=run)


def load_agentic(
    skill_id: str,
    *,
    mode: SkillMode = "autonomous",
    synchronous: bool = False,
    registry: list[SkillSpec] | None = None,
    runtime: str = "claude",
) -> AgenticSkillHandle:
    """Load an agentic skill for an LLM-driven runner.

    Refuses validator skills. Refuses when ``synchronous=True`` (hot-path
    caller). Returns an :class:`AgenticSkillHandle` carrying the adapter path
    and contract — actual prompt execution is the caller's responsibility.

    Adapter path resolution (Phase 0.5d.2):

    1. If ``spec.adapters[runtime]`` is set in the registry, use that
       path (validated at registry-load time by ``_ADAPTER_PATH_PATTERN``).
    2. Otherwise, fall back to the legacy hard-coded
       ``adapters/claude/<skill_id>.md`` lookup.

    The fallback is intentionally runtime-agnostic for Phase 0 — it
    returns the Claude adapter path regardless of the ``runtime``
    argument, preserving existing behavior. Phase 4 ships registry
    entries populated with `adapters: {acp: ...}` for the skills that
    gain ACP support; those entries override the fallback naturally.
    """
    if synchronous:
        raise SkillKindMismatch(
            f"skill {skill_id!r}: agentic skills refuse synchronous callers"
        )

    spec = _find(skill_id, registry=registry)
    if spec.kind != "agentic":
        raise SkillKindMismatch(
            f"skill {skill_id!r} has kind={spec.kind!r}; agentic required"
        )

    unrated = spec.fixture_status != "passing"
    if mode == "autonomous" and unrated:
        raise SkillNotEvaluated(
            f"skill {skill_id!r} fixture_status={spec.fixture_status!r}; "
            "refuse to load in mode='autonomous'"
        )

    # Phase 0.5d.2: registry-driven adapter path with legacy fallback.
    registry_adapter = spec.adapters.get(runtime)
    if registry_adapter is not None:
        adapter = _skills_root() / registry_adapter
    else:
        # Legacy fallback — preserves existing behavior when no
        # `adapters:` map is present on the skill entry.
        adapter = _skills_root() / "adapters" / "claude" / f"{skill_id}.md"

    contract_file = _skills_root() / "canonical" / skill_id / "contract.yaml"
    contract: dict[str, Any] = {}
    if contract_file.exists():
        contract = yaml.safe_load(contract_file.read_text()) or {}

    return AgenticSkillHandle(
        spec=spec,
        adapter_path=str(adapter),
        prompt_contract=contract,
        unrated=unrated,
    )
