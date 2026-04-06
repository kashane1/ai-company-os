from pathlib import Path
import time
import sys
from dataclasses import asdict, dataclass
from threading import Event

ROOT = Path(__file__).resolve().parents[2]
ENGINEERING_APP = ROOT / "apps" / "worker-engineering"
for entry in (ROOT, ENGINEERING_APP):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from apps.api.control_plane import ControlPlaneService
from ios.runner import execute_task
from packages.schemas.approval import ApprovalRecord
from packages.schemas.task_packet import TaskResult
from packages.schemas.task_packet import TaskStatus, WorkerLane


@dataclass(frozen=True)
class WorkerLoopStats:
    worker_id: str
    processed_count: int
    idle_cycles: int
    stop_reason: str


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
        summary = f"iOS worker execution failed: {exc}"
        control_plane.submit_task_result(
            task_id=task.id,
            status=TaskStatus.FAILED,
            summary=summary,
            worker_id=worker_id,
        )
        raise

    control_plane.submit_task_result(
        task_id=task.id,
        status=result.status,
        summary=result.summary,
        worker_id=worker_id,
        approval_id=result.approval_id,
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
    stop_signal = stop_event or Event()
    processed_count = 0
    idle_cycles = 0
    iterations = 0
    stop_reason = "stopped"

    while not stop_signal.is_set():
        try:
            result = execute_claimed_task(worker_id=worker_id, service=control_plane)
        except KeyboardInterrupt:
            stop_reason = "interrupted"
            break
        except Exception:
            processed_count += 1
            stop_reason = "failed"
            iterations += 1
            if max_iterations is not None and iterations >= max_iterations:
                break
            continue

        iterations += 1
        if result is None:
            idle_cycles += 1
            stop_reason = "idle"
            sleep_fn(poll_interval_seconds)
            if max_iterations is not None and iterations >= max_iterations:
                break
            continue

        processed_count += 1
        stop_reason = "processed"
        if max_iterations is not None and iterations >= max_iterations:
            break

    if stop_signal.is_set():
        stop_reason = "stop_requested"

    return WorkerLoopStats(
        worker_id=worker_id,
        processed_count=processed_count,
        idle_cycles=idle_cycles,
        stop_reason=stop_reason,
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
