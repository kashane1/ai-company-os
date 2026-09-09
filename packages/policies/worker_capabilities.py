"""Control-plane policy for lanes that have a live task consumer.

``WorkerLane`` is deliberately broader than the processes currently managed by
the local runtime supervisor.  The control plane must not enqueue a task merely
because its enum value exists: an orphaned task looks actionable but will never
be claimed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from packages.schemas.task_packet import WorkerLane


class LaneExecutionMode(str, Enum):
    SUPERVISED = "supervised"
    OPERATOR_INVOKED = "operator_invoked"
    PLANNED = "planned"


@dataclass(frozen=True)
class LaneCapability:
    execution_mode: LaneExecutionMode
    accepts_queued_tasks: bool
    guidance: str


# One explicit table keeps the schema, planner, and active runtime honest about
# how each lane can run. Adding an enum member must include an intentional
# capability decision here before it can enter the queue.
LANE_CAPABILITIES = {
    WorkerLane.SUPERVISOR: LaneCapability(
        LaneExecutionMode.PLANNED,
        False,
        "Use SupervisorSession.record_strategic_artifact for interactive planning, "
        "or route executable work to a supervised specialist lane.",
    ),
    WorkerLane.ENGINEERING: LaneCapability(
        LaneExecutionMode.SUPERVISED, True, "Handled by worker-engineering."
    ),
    WorkerLane.IOS: LaneCapability(
        LaneExecutionMode.SUPERVISED, True, "Handled by worker-ios."
    ),
    WorkerLane.APPSTORE: LaneCapability(
        LaneExecutionMode.SUPERVISED, True, "Handled locally by worker-appstore."
    ),
    WorkerLane.SKILL_EVOLUTION: LaneCapability(
        LaneExecutionMode.SUPERVISED, True, "Handled by worker-skill-evolution."
    ),
    WorkerLane.OUTREACH: LaneCapability(
        LaneExecutionMode.SUPERVISED, True, "Handled by worker-outreach."
    ),
    WorkerLane.GTM: LaneCapability(
        LaneExecutionMode.OPERATOR_INVOKED,
        False,
        "Run the GTM entrypoint manually; it is not registered with the active runtime.",
    ),
    WorkerLane.WEB: LaneCapability(
        LaneExecutionMode.OPERATOR_INVOKED,
        False,
        "Use the supported web build CLI manually.",
    ),
    WorkerLane.WEBDEPLOY: LaneCapability(
        LaneExecutionMode.OPERATOR_INVOKED,
        False,
        "Use the approval-gated web deploy CLI manually.",
    ),
}

TASK_CONSUMER_LANES = frozenset(
    lane
    for lane, capability in LANE_CAPABILITIES.items()
    if capability.execution_mode is LaneExecutionMode.SUPERVISED
)
UNCONSUMED_LANES = frozenset(
    lane
    for lane, capability in LANE_CAPABILITIES.items()
    if not capability.accepts_queued_tasks
)


class LaneCapabilityError(ValueError):
    """A requested lane cannot be accepted by the active task runtime."""


def ensure_task_lane_is_consumed(lane: WorkerLane) -> None:
    """Reject lanes that would otherwise leave a task unclaimed forever."""
    capability = LANE_CAPABILITIES.get(lane)
    if capability is None:
        raise LaneCapabilityError(
            f"Lane '{lane.value}' has no capability registration and cannot be queued."
        )
    if not capability.accepts_queued_tasks:
        raise LaneCapabilityError(
            f"Lane '{lane.value}' is unsupported by the active task runtime and "
            f"has no registered consumer. {capability.guidance} Classify this work "
            "as manual or route it to a supported lane before enqueueing."
        )
