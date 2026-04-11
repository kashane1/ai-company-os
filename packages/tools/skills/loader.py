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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

import yaml


SkillKind = Literal["validator", "agentic"]
SkillMode = Literal["autonomous", "manual"]
FixtureStatus = Literal["passing", "failing", "missing"]


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
        kind = entry.get("kind", "agentic")
        if kind not in ("validator", "agentic"):
            raise SkillLoadError(
                f"skill {entry.get('id')!r}: invalid kind {kind!r}"
            )
        status = entry.get("fixture_status", "missing")
        if status not in ("passing", "failing", "missing"):
            raise SkillLoadError(
                f"skill {entry.get('id')!r}: invalid fixture_status {status!r}"
            )
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
