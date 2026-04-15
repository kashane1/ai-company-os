"""Phase 1.3a — registry ↔ fixture reconciliation check (structural).

Walks every skill marked ``fixture_status: passing`` in the registry
and verifies STRUCTURAL invariants only:

1. Fixtures exist on disk for the skill (via
   ``loader.discover_fixtures``).
2. Every fixture file parses as valid YAML or JSON.
3. Every fixture has an ``input`` field (the one convention every
   skill in the repo follows; see ``social-post-safety``,
   ``approval-token-audit``, ``failure-mode-regression``,
   ``content-voice-guardrail``, etc.).

**Verdict matching is NOT done here.** Each skill has its own
validator signature and fixture conventions — some use
``input`` + ``expected``, some use ``input`` + ``expected_verdict``,
some use ``input`` + ``reasons_contains`` for set-membership
semantics. The authority for verdict correctness is each skill's
dedicated pytest file (``test_<skill-id>_skill.py``). The
reconciliation's job is to prevent the "passing without any
evidence" gap the deepening review flagged — a skill with
``fixture_status: passing`` but no fixtures on disk, or with
fixtures that don't even parse.

This check runs in CI on every push and hard-fails on drift.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from packages.tools.skills.loader import (
    SkillSpec,
    discover_fixtures,
    load_registry,
)


@dataclass(frozen=True)
class DriftItem:
    skill_id: str
    kind: str
    drift_type: str  # "missing_fixtures" | "unparseable_fixture" | "malformed_fixture"
    detail: str
    fixture_path: str | None = None


@dataclass
class ReconciliationReport:
    passing_skills_checked: int = 0
    drift_items: list[DriftItem] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not self.drift_items

    def format(self) -> str:
        if self.is_clean:
            return (
                f"Reconciliation clean: all {self.passing_skills_checked} "
                "passing skills verified structurally."
            )
        lines = [
            f"Reconciliation found {len(self.drift_items)} drift item(s) "
            f"across {self.passing_skills_checked} passing skills:"
        ]
        for item in self.drift_items:
            prefix = f"  - {item.skill_id} ({item.kind}): {item.drift_type}"
            if item.fixture_path:
                prefix += f" [{Path(item.fixture_path).name}]"
            lines.append(f"{prefix} — {item.detail}")
        return "\n".join(lines)


def reconcile_registry(
    registry: list[SkillSpec] | None = None,
) -> ReconciliationReport:
    """Structural reconciliation pass over every passing skill."""
    specs = registry if registry is not None else load_registry()
    report = ReconciliationReport()

    for spec in specs:
        if spec.fixture_status != "passing":
            continue
        report.passing_skills_checked += 1
        _check_skill_structural(spec, report)

    return report


def _check_skill_structural(
    spec: SkillSpec, report: ReconciliationReport
) -> None:
    """Invariant: fixtures exist, parse, and each has an ``input`` field."""
    fixtures = discover_fixtures(spec)
    if not fixtures:
        report.drift_items.append(
            DriftItem(
                skill_id=spec.id,
                kind=spec.kind,
                drift_type="missing_fixtures",
                detail=(
                    f"{spec.kind}-kind skill marked passing has zero "
                    "fixtures on disk"
                ),
            )
        )
        return

    for fixture_path in fixtures:
        try:
            fixture = _parse_fixture(fixture_path)
        except Exception as e:
            report.drift_items.append(
                DriftItem(
                    skill_id=spec.id,
                    kind=spec.kind,
                    drift_type="unparseable_fixture",
                    detail=f"{type(e).__name__}: {e}",
                    fixture_path=str(fixture_path),
                )
            )
            continue

        # Normalize: fixtures may be single dicts or lists-of-cases.
        cases = fixture if isinstance(fixture, list) else [fixture]
        for case in cases:
            if not isinstance(case, dict):
                report.drift_items.append(
                    DriftItem(
                        skill_id=spec.id,
                        kind=spec.kind,
                        drift_type="malformed_fixture",
                        detail=(
                            f"fixture case must be a mapping, "
                            f"got {type(case).__name__}"
                        ),
                        fixture_path=str(fixture_path),
                    )
                )
                continue
            if "input" not in case:
                report.drift_items.append(
                    DriftItem(
                        skill_id=spec.id,
                        kind=spec.kind,
                        drift_type="malformed_fixture",
                        detail="fixture case missing 'input' field",
                        fixture_path=str(fixture_path),
                    )
                )
                continue
            if case["input"] is None or case["input"] == {} or case["input"] == []:
                report.drift_items.append(
                    DriftItem(
                        skill_id=spec.id,
                        kind=spec.kind,
                        drift_type="malformed_fixture",
                        detail="fixture 'input' field is empty",
                        fixture_path=str(fixture_path),
                    )
                )


def _parse_fixture(path: Path) -> Any:
    """Parse a fixture file (YAML or JSON)."""
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        return yaml.safe_load(text)
    if path.suffix == ".json":
        import json

        return json.loads(text)
    raise ValueError(f"unknown fixture extension: {path.suffix}")
