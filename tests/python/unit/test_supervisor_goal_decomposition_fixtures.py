"""Phase 1 PR-1b — fixture replay for supervisor-goal-decomposition.

Loads the sibling fixture file at
`skills/canonical/shared/supervisor-goal-decomposition.fixtures.yaml`
and runs each case through `apps/worker-supervisor/main.py:plan_goal`.

This is the PER-SKILL verdict test (the reconciliation check is
structural-only; actual pass/fail logic lives here and in the other
`test_<skill-id>_fixtures.py` files).

The skill is `kind: agentic` in the registry — LLM-backed for the
natural-language decomposition — but the supervisor's ROUTING is
deterministic Python. These fixtures exercise the deterministic path,
which is exactly the contract that gets called in autonomous
dispatch when `worker-supervisor` routes tasks to lanes.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from packages.schemas.task_packet import (
    Goal,
    RiskLevel,
    TaskPacket,
    WorkerLane,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKER_SUPERVISOR_MAIN = REPO_ROOT / "apps" / "worker-supervisor" / "main.py"


def _load_worker_supervisor_main() -> Any:
    """Import apps/worker-supervisor/main.py under a unique module name.

    We CANNOT use `from main import plan_goal` because multiple apps in
    this repo have a `main.py` and bare-name imports pollute sys.modules.
    Matches the existing `load_runtime_supervisor_main` helper pattern
    in tests/python/unit/test_default_worker_specs_api.py.
    """
    spec = importlib.util.spec_from_file_location(
        "worker_supervisor_main_goal_decomposition_fixture",
        WORKER_SUPERVISOR_MAIN,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FIXTURES_PATH = (
    REPO_ROOT
    / "skills"
    / "canonical"
    / "shared"
    / "supervisor-goal-decomposition.fixtures.yaml"
)


def _load_cases() -> list[dict]:
    with FIXTURES_PATH.open() as f:
        raw = yaml.safe_load(f)
    assert isinstance(raw, list), "fixture file must be a list of cases"
    return raw


def _case_id(case: dict) -> str:
    return case["name"]


@pytest.mark.parametrize("case", _load_cases(), ids=_case_id)
def test_plan_goal_matches_fixture(case: dict) -> None:
    worker_supervisor_main = _load_worker_supervisor_main()
    goal_fields = case["input"]["goal"]
    goal = Goal(
        id=goal_fields["id"],
        title=goal_fields["title"],
        summary=goal_fields["summary"],
    )
    tasks = worker_supervisor_main.plan_goal(goal)
    assert len(tasks) == 1, (
        f"plan_goal must return exactly one task per goal today, "
        f"got {len(tasks)}"
    )
    task = tasks[0]
    assert isinstance(task, TaskPacket)

    expected = case["expected"]

    # Lane match — compare via enum string value.
    expected_lane = WorkerLane(expected["lane"])
    assert task.lane is expected_lane, (
        f"{case['name']}: expected lane {expected_lane.value!r}, "
        f"got {task.lane.value!r}"
    )

    expected_risk = RiskLevel(expected["risk_level"])
    assert task.risk_level is expected_risk, (
        f"{case['name']}: expected risk {expected_risk.value!r}, "
        f"got {task.risk_level.value!r}"
    )

    assert task.requires_approval is expected["requires_approval"], (
        f"{case['name']}: expected requires_approval="
        f"{expected['requires_approval']}, got {task.requires_approval}"
    )

    assert task.tests_required is expected["tests_required"], (
        f"{case['name']}: expected tests_required="
        f"{expected['tests_required']}, got {task.tests_required}"
    )
