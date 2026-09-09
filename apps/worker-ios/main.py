import sys
import time
from dataclasses import asdict, replace
from pathlib import Path
from threading import Event

ROOT = Path(__file__).resolve().parents[2]
ENGINEERING_APP = ROOT / "apps" / "worker-engineering"
for entry in (ROOT, ENGINEERING_APP):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from ios.runner import execute_task

from apps.api.control_plane import ControlPlaneService
from packages.schemas.approval import ApprovalRecord
from packages.schemas.task_packet import TaskResult, TaskStatus, WorkerLane
from packages.tools.worker_loop import (
    WorkerLoopStats,
    redacted_error_message,
    worker_exit_code,
)
from packages.tools.worker_loop import run_worker_loop as shared_worker_loop


def execute(task_id: str) -> TaskResult:
    return execute_task(task_id)


def execute_claimed_task(*, worker_id: str, service: ControlPlaneService | None = None) -> TaskResult | None:
    control_plane = service or ControlPlaneService()
    task = control_plane.claim_task(lane=WorkerLane.IOS, worker_id=worker_id)
    if task is None:
        return None

    def approval_factory(
        task_id: str,
        task_run_id: str,
        review_artifact_path: str,
        summary: str,
    ) -> ApprovalRecord:
        return control_plane.request_approval(
            summary=summary,
            subject_type="task_run",
            subject_id=task_run_id,
            action="review_ios_task",
            approval_type="ios_review",
            task_id=task_id,
            task_run_id=task_run_id,
            review_artifact_path=review_artifact_path,
        )

    try:
        result = execute_task(
            task.id,
            update_task_status=False,
            approval_factory=approval_factory,
        )
    except Exception as exc:
        summary = f"iOS worker execution failed: {redacted_error_message(exc)}"
        control_plane.submit_task_result(
            task_id=task.id,
            status=TaskStatus.FAILED,
            summary=summary,
            worker_id=worker_id,
        )
        return TaskResult(task_id=task.id, status=TaskStatus.FAILED, summary=summary)

    result_artifacts = list(result.artifacts or [])
    submit_kwargs: dict = {
        "task_id": task.id,
        "status": result.status,
        "summary": result.summary,
        "worker_id": worker_id,
        "approval_id": result.approval_id,
    }
    if result_artifacts:
        submit_kwargs["artifacts"] = result_artifacts
    if result.status is TaskStatus.COMPLETED:
        submit_kwargs["events"] = ["task_claimed"]
    submitted = control_plane.submit_task_result(**submit_kwargs)
    if submitted.status is not result.status:
        return replace(
            result,
            status=submitted.status,
            summary=submitted.error_summary or result.summary,
            failure_codes=[*result.failure_codes, "post_run_validation_failed"],
        )
    return result


def run_worker_loop(
    *,
    worker_id: str,
    service: ControlPlaneService | None = None,
    poll_interval_seconds: float = 2.0,
    stop_event: Event | None = None,
    sleep_fn=time.sleep,
    max_iterations: int | None = None,
) -> WorkerLoopStats:
    control_plane = service or ControlPlaneService()
    return shared_worker_loop(
        worker_id=worker_id,
        work_once=lambda: execute_claimed_task(worker_id=worker_id, service=control_plane),
        poll_interval_seconds=poll_interval_seconds,
        stop_event=stop_event,
        sleep_fn=sleep_fn,
        max_iterations=max_iterations,
    )


if __name__ == "__main__":
    import json

    try:
        stats = run_worker_loop(worker_id="worker-ios")
    except KeyboardInterrupt:
        stats = WorkerLoopStats(
            worker_id="worker-ios",
            processed_count=0,
            idle_cycles=0,
            stop_reason="interrupted",
        )
    print(json.dumps({"stats": asdict(stats)}, default=str))
    raise SystemExit(worker_exit_code(stats))
