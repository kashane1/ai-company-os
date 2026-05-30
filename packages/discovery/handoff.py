"""Handoff — turn a validated opportunity into a build goal, gate-enforced.

This is the seam between the discovery layer and the existing build lanes. Two
jobs:

* **B3 — projection:** ``opportunity_to_goal`` maps an ``OpportunityRecord`` onto
  a typed ``GoalRecord`` the supervisor already understands.
* **B2 — enforcement:** ``guard_and_handoff`` calls ``assert_ready_to_build``
  *first*, so an opportunity can only become a build goal after a validation
  experiment has passed. The "validate before you build" rule becomes code at the
  exact boundary where work gets created, not a convention someone has to
  remember.

The actual enqueue is injected as a ``sink`` callable (e.g. ``GoalStore.save`` or
a supervisor enqueue wrapper), so this module stays decoupled from the control
plane and is trivial to test.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from packages.policies.discovery_gates import assert_ready_to_build
from packages.schemas.experiment import ExperimentRecord
from packages.schemas.goal import GoalRecord, GoalStatus
from packages.schemas.opportunity import OpportunityRecord

GoalSink = Callable[[GoalRecord], object]


def opportunity_to_goal(
    opportunity: OpportunityRecord,
    *,
    now: Callable[[], datetime] | None = None,
) -> GoalRecord:
    timestamp = (now or (lambda: datetime.now(timezone.utc)))().isoformat()
    return GoalRecord(
        id=f"goal_{opportunity.id.removeprefix('opp_')}",
        title=opportunity.title,
        summary=opportunity.problem,
        description=(
            f"Build goal from validated opportunity {opportunity.id}. "
            f"Audience: {opportunity.audience}."
        ),
        status=GoalStatus.OPEN,
        created_at=timestamp,
        updated_at=timestamp,
    )


def guard_and_handoff(
    opportunity: OpportunityRecord,
    experiment: ExperimentRecord | None,
    *,
    sink: GoalSink,
    now: Callable[[], datetime] | None = None,
) -> GoalRecord:
    """Enforce the build gate, then hand the opportunity off as a goal.

    Raises :class:`~packages.policies.approvals.PolicyViolation` (and creates
    nothing) if the validation experiment has not passed.
    """
    assert_ready_to_build(opportunity, experiment)
    goal = opportunity_to_goal(opportunity, now=now)
    sink(goal)
    return goal
