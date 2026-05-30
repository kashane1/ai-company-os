"""Web-first validation handoff (F6).

The cheapest way to validate a discovered wedge is to put a real page in front of
real people and measure intent — and a landing page is exactly what the WEB lane
builds. So the first handoff for a new opportunity isn't a full build; it's:

1. a **landing-page validation experiment** (recorded in the experiment store,
   with success criteria set *before* it runs — the same gate
   ``assert_ready_to_build`` later checks), and
2. a **web build goal** that routes to the WEB lane (its summary carries the
   "landing page" cue the supervisor's ``plan_goal`` routes on).

This closes the loop the platform already enforces: the landing page is both the
thing we build *and* the experiment that decides whether the wedge earns a fuller
build (iOS app or a full web app via ``handoff.guard_and_handoff``). Nothing here
bypasses the build gate — it *feeds* it.

Both persistence steps are injected as sinks, so this stays decoupled from the
control plane and is trivial to test.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

from packages.schemas.experiment import (
    ExperimentMetric,
    ExperimentRecord,
    ExperimentStatus,
    ExperimentType,
    SuccessCriteria,
)
from packages.schemas.goal import GoalRecord, GoalStatus
from packages.schemas.opportunity import OpportunityRecord

GoalSink = Callable[[GoalRecord], object]
ExperimentSink = Callable[[ExperimentRecord], object]


class BuildTarget(str, Enum):
    """Where a validated wedge gets built. Web is the default first target
    (cheap, fast to validate); iOS/full-app come after a wedge converts."""

    WEB = "web"
    IOS = "ios"


def web_landing_goal(
    opportunity: OpportunityRecord, *, now: Callable[[], datetime] | None = None
) -> GoalRecord:
    """Project an opportunity into a goal that routes to the WEB lane.

    The summary leads with the "landing page" cue so the supervisor's keyword
    router (`plan_goal`) sends it to ``WorkerLane.WEB`` rather than engineering.
    """
    timestamp = (now or (lambda: datetime.now(timezone.utc)))().isoformat()
    return GoalRecord(
        id=f"goal_web_{opportunity.id.removeprefix('opp_')}",
        title=f"Landing page: {opportunity.title}",
        summary=f"Build a landing page to validate demand for: {opportunity.problem}",
        description=(
            f"Web-first validation for opportunity {opportunity.id}. "
            f"Audience: {opportunity.audience}. Ship a landing page (web lane), "
            "measure intent, and only commit to a fuller build if it converts."
        ),
        status=GoalStatus.OPEN,
        created_at=timestamp,
        updated_at=timestamp,
    )


def landing_page_experiment(
    opportunity: OpportunityRecord,
    *,
    metric: ExperimentMetric = ExperimentMetric.SIGNUPS,
    threshold: float = 25,
    window: str = "14 days",
    now: Callable[[], datetime] | None = None,
) -> ExperimentRecord:
    """Build the landing-page validation experiment for an opportunity.

    Success criteria are set up front (no post-hoc goalposts), status ``PLANNED``.
    Once the page is live and the criteria are met, mark it ``PASSED`` so the
    build gate opens for the next, fuller target.
    """
    timestamp = (now or (lambda: datetime.now(timezone.utc)))().isoformat()
    return ExperimentRecord(
        id=f"exp_lp_{opportunity.id.removeprefix('opp_')}",
        opportunity_id=opportunity.id,
        type=ExperimentType.LANDING_PAGE,
        hypothesis=(
            f"A landing page for “{opportunity.title}” will draw at least "
            f"{threshold:g} {metric.value} from {opportunity.audience} within {window}."
        ),
        success_criteria=SuccessCriteria(metric=metric, threshold=threshold, window=window),
        status=ExperimentStatus.PLANNED,
        created_at=timestamp,
    )


@dataclass(frozen=True)
class WebFirstPlan:
    goal: GoalRecord
    experiment: ExperimentRecord


def plan_web_first_validation(
    opportunity: OpportunityRecord,
    *,
    goal_sink: GoalSink,
    experiment_sink: ExperimentSink,
    metric: ExperimentMetric = ExperimentMetric.SIGNUPS,
    threshold: float = 25,
    window: str = "14 days",
    now: Callable[[], datetime] | None = None,
) -> WebFirstPlan:
    """Record the landing-page experiment and create the web build goal.

    Returns the created goal + experiment. Persists the experiment first (the
    measurement plan exists before the page ships), then enqueues the goal.
    """
    experiment = landing_page_experiment(
        opportunity, metric=metric, threshold=threshold, window=window, now=now
    )
    experiment_sink(experiment)
    goal = web_landing_goal(opportunity, now=now)
    goal_sink(goal)
    return WebFirstPlan(goal=goal, experiment=experiment)
