"""Tests for the web-first validation handoff (F6).

The key guarantees: the projected goal actually routes to the WEB lane through
the real supervisor, the landing-page experiment has its success criteria set
before running, and the orchestration persists both records.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from packages.discovery.web_handoff import (
    BuildTarget,
    landing_page_experiment,
    plan_web_first_validation,
    web_landing_goal,
)
from packages.schemas.experiment import ExperimentMetric, ExperimentStatus, ExperimentType
from packages.schemas.opportunity import (
    EvidenceKind,
    EvidenceLink,
    OpportunityRecord,
    OpportunityStatus,
    SourceRef,
)
from packages.schemas.task_packet import Goal, WorkerLane

FIXED_ISO = "2026-05-30T12:00:00+00:00"


def _opportunity() -> OpportunityRecord:
    return OpportunityRecord(
        id="opp_abc123",
        title="Automate invoice reminders",
        problem="Freelancers chase late invoices by hand",
        audience="freelancers",
        source=SourceRef(connector="hackernews", query="invoices"),
        status=OpportunityStatus.SCORED,
        evidence=[EvidenceLink(url="https://news.ycombinator.com/item?id=1",
                               kind=EvidenceKind.COMPLAINT)],
        created_at=FIXED_ISO,
        updated_at=FIXED_ISO,
    )


def _load_supervisor():
    path = Path(__file__).resolve().parents[3] / "apps" / "worker-supervisor" / "main.py"
    spec = importlib.util.spec_from_file_location("supervisor_main_f6", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_web_goal_routes_to_web_lane_through_supervisor() -> None:
    goal = web_landing_goal(_opportunity())
    assert "landing page" in goal.summary.lower()
    sup = _load_supervisor()
    (task,) = sup.plan_goal(Goal(id=goal.id, title=goal.title, summary=goal.summary))
    assert task.lane is WorkerLane.WEB


def test_landing_page_experiment_sets_criteria_before_running() -> None:
    exp = landing_page_experiment(_opportunity(), threshold=30, window="10 days")
    assert exp.type is ExperimentType.LANDING_PAGE
    assert exp.status is ExperimentStatus.PLANNED
    assert exp.success_criteria.metric is ExperimentMetric.SIGNUPS
    assert exp.success_criteria.threshold == 30
    assert exp.success_criteria.window == "10 days"
    assert exp.opportunity_id == "opp_abc123"


def test_plan_persists_experiment_and_goal() -> None:
    goals: list = []
    experiments: list = []
    plan = plan_web_first_validation(
        _opportunity(),
        goal_sink=goals.append,
        experiment_sink=experiments.append,
        threshold=50,
    )
    assert experiments == [plan.experiment]
    assert goals == [plan.goal]
    # Experiment recorded before the goal (measurement plan exists first).
    assert plan.experiment.success_criteria.threshold == 50
    assert plan.goal.id.startswith("goal_web_")


def test_build_target_enum() -> None:
    assert BuildTarget.WEB.value == "web"
    assert BuildTarget.IOS.value == "ios"
