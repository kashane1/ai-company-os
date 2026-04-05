from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from uuid import uuid4

from packages.config.settings import ensure_runtime_directories, load_runtime_paths
from packages.db.approval_store import ApprovalStore
from packages.db.event_store import EventStore
from packages.db.goal_store import GoalStore
from packages.db.task_store import TaskStore
from packages.queue import TaskQueue
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.schemas.event import EventRecord
from packages.schemas.goal import GoalRecord, GoalStatus
from packages.schemas.task import Task
from packages.schemas.task_packet import RiskLevel, TaskStatus, WorkerLane


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
        return {
            "status": "ok",
            "repo_root": str(paths.repo_root),
            "state_root": str(paths.state_root),
            "control_plane_db_path": str(paths.control_plane_db_path),
            "queued_tasks": self.queue.size(),
        }

    def create_goal(
        self,
        *,
        title: str,
        summary: str,
        description: str = "",
        goal_id: str | None = None,
        parent_goal_id: str | None = None,
    ) -> GoalRecord:
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
        self.goals.save(goal)
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
        goal = self.goals.load(goal_id)
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
        self.tasks.save(task)
        self.queue.enqueue(task)
        if goal.status is GoalStatus.OPEN:
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

    def claim_task(self, *, lane: WorkerLane, worker_id: str) -> Task | None:
        claimed = self.queue.claim_next(lanes=[lane], worker_id=worker_id)
        if claimed is None:
            return None
        task = self.tasks.claim(claimed.task_id, worker_id=worker_id, claimed_at=claimed.claimed_at)
        self._append_event(
            event_type="task_claimed",
            subject_type="task",
            subject_id=task.id,
            goal_id=task.goal_id,
            task_id=task.id,
            payload={"worker_id": worker_id, "lane": lane.value, "claimed_at": claimed.claimed_at},
        )
        return task

    def submit_task_result(
        self,
        *,
        task_id: str,
        status: TaskStatus,
        summary: str,
        worker_id: str,
        approval_id: str | None = None,
    ) -> Task:
        now = self._now()
        if status is TaskStatus.COMPLETED:
            task = self.tasks.complete(
                task_id,
                summary=summary,
                completed_at=now,
                approval_id=approval_id,
            )
            self.queue.acknowledge(task_id)
            event_type = "task_completed"
        elif status is TaskStatus.FAILED:
            task = self.tasks.fail(task_id, error_summary=summary, failed_at=now)
            self.queue.acknowledge(task_id)
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
            subject_type=subject_type,
            subject_id=subject_id,
            action=action,
        )
        self.approvals.save(approval)
        self._append_event(
            event_type="approval_requested",
            subject_type="approval",
            subject_id=approval.id,
            task_id=task_id,
            approval_id=approval.id,
            payload=approval.to_dict(),
        )
        return approval

    def decide_approval(
        self,
        *,
        approval_id: str,
        status: ApprovalStatus,
        decided_by: str,
        decision_notes: str = "",
    ) -> ApprovalRecord:
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
                "status": status.value,
                "decided_by": decided_by,
                "decision_notes": decision_notes,
            },
        )
        return approval

    def list_events(self) -> list[EventRecord]:
        return self.events.list()

    def _refresh_goal_status(self, goal_id: str | None, now: str) -> None:
        if not goal_id:
            return
        tasks = self.tasks.list_for_goal(goal_id)
        if not tasks:
            return
        if any(task.status in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED} for task in tasks):
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
