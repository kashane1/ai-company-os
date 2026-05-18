"""End-to-end control loop on fixtures, zero external dependencies.

Exercises the same path the runtime takes — goal -> typed task ->
worker execution -> validation -> human approval gate -> structured
audit artifact — using the real schema classes, with no Postgres,
Redis, Codex, network, or Mac runtime. This is the single most
load-bearing "safe to leave running unattended" assertion.
"""

from __future__ import annotations

from scripts.demo.run_demo import build_demo_run

from packages.schemas.approval import ApprovalStatus
from packages.schemas.goal import GoalStatus
from packages.schemas.task_run import EngineeringResultClassification, TaskRun, TaskRunStatus


def test_happy_path_reaches_approved_audited_state():
    run = build_demo_run(succeeded=True)

    assert run.goal.status is GoalStatus.COMPLETED
    assert run.task_run.status is TaskRunStatus.SUCCEEDED
    assert run.task_run.classification is EngineeringResultClassification.SAFE_FOR_REVIEW
    # The audit artifact is linked to the approval that gated the merge.
    assert run.task_run.approval_id == run.approval.id
    assert run.approval.status is ApprovalStatus.APPROVED
    assert run.approval.decided_by  # a human actually decided
    assert all(check.passed for check in run.task_run.validation_checks)


def test_audit_artifact_is_replayable():
    """An audit artifact you cannot faithfully reload is not an audit
    artifact. Round-trip must be lossless."""
    run = build_demo_run(succeeded=True)
    restored = TaskRun.from_dict(run.task_run.to_dict())
    assert restored.to_dict() == run.task_run.to_dict()


def test_failure_path_takes_no_irreversible_action_and_is_audited():
    run = build_demo_run(succeeded=False)

    assert run.task_run.status is TaskRunStatus.FAILED
    # No approval was granted -> the irreversible action did not happen.
    assert run.approval.status is ApprovalStatus.PENDING
    assert run.approval.decided_by is None
    assert run.task_run.approval_id is None
    # The failure is still captured as a structured, redacted audit record.
    assert run.postmortem.task_run_id == run.task_run.id
    assert run.postmortem.failure_code == "execution_failed"
