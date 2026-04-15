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

import importlib.util
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


def load_registry(path: Path | None = None) -> list[SkillSpec]:
    registry_file = path or _registry_path()
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
    return out


def _find(skill_id: str, registry: list[SkillSpec] | None = None) -> SkillSpec:
    registry = registry if registry is not None else load_registry()
    for spec in registry:
        if spec.id == skill_id:
            return spec
    raise SkillNotFound(f"skill {skill_id!r} not in registry")


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
) -> AgenticSkillHandle:
    """Load an agentic skill for an LLM-driven runner.

    Refuses validator skills. Refuses when ``synchronous=True`` (hot-path
    caller). Returns an :class:`AgenticSkillHandle` carrying the adapter path
    and contract — actual prompt execution is the caller's responsibility.
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

    adapter = (
        _skills_root() / "adapters" / "claude" / f"{skill_id}.md"
    )
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
