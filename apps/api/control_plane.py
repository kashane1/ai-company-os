from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from functools import wraps
from uuid import uuid4

from packages.config.settings import ensure_runtime_directories, load_runtime_paths
from packages.db.approval_store import ApprovalStore
from packages.db.event_store import EventStore
from packages.db.goal_store import GoalStore
from packages.db.task_store import TaskStore
from packages.policies.completion_evidence import (
    SUPPORTED_LANES,
    validate_completion_evidence,
)
from packages.policies.worker_capabilities import ensure_task_lane_is_consumed
from packages.queue import TaskQueue
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.schemas.event import EventRecord
from packages.schemas.goal import GoalRecord, GoalStatus
from packages.schemas.task import Task
from packages.schemas.task_packet import RiskLevel, TaskStatus, WorkerLane
from packages.tools.skills.loader import (
    SkillLoadError,
    SkillNotEvaluated,
    SkillNotFound,
    load_validator,
)


def _atomic_lifecycle(method):
    """Keep database task, event, goal and dispatch-table writes together."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self.tasks.db.transaction():
            return method(self, *args, **kwargs)
    return wrapped


class ControlPlaneService:
    def __init__(self) -> None:
        ensure_runtime_directories()
        self.goals = GoalStore()
        self.tasks = TaskStore()
        self.approvals = ApprovalStore()
        self.events = EventStore()
        self.queue = TaskQueue()

    def health(self) -> dict[str, object]:
        paths = load_runtime_paths()
        db_info = self.queue.db.health_info()
        metrics = self.queue.metrics_by_lane()
        return {
            "status": "ok",
            "repo_root": str(paths.repo_root),
            "state_root": str(paths.state_root),
            "control_plane_db_path": str(paths.control_plane_db_path),
            "database": db_info,
            "queued_tasks": sum(counts["queued"] for counts in metrics.values()),
            "queued_tasks_by_lane": {
                lane: counts["queued"] for lane, counts in metrics.items() if counts["queued"]
            },
            "queue_metrics_by_lane": metrics,
        }

    @_atomic_lifecycle
    def create_goal(
        self,
        *,
        title: str,
        summary: str,
        description: str = "",
        goal_id: str | None = None,
        parent_goal_id: str | None = None,
    ) -> GoalRecord:
        if parent_goal_id is not None:
            self.goals.load(parent_goal_id)
        now = self._now()
        goal = GoalRecord(
            id=goal_id or self._prefixed_id("goal"),
            title=title,
            summary=summary,
            description=description,
            parent_goal_id=parent_goal_id,
            created_at=now,
            updated_at=now,
        )
        self.goals.save(goal, create_only=True)
        self._append_event(
            event_type="goal_created",
            subject_type="goal",
            subject_id=goal.id,
            goal_id=goal.id,
            payload=goal.to_dict(),
        )
        return goal

    def list_goals(self) -> list[GoalRecord]:
        return self.goals.list()

    @_atomic_lifecycle
    def create_task_for_goal(
        self,
        *,
        goal_id: str,
        repo_id: str,
        lane: WorkerLane,
        title: str,
        summary: str,
        task_type: str,
        risk_level: RiskLevel = RiskLevel.LOW,
        product_id: str | None = None,
        requires_approval: bool = False,
        constraints: list[str] | None = None,
        task_id: str | None = None,
    ) -> Task:
        goal = self.goals.load_for_update(goal_id)
        ensure_task_lane_is_consumed(lane)
        now = self._now()
        task = Task(
            id=task_id or self._prefixed_id("task"),
            goal_id=goal.id,
            repo_id=repo_id,
            lane=lane,
            title=title,
            summary=summary,
            task_type=task_type,
            product_id=product_id,
            risk_level=risk_level,
            requires_approval=requires_approval,
            constraints=constraints or [],
            created_at=now,
            updated_at=now,
        )
        self.tasks.save(task, create_only=True)
        self.queue.enqueue(task)
        if goal.status is not GoalStatus.IN_PROGRESS:
            self.goals.set_status(goal.id, GoalStatus.IN_PROGRESS, updated_at=now)
        self._append_event(
            event_type="task_created",
            subject_type="task",
            subject_id=task.id,
            goal_id=goal.id,
            task_id=task.id,
            payload=task.to_dict(),
        )
        return task

    def list_tasks_for_goal(self, goal_id: str) -> list[Task]:
        self.goals.load(goal_id)
        return self.tasks.list_for_goal(goal_id)

    @_atomic_lifecycle
    def claim_task(self, *, lane: WorkerLane, worker_id: str) -> Task | None:
        claimed = self.queue.claim_next(lanes=[lane], worker_id=worker_id)
        if claimed is None:
            return None
        task = self.tasks.claim(
            claimed.task_id, worker_id=worker_id, claimed_at=claimed.claimed_at,
            allow_reclaim=self.queue.backend.name == "redis",
        )
        self._append_event(
            event_type="task_claimed",
            subject_type="task",
            subject_id=task.id,
            goal_id=task.goal_id,
            task_id=task.id,
            payload={"worker_id": worker_id, "lane": lane.value, "claimed_at": claimed.claimed_at},
        )
        return task

    @_atomic_lifecycle
    def abandon_task(
        self, *, task_id: str, reason: str, workers_stopped: bool = False,
    ) -> tuple[Task, GoalRecord, Task]:
        """Preserve an abandoned active attempt and create a pending replacement.

        This is a stopped-worker maintenance operation. It does not claim or
        execute the replacement task. Redis terminal-dispatch cleanup remains
        the explicit reconciliation operation because Redis is outside this
        database transaction.
        """
        if not workers_stopped:
            raise ValueError("task recovery requires stopped-worker confirmation")
        reason = reason.strip()
        if not reason:
            raise ValueError("an abandonment reason is required")
        current = self.tasks.load_for_update(task_id)
        if current.status not in {TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED}:
            raise ValueError("only in-progress or blocked tasks can be abandoned")
        if not current.goal_id:
            raise ValueError("an abandoned task must have a parent goal")
        self.goals.load(current.goal_id)
        now = self._now()
        recovery_goal_id = self._prefixed_id("goal")
        replacement_task_id = self._prefixed_id("task")
        failed = self.tasks.fail(
            current.id,
            error_summary=f"abandoned after stopped-worker confirmation: {reason}",
            failed_at=now,
        )
        self._ack_database_task(current.id, worker_id=current.claimed_by or "maintenance")
        self._refresh_goal_status(current.goal_id, now)
        self._append_event(
            event_type="task_abandoned",
            subject_type="task",
            subject_id=failed.id,
            goal_id=current.goal_id,
            task_id=failed.id,
            payload={
                "reason": reason,
                "previous_status": current.status.value,
                "replacement_goal_id": recovery_goal_id,
                "replacement_task_id": replacement_task_id,
            },
        )
        recovery_goal = self.create_goal(
            goal_id=recovery_goal_id,
            parent_goal_id=current.goal_id,
            title=f"Recovery: {current.title}",
            summary=f"Replacement attempt for abandoned task {current.id}.",
            description="Created by stopped-worker maintenance recovery.",
        )
        replacement = self.create_task_for_goal(
            goal_id=recovery_goal.id,
            task_id=replacement_task_id,
            repo_id=current.repo_id,
            lane=current.lane,
            title=current.title,
            summary=current.summary,
            task_type=current.task_type,
            risk_level=current.risk_level,
            product_id=current.product_id,
            requires_approval=current.requires_approval,
            constraints=list(current.constraints),
        )
        return failed, recovery_goal, replacement

    def submit_task_result(
        self,
        *,
        task_id: str,
        status: TaskStatus,
        summary: str,
        worker_id: str,
        approval_id: str | None = None,
        artifacts: list[str] | None = None,
        events: list[str] | None = None,
    ) -> Task:
        # Redis dispatch is outside the database transaction. Commit canonical
        # state first: failed ACKs can then be retried or reconciled from it.
        task = self._persist_task_result(
            task_id=task_id, status=status, summary=summary, worker_id=worker_id,
            approval_id=approval_id, artifacts=artifacts, events=events,
        )
        if self.queue.backend.name == "redis" and task.status in {
            TaskStatus.COMPLETED, TaskStatus.FAILED,
        }:
            self.queue.acknowledge(task_id, worker_id=worker_id)
        return task

    @_atomic_lifecycle
    def _persist_task_result(
        self,
        *,
        task_id: str,
        status: TaskStatus,
        summary: str,
        worker_id: str,
        approval_id: str | None = None,
        artifacts: list[str] | None = None,
        events: list[str] | None = None,
    ) -> Task:
        current = self.tasks.load_for_update(task_id)
        if current.claimed_by != worker_id or current.status is TaskStatus.PENDING:
            raise ValueError("result requires the current task claimant")
        if current.status in {TaskStatus.COMPLETED, TaskStatus.FAILED}:
            recorded_summary = current.result_summary if status is TaskStatus.COMPLETED else current.error_summary
            if current.status is status and recorded_summary == summary:
                return current
            raise ValueError("terminal task result conflicts with the recorded result")
        self.queue.assert_claim_owner(task_id, worker_id=worker_id)
        now = self._now()
        if status is TaskStatus.COMPLETED:
            # Completion is accepted only after the lane validator verifies
            # existing evidence. Missing evidence and unavailable validators
            # are both failures, never an implicit test-only bypass.
            gate = self._run_post_run_validation(
                task_id=task_id,
                summary=summary,
                artifacts=artifacts or [],
                events=events or [],
            )
            if gate.get("verdict") != "ok":
                failure_code = gate.get("failure_code") or "post_run_validation_failed"
                reason = gate.get("reason") or failure_code
                task = self.tasks.fail(
                    task_id,
                    error_summary=f"post_run_validation:{failure_code}: {reason}",
                    failed_at=now,
                )
                self._ack_database_task(task_id, worker_id=worker_id)
                self._append_event(
                    event_type="task_result_rejected",
                    subject_type="task",
                    subject_id=task.id,
                    goal_id=task.goal_id,
                    task_id=task.id,
                    approval_id=approval_id,
                    payload={
                        "worker_id": worker_id,
                        "summary": summary,
                        "failure_code": failure_code,
                        "lane": gate.get("lane", ""),
                        "reason": reason,
                    },
                )
                self._refresh_goal_status(task.goal_id, now)
                return task

            task = self.tasks.complete(
                task_id,
                summary=summary,
                completed_at=now,
                approval_id=approval_id,
            )
            self._ack_database_task(task_id, worker_id=worker_id)
            event_type = "task_completed"
        elif status is TaskStatus.FAILED:
            task = self.tasks.fail(task_id, error_summary=summary, failed_at=now)
            self._ack_database_task(task_id, worker_id=worker_id)
            event_type = "task_failed"
        elif status is TaskStatus.BLOCKED:
            task = self.tasks.set_status(task_id, TaskStatus.BLOCKED, updated_at=now)
            event_type = "task_blocked"
        else:
            raise ValueError(f"Unsupported task result status for submit flow: {status.value}")

        self._append_event(
            event_type=event_type,
            subject_type="task",
            subject_id=task.id,
            goal_id=task.goal_id,
            task_id=task.id,
            approval_id=approval_id,
            payload={"worker_id": worker_id, "summary": summary, "status": status.value},
        )
        self._refresh_goal_status(task.goal_id, now)
        return task

    def _ack_database_task(self, task_id: str, *, worker_id: str) -> None:
        if self.queue.backend.name == "database":
            self.queue.acknowledge(task_id, worker_id=worker_id)

    @_atomic_lifecycle
    def request_approval(
        self,
        *,
        summary: str,
        subject_type: str,
        subject_id: str,
        action: str,
        approval_type: str,
        task_id: str | None = None,
        task_run_id: str | None = None,
        review_artifact_path: str | None = None,
        reviewed_revision: str = "",
        approval_id: str | None = None,
    ) -> ApprovalRecord:
        now = self._now()
        approval = ApprovalRecord(
            id=approval_id or self._prefixed_id("approval"),
            status=ApprovalStatus.PENDING,
            summary=summary,
            created_at=now,
            task_id=task_id,
            task_run_id=task_run_id,
            approval_type=approval_type,
            review_artifact_path=review_artifact_path,
            reviewed_revision=reviewed_revision,
            subject_type=subject_type,
            subject_id=subject_id,
            action=action,
        )
        self.approvals.save(approval, create_only=True)
        self._append_event(
            event_type="approval_requested",
            subject_type="approval",
            subject_id=approval.id,
            task_id=task_id,
            approval_id=approval.id,
            payload=approval.to_dict(),
        )
        return approval

    @_atomic_lifecycle
    def decide_approval(
        self,
        *,
        approval_id: str,
        status: ApprovalStatus,
        decided_by: str,
        decision_notes: str = "",
    ) -> ApprovalRecord:
        current = self.approvals.load(approval_id)
        if current.status is not ApprovalStatus.PENDING:
            return current
        if status is ApprovalStatus.PENDING:
            raise ValueError("approval decisions must be terminal")
        approval = self.approvals.update_status(
            approval_id,
            status,
            decided_by=decided_by,
            decided_at=self._now(),
            decision_notes=decision_notes,
        )
        self._append_event(
            event_type="approval_decided",
            subject_type="approval",
            subject_id=approval.id,
            task_id=approval.task_id,
            approval_id=approval.id,
            payload={
                "status": approval.status.value,
                "decided_by": approval.decided_by,
                "decision_notes": approval.decision_notes,
            },
        )
        return approval

    def list_events(self) -> list[EventRecord]:
        return self.events.list()

    def _run_post_run_validation(
        self,
        *,
        task_id: str,
        summary: str,
        artifacts: list[str],
        events: list[str],
    ) -> dict[str, str]:
        """Invoke the ``post-run-validation`` validator skill.

        Returns a fail-closed validator verdict. A missing task or unavailable
        validator is represented as a structured failure so callers can audit
        why completion was rejected.
        """
        try:
            task = self.tasks.load(task_id)
        except Exception as exc:
            return {
                "verdict": "fail",
                "failure_code": "task_unavailable",
                "reason": str(exc),
                "lane": "",
            }
        if task.lane in SUPPORTED_LANES:
            evidence = validate_completion_evidence(task)
            if not evidence.ok:
                return {
                    "verdict": "fail",
                    "failure_code": evidence.failure_code,
                    "reason": evidence.reason,
                    "lane": task.lane.value,
                }
            # The submission body is worker-supplied prose. Build the skill
            # input from the persisted TaskRun and event log instead.
            summary = evidence.summary
            artifacts = list(evidence.artifacts)
            events = [
                event.event_type
                for event in self.events.list_for_subject("task", task_id)
            ]
            failure_codes = list(evidence.failure_codes)
        else:
            failure_codes = []
        try:
            validator = load_validator("post-run-validation")
        except (SkillNotFound, SkillNotEvaluated, SkillLoadError) as exc:
            return {
                "verdict": "fail",
                "failure_code": "validator_unavailable",
                "reason": f"{type(exc).__name__}: {exc}",
                "lane": task.lane.value,
            }
        if validator is None or not callable(getattr(validator, "run", None)):
            return {
                "verdict": "fail",
                "failure_code": "validator_unavailable",
                "reason": "post-run-validation did not provide a runnable validator",
                "lane": task.lane.value,
            }
        persisted_event_types = {
            event.event_type
            for event in self.events.list_for_subject("task", task_id)
        }
        unpersisted_events = sorted(set(events) - persisted_event_types)
        if unpersisted_events:
            return {
                "verdict": "fail",
                "failure_code": "event_evidence_not_persisted",
                "reason": f"unpersisted task event(s): {unpersisted_events}",
                "lane": task.lane.value,
            }
        try:
            paths = load_runtime_paths()
            result = validator.run(
                {
                    "lane": task.lane.value,
                    "task_type": task.task_type,
                    "task_id": task_id,
                    "result": {
                        "task_id": task_id,
                        "summary": summary,
                        "status": "completed",
                        "artifacts": artifacts,
                        "events": events,
                        "failure_codes": failure_codes,
                    },
                    "repo_root": str(paths.repo_root),
                }
            )
            if not isinstance(result, dict):
                return {
                    "verdict": "fail",
                    "failure_code": "validator_invalid_result",
                    "reason": (
                        "post-run-validation returned "
                        f"{type(result).__name__}, expected a mapping"
                    ),
                    "lane": task.lane.value,
                }
            return result
        except Exception as exc:
            return {
                "verdict": "fail",
                "failure_code": f"exception:{type(exc).__name__}",
                "reason": str(exc),
                "lane": getattr(task.lane, "value", ""),
            }

    def _refresh_goal_status(self, goal_id: str | None, now: str) -> None:
        if not goal_id:
            return
        # Serialize goal aggregation across completions of different tasks.
        # SQLite holds its writer lock; Postgres needs this shared parent lock.
        self.goals.load_for_update(goal_id)
        tasks = self.tasks.list_for_goal(goal_id)
        if not tasks:
            return
        active_statuses = {TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED}
        if any(task.status in active_statuses for task in tasks):
            self.goals.set_status(goal_id, GoalStatus.IN_PROGRESS, updated_at=now)
            return
        if any(task.status is TaskStatus.FAILED for task in tasks):
            self.goals.set_status(goal_id, GoalStatus.FAILED, updated_at=now)
            return
        self.goals.set_status(goal_id, GoalStatus.COMPLETED, updated_at=now, completed_at=now)

    def _append_event(
        self,
        *,
        event_type: str,
        subject_type: str,
        subject_id: str,
        payload: dict[str, object],
        goal_id: str | None = None,
        task_id: str | None = None,
        approval_id: str | None = None,
    ) -> None:
        event = EventRecord(
            id=self._prefixed_id("event"),
            event_type=event_type,
            subject_type=subject_type,
            subject_id=subject_id,
            goal_id=goal_id,
            task_id=task_id,
            approval_id=approval_id,
            payload=payload,
            created_at=self._now(),
        )
        self.events.append(event)

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _prefixed_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex[:12]}"


def as_payload(record: object) -> dict[str, object]:
    if hasattr(record, "to_dict"):
        return getattr(record, "to_dict")()
    return asdict(record)
