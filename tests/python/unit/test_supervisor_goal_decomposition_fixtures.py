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

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SUPERVISOR_APP = REPO_ROOT / "apps" / "worker-supervisor"
if str(SUPERVISOR_APP) not in sys.path:
    sys.path.insert(0, str(SUPERVISOR_APP))

from main import plan_goal  # type: ignore[import-not-found]  # noqa: E402

from packages.schemas.task_packet import (  # noqa: E402
    Goal,
    RiskLevel,
    TaskPacket,
    WorkerLane,
)


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
    goal_fields = case["input"]["goal"]
    goal = Goal(
        id=goal_fields["id"],
        title=goal_fields["title"],
        summary=goal_fields["summary"],
    )
    tasks = plan_goal(goal)
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
