"""Phase 2.1 — worker-gtm entrypoint.

Mirrors apps/worker-engineering/main.py. The worker:

- Honors the kill switch (`state/flags/gtm_frozen`) before every claim and
  every MCP call.
- Honors the MCP threat model acknowledgment (Phase 2.0): if the threat
  model hash has drifted from the recorded checksum, the worker refuses to
  claim tasks and emits a lane-blocked event.
- Runs draft/voice-guardrail/social-post-safety/schedule as a chain. Publish
  is approval-gated.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Event

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from apps.api.control_plane import ControlPlaneService
from gtm.runner import execute_task, GtmFrozenError
from gtm.validator import check_threat_model_drift, is_gtm_frozen
from packages.schemas.task_packet import TaskResult, TaskStatus, WorkerLane


@dataclass(frozen=True)
class WorkerLoopStats:
    worker_id: str
    processed_count: int
    idle_cycles: int
    frozen_cycles: int
    stop_reason: str


def _refuse_if_blocked(control_plane: ControlPlaneService, worker_id: str) -> str | None:
    if is_gtm_frozen(ROOT):
        return "frozen"
    drift = check_threat_model_drift(ROOT)
    if drift is not None:
        return f"threat_model_drift:{drift}"
    return None


def execute_claimed_task(
    *, worker_id: str, service: ControlPlaneService | None = None
) -> TaskResult | None:
    control_plane = service or ControlPlaneService()

    blocked = _refuse_if_blocked(control_plane, worker_id)
    if blocked is not None:
        return None

    task = control_plane.claim_task(lane=WorkerLane.GTM, worker_id=worker_id)
    if task is None:
        return None

    try:
        result = execute_task(task)
    except GtmFrozenError:
        # Re-queue the task as paused:frozen. No work stranded.
        control_plane.submit_task_result(
            task_id=task.id,
            status=TaskStatus.BLOCKED,
            summary="paused:frozen — gtm kill switch engaged mid-task",
            worker_id=worker_id,
        )
        return None
    except Exception as exc:
        control_plane.submit_task_result(
            task_id=task.id,
            status=TaskStatus.FAILED,
            summary=f"gtm worker execution failed: {exc}",
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
    processed = 0
    idle = 0
    frozen = 0
    iters = 0
    stop_reason = "stopped"

    while not stop_signal.is_set():
        try:
            blocked = _refuse_if_blocked(control_plane, worker_id)
            if blocked is not None:
                frozen += 1
                sleep_fn(poll_interval_seconds)
                iters += 1
                if max_iterations is not None and iters >= max_iterations:
                    stop_reason = "frozen"
                    break
                continue

            result = execute_claimed_task(
                worker_id=worker_id, service=control_plane
            )
        except KeyboardInterrupt:
            stop_reason = "interrupted"
            break
        except Exception:
            processed += 1
            stop_reason = "failed"
            iters += 1
            if max_iterations is not None and iters >= max_iterations:
                break
            continue

        iters += 1
        if result is None:
            idle += 1
            sleep_fn(poll_interval_seconds)
            stop_reason = "idle"
            if max_iterations is not None and iters >= max_iterations:
                break
            continue
        processed += 1
        stop_reason = "processed"
        if max_iterations is not None and iters >= max_iterations:
            break

    return WorkerLoopStats(
        worker_id=worker_id,
        processed_count=processed,
        idle_cycles=idle,
        frozen_cycles=frozen,
        stop_reason=stop_reason,
    )


if __name__ == "__main__":
    try:
        stats = run_worker_loop(worker_id="worker-gtm")
    except KeyboardInterrupt:
        stats = WorkerLoopStats(
            worker_id="worker-gtm",
            processed_count=0,
            idle_cycles=0,
            frozen_cycles=0,
            stop_reason="interrupted",
        )
    print(json.dumps({"stats": asdict(stats)}, default=str))
