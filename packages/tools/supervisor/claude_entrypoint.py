"""Phase 3.3 — typed supervisor entrypoint for Claude sessions.

Claude opens a :class:`SupervisorSession`, enqueues typed tasks into the
existing ``worker-engineering`` / ``worker-ios`` / ``worker-gtm`` lanes,
requests approvals, appends events, and closes the session with a
validated summary. Dispatch is **fire-and-forget**: enqueue methods
persist a task and return immediately. The existing worker loops (run
under the runtime-supervisor launchd plist from Phase 1.1) claim and
execute. Results are read back by :meth:`SessionHandle.read_result` on
the next Claude session, or by the morning briefing in Phase 4.1. No
Claude session ever blocks on a 30-minute codex run.

Strategic-task validation happens inline in :meth:`SessionHandle.close`
— the plan review deleted the idea of a separate strategic-worker
daemon because a worker whose only job is to validate is a contradictory
role (see the Phase 3.3 review note).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from apps.api.control_plane import ControlPlaneService
from packages.policies.approvals import PolicyViolation
from packages.schemas.approval import ApprovalRecord
from packages.schemas.event import EventRecord
from packages.schemas.goal import GoalRecord
from packages.schemas.task import Task
from packages.schemas.task_packet import RiskLevel, TaskStatus, WorkerLane
from packages.tools.supervisor.enqueue import (
    EngineeringTaskDef,
    GTMTaskDef,
    IOSTaskDef,
    enqueue_engineering,
    enqueue_gtm,
    enqueue_ios,
)


STRATEGIC_TASK_TYPES = frozenset(
    {
        "PRODUCT_BRIEF_UPDATE",
        "MVP_SPEC_UPDATE",
        "APPSTORE_POSITIONING_REFRESH",
        "APPSTORE_METADATA_DRAFT",
        "SCREENSHOT_PLAN_REFRESH",
        "ARTIFACT_CHAIN_REVIEW",
        "FOUNDER_BRIEF_INTAKE",
        "GTM_CAMPAIGN_BRIEF",
        "FAILURE_REGRESSION_FIXTURE",
    }
)


@dataclass(frozen=True)
class StrategicTaskDef:
    goal_id: str
    repo_id: str
    title: str
    summary: str
    task_type: str
    lane: WorkerLane
    product_id: str | None = None
    constraints: list[str] = field(default_factory=list)
    testing_policy: str = "strategic_artifact_non_logic"


@dataclass(frozen=True)
class SessionSummary:
    session_id: str
    actor: str
    opened_at: str
    closed_at: str
    summary_md: str
    enqueued_task_ids: tuple[str, ...]
    strategic_task_ids: tuple[str, ...]
    approval_ids: tuple[str, ...]
    events_appended: int


class SupervisorSession:
    """Typed entrypoint Claude uses to drive the control plane.

    Usage::

        with SupervisorSession("claude-2026-04-10-1400") as handle:
            task = handle.enqueue_engineering(task_def=...)
            handle.request_approval(...)
            handle.close(summary_md="...")
    """

    def __init__(
        self,
        session_id: str,
        *,
        actor: str = "claude",
        service: ControlPlaneService | None = None,
    ) -> None:
        self.session_id = session_id
        self.actor = actor
        self._service = service or ControlPlaneService()
        self._handle: SessionHandle | None = None

    def open(self) -> "SessionHandle":
        if self._handle is not None:
            raise RuntimeError(f"session {self.session_id} already open")
        now = _iso_now()
        self._handle = SessionHandle(
            session_id=self.session_id,
            actor=self.actor,
            service=self._service,
            opened_at=now,
        )
        self._service.events  # ensure service is wired
        self._handle._append_session_event("session_opened", {"actor": self.actor})
        return self._handle

    def __enter__(self) -> "SessionHandle":
        return self.open()

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._handle is not None and not self._handle.closed:
            # Unclean exit — still append a close event so the audit trail
            # is continuous. Do not validate strategic tasks on unclean
            # exit; raising while unwinding an exception would mask it.
            self._handle._append_session_event(
                "session_exited_uncleanly",
                {"exc_type": getattr(exc_type, "__name__", None)},
            )


class SessionHandle:
    def __init__(
        self,
        *,
        session_id: str,
        actor: str,
        service: ControlPlaneService,
        opened_at: str,
    ) -> None:
        self.session_id = session_id
        self.actor = actor
        self._service = service
        self._opened_at = opened_at
        self._enqueued: list[str] = []
        self._strategic: list[str] = []
        self._strategic_artifacts: list[tuple[Path, str | None]] = []
        self._approvals: list[str] = []
        self._events_appended = 0
        self.closed = False

    # ── strategic artifacts ───────────────────────────────────────

    def record_strategic_artifact(
        self,
        path: Path | str,
        *,
        expected_parent: str | None = None,
    ) -> None:
        """Declare a strategic markdown artifact touched by this session.

        At :meth:`close`, every recorded path is run through the
        Phase 5.4 ``claude_output`` policy. Violations surface as
        :class:`PolicyViolation` with codes prefixed ``claude_output_``.
        """
        self._strategic_artifacts.append((Path(path), expected_parent))

    # ── strategic tasks ───────────────────────────────────────────

    def create_strategic_task(self, *, task_def: StrategicTaskDef) -> Task:
        if task_def.task_type not in STRATEGIC_TASK_TYPES:
            raise PolicyViolation(
                "invalid_strategic_task_type",
                f"{task_def.task_type!r} not in STRATEGIC_TASK_TYPES",
            )
        task = self._service.create_task_for_goal(
            goal_id=task_def.goal_id,
            repo_id=task_def.repo_id,
            lane=task_def.lane,
            title=task_def.title,
            summary=task_def.summary,
            task_type=task_def.task_type,
            risk_level=RiskLevel.LOW,
            product_id=task_def.product_id,
            constraints=list(task_def.constraints),
        )
        self._strategic.append(task.id)
        return task

    # ── fire-and-forget enqueue ──────────────────────────────────

    def enqueue_engineering(self, *, task_def: EngineeringTaskDef) -> Task:
        task = enqueue_engineering(task_def, service=self._service)
        self._enqueued.append(task.id)
        return task

    def enqueue_ios(self, *, task_def: IOSTaskDef) -> Task:
        task = enqueue_ios(task_def, service=self._service)
        self._enqueued.append(task.id)
        return task

    def enqueue_gtm(self, *, task_def: GTMTaskDef) -> Task:
        task = enqueue_gtm(task_def, service=self._service)
        self._enqueued.append(task.id)
        return task

    # ── approvals ─────────────────────────────────────────────────

    def request_approval(
        self,
        *,
        subject_type: str,
        subject_id: str,
        action: str,
        summary: str,
        approval_type: str = "",
        task_id: str | None = None,
        task_run_id: str | None = None,
        review_artifact_path: str | None = None,
    ) -> ApprovalRecord:
        approval = self._service.request_approval(
            summary=summary,
            subject_type=subject_type,
            subject_id=subject_id,
            action=action,
            approval_type=approval_type or action,
            task_id=task_id,
            task_run_id=task_run_id,
            review_artifact_path=review_artifact_path,
        )
        self._approvals.append(approval.id)
        return approval

    # ── events and reads ─────────────────────────────────────────

    def append_event(self, *, event_type: str, payload: dict[str, Any]) -> None:
        self._service._append_event(  # type: ignore[attr-defined]
            event_type=event_type,
            subject_type="session",
            subject_id=self.session_id,
            payload={**payload, "session_id": self.session_id, "actor": self.actor},
        )
        self._events_appended += 1

    def read_result(self, *, task_id: str) -> Task | None:
        """Non-blocking read of a previously-enqueued task's persisted row.

        Returns ``None`` if the task is not yet completed. Callers are
        expected to poll across Claude sessions, not within one.
        """
        try:
            task = self._service.tasks.load(task_id)
        except FileNotFoundError:
            return None
        if task.status in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}:
            return None
        return task

    # ── close ─────────────────────────────────────────────────────

    def close(self, *, summary_md: str) -> SessionSummary:
        if self.closed:
            raise RuntimeError(f"session {self.session_id} already closed")

        self._validate_strategic_outputs()
        self._validate_strategic_artifacts()

        closed_at = _iso_now()
        summary = SessionSummary(
            session_id=self.session_id,
            actor=self.actor,
            opened_at=self._opened_at,
            closed_at=closed_at,
            summary_md=summary_md,
            enqueued_task_ids=tuple(self._enqueued),
            strategic_task_ids=tuple(self._strategic),
            approval_ids=tuple(self._approvals),
            events_appended=self._events_appended,
        )
        self._append_session_event(
            "session_closed",
            {
                "closed_at": closed_at,
                "summary_md_len": len(summary_md),
                "enqueued": len(self._enqueued),
                "strategic": len(self._strategic),
                "approvals": len(self._approvals),
            },
        )
        self.closed = True
        return summary

    # ── internals ─────────────────────────────────────────────────

    def _validate_strategic_outputs(self) -> None:
        """Phase 3.3 — inline strategic-task validation.

        For every strategic task created in this session, assert the task
        was persisted with a known type. Content validation of the
        underlying artifacts is Phase 5.1 (product-artifact-chain); this
        method only enforces the invariant that ``create_strategic_task``
        produced a persistable record with a valid type.
        """
        for task_id in self._strategic:
            try:
                task = self._service.tasks.load(task_id)
            except FileNotFoundError as exc:
                raise PolicyViolation(
                    "strategic_task_lost",
                    f"strategic task {task_id} not persisted",
                ) from exc
            if task.task_type not in STRATEGIC_TASK_TYPES:
                raise PolicyViolation(
                    "strategic_task_type_drift",
                    f"task {task_id} has type {task.task_type!r}",
                )

    def _validate_strategic_artifacts(self) -> None:
        """Phase 5.4 — run the claude_output policy on every recorded file."""
        if not self._strategic_artifacts:
            return
        from packages.policies.claude_output import (
            ClaudeOutputViolation,
            validate_claude_output,
        )

        for path, expected_parent in self._strategic_artifacts:
            try:
                validate_claude_output(path, expected_parent=expected_parent)
            except ClaudeOutputViolation as exc:
                raise PolicyViolation(
                    f"claude_output_{exc.code}",
                    exc.detail,
                ) from exc

    def _append_session_event(
        self, event_type: str, payload: dict[str, Any]
    ) -> None:
        self._service._append_event(  # type: ignore[attr-defined]
            event_type=event_type,
            subject_type="session",
            subject_id=self.session_id,
            payload={**payload, "session_id": self.session_id, "actor": self.actor},
        )
        self._events_appended += 1


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()
