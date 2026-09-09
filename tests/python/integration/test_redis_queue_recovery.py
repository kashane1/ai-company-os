from __future__ import annotations

import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from shutil import which

import pytest

from packages.queue.task_queue import RedisStreamQueueBackend
from packages.schemas.task import Task
from packages.schemas.task_packet import RiskLevel, TaskStatus, WorkerLane


@pytest.fixture
def isolated_redis_url(tmp_path: Path) -> Iterator[str]:
    """Start a dedicated Redis process; never connect to an operator instance."""
    redis_server = which("redis-server")
    if redis_server is None:
        pytest.skip("redis-server is required for Redis queue recovery integration tests")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    process = subprocess.Popen(
        [
            redis_server,
            "--bind",
            "127.0.0.1",
            "--port",
            str(port),
            "--save",
            "",
            "--appendonly",
            "no",
            "--dir",
            str(tmp_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"redis://127.0.0.1:{port}/0"
    try:
        backend = RedisStreamQueueBackend(url=url)
        for _ in range(50):
            try:
                backend.client.ping()
                break
            except Exception:
                time.sleep(0.01)
        else:
            pytest.fail("isolated redis-server did not start")
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def test_redis_reclaims_crashed_worker_pending_task_with_owner_fencing(
    isolated_redis_url: str,
) -> None:
    backend = RedisStreamQueueBackend(url=isolated_redis_url)
    task = Task(
        id="task-crash-recovery",
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Recover pending work",
        summary="A worker crashed after claiming this task.",
        task_type="engineering_change",
        risk_level=RiskLevel.LOW,
        created_at="2026-09-08T00:00:00+00:00",
        updated_at="2026-09-08T00:00:00+00:00",
    )
    backend.enqueue(task)
    first = backend.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-crashed")
    assert first is not None

    time.sleep(0.01)
    assert backend.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-recovery") is None

    recovery = RedisStreamQueueBackend(
        url=isolated_redis_url,
        enable_recovery=True,
        reclaim_min_idle_ms=1,
    )
    recovered = recovery.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-recovery")

    assert recovered is not None
    assert recovered.task_id == task.id
    assert recovered.worker_id == "worker-recovery"
    assert not backend.acknowledge(task.id, worker_id="worker-crashed")
    assert recovery.size() == 1
    assert recovery.acknowledge(task.id, worker_id="worker-recovery")
    assert recovery.size() == 0


def test_redis_recovery_cursor_advances_across_multiple_pending_messages(
    isolated_redis_url: str,
) -> None:
    backend = RedisStreamQueueBackend(url=isolated_redis_url)
    for task_id in ("task-old-1", "task-old-2"):
        backend.enqueue(
            Task(
                id=task_id,
                repo_id="ai-company-os",
                lane=WorkerLane.ENGINEERING,
                title="Recover pending work",
                summary="A worker crashed after claiming this task.",
                task_type="engineering_change",
                risk_level=RiskLevel.LOW,
                created_at="2026-09-08T00:00:00+00:00",
                updated_at="2026-09-08T00:00:00+00:00",
            )
        )
    assert backend.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-crashed-1")
    assert backend.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-crashed-2")

    time.sleep(0.01)
    recovery = RedisStreamQueueBackend(
        url=isolated_redis_url,
        enable_recovery=True,
        reclaim_min_idle_ms=1,
    )
    first = recovery.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-recovery")
    second = recovery.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-recovery")

    assert first is not None and second is not None
    assert {first.task_id, second.task_id} == {"task-old-1", "task-old-2"}


def test_redis_atomic_ack_does_not_delete_a_reclaimed_owner_entry(
    isolated_redis_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = RedisStreamQueueBackend(url=isolated_redis_url)
    task = Task(
        id="task-ack-race",
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Protect recovered pending work",
        summary="The previous worker races acknowledgement with recovery.",
        task_type="engineering_change",
        risk_level=RiskLevel.LOW,
        created_at="2026-09-08T00:00:00+00:00",
        updated_at="2026-09-08T00:00:00+00:00",
    )
    backend.enqueue(task)
    assert backend.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-stale")
    time.sleep(0.01)
    recovery = RedisStreamQueueBackend(
        url=isolated_redis_url,
        enable_recovery=True,
        reclaim_min_idle_ms=1,
    )
    original_eval = backend.client.eval

    def reclaim_before_ack(script: str, keys: int, *args: str) -> int:
        assert recovery.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-current")
        return original_eval(script, keys, *args)

    monkeypatch.setattr(backend.client, "eval", reclaim_before_ack)

    assert not backend.acknowledge(task.id, worker_id="worker-stale")
    assert recovery.size() == 1
    assert recovery.acknowledge(task.id, worker_id="worker-current")


def test_redis_queue_metrics_distinguish_queued_and_inflight_work(
    isolated_redis_url: str,
) -> None:
    backend = RedisStreamQueueBackend(url=isolated_redis_url)
    assert backend.metrics_by_lane() == {}
    assert backend.client.keys("ai-company-os:queue:*") == []

    ungrouped_stream = backend._stream(WorkerLane.IOS)
    backend.client.xadd(
        ungrouped_stream,
        {"task_id": "task-ungrouped", "lane": WorkerLane.IOS.value},
    )
    assert backend.metrics_by_lane()[WorkerLane.IOS.value] == {
        "queued": 1,
        "inflight": 0,
        "total": 1,
    }
    assert backend.client.xinfo_groups(ungrouped_stream) == []

    task = Task(
        id="task-metrics",
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Report dispatch state",
        summary="Separate queued from in-flight work.",
        task_type="engineering_change",
        risk_level=RiskLevel.LOW,
        created_at="2026-09-08T00:00:00+00:00",
        updated_at="2026-09-08T00:00:00+00:00",
    )
    backend.enqueue(task)
    assert backend.counts_by_lane() == {
        WorkerLane.ENGINEERING.value: 1,
        WorkerLane.IOS.value: 1,
    }
    assert backend.metrics_by_lane()[WorkerLane.ENGINEERING.value] == {
        "queued": 1,
        "inflight": 0,
        "total": 1,
    }
    assert backend.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-metrics")
    assert backend.size(WorkerLane.ENGINEERING) == 1
    assert backend.counts_by_lane() == {WorkerLane.IOS.value: 1}
    assert backend.metrics_by_lane()[WorkerLane.ENGINEERING.value] == {
        "queued": 0,
        "inflight": 1,
        "total": 1,
    }


def test_redis_reconciliation_dry_runs_then_repairs_terminal_orphan_and_missing_dispatch(
    isolated_redis_url: str,
) -> None:
    backend = RedisStreamQueueBackend(url=isolated_redis_url)

    def task(task_id: str, status: TaskStatus) -> Task:
        return Task(
            id=task_id,
            repo_id="ai-company-os",
            lane=WorkerLane.ENGINEERING,
            title="Reconcile dispatch",
            summary="Use canonical task state to repair Redis dispatch.",
            task_type="engineering_change",
            status=status,
            risk_level=RiskLevel.LOW,
            created_at="2026-09-08T00:00:00+00:00",
            updated_at="2026-09-08T00:00:00+00:00",
        )

    pending = task("task-pending", TaskStatus.PENDING)
    missing = task("task-missing", TaskStatus.PENDING)
    terminal = task("task-terminal", TaskStatus.COMPLETED)
    active = task("task-active", TaskStatus.IN_PROGRESS)
    backend.enqueue(active)
    assert backend.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-active")
    for queued in (pending, terminal):
        backend.enqueue(queued)
    stream = backend._stream(WorkerLane.ENGINEERING)
    backend.client.xadd(stream, {"task_id": "task-orphan", "lane": "engineering"})

    preview = backend.reconcile_pending([pending, missing, terminal, active], dry_run=True)

    assert preview.enqueued_missing_ids == ("task-missing",)
    assert set(preview.removed_terminal_ids) == {"task-terminal"}
    assert preview.removed_orphan_ids == ("task-orphan",)
    assert preview.preserved_active_ids == ("task-active",)
    assert backend.size(WorkerLane.ENGINEERING) == 4

    applied = backend.reconcile_pending([pending, missing, terminal, active], dry_run=False, workers_stopped=True)

    assert applied.dry_run is False
    assert applied.removed_orphan_ids == preview.removed_orphan_ids
    assert applied.removed_terminal_ids == preview.removed_terminal_ids
    assert applied.enqueued_missing_ids == preview.enqueued_missing_ids
    assert applied.preserved_active_ids == preview.preserved_active_ids
    remaining = backend.client.xrange(stream, "-", "+")
    assert {entry[1]["task_id"] for entry in remaining} == {
        "task-pending",
        "task-missing",
        "task-active",
    }


def test_redis_reconciliation_reports_then_repairs_uncommitted_pending_claim_only_when_workers_stopped(
    isolated_redis_url: str,
) -> None:
    backend = RedisStreamQueueBackend(url=isolated_redis_url)
    pending = Task(
        id="task-uncommitted-claim",
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Repair uncommitted claim",
        summary="The Redis claim succeeded but canonical task claiming rolled back.",
        task_type="engineering_change",
        status=TaskStatus.PENDING,
        risk_level=RiskLevel.LOW,
        created_at="2026-09-08T00:00:00+00:00",
        updated_at="2026-09-08T00:00:00+00:00",
    )
    backend.enqueue(pending)
    assert backend.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-crashed")

    preview = backend.reconcile_pending([pending], dry_run=True)

    assert preview.uncommitted_claim_ids == (pending.id,)
    assert preview.enqueued_missing_ids == ()
    assert backend.size(WorkerLane.ENGINEERING) == 1
    with pytest.raises(ValueError, match="workers_stopped"):
        backend.reconcile_pending([pending], dry_run=False)
    assert backend.size(WorkerLane.ENGINEERING) == 1

    applied = backend.reconcile_pending([pending], dry_run=False, workers_stopped=True)

    assert applied.uncommitted_claim_ids == (pending.id,)
    assert applied.requeued_uncommitted_claim_ids == (pending.id,)
    assert backend.size(WorkerLane.ENGINEERING) == 1
    assert backend.client.xpending(backend._stream(pending.lane), backend.group)["pending"] == 0
    repeated = backend.reconcile_pending([pending], dry_run=False, workers_stopped=True)
    assert repeated.uncommitted_claim_ids == ()
    assert repeated.enqueued_missing_ids == ()
    assert backend.size(WorkerLane.ENGINEERING) == 1


def test_redis_reconciliation_reports_missing_in_progress_without_requeuing(
    isolated_redis_url: str,
) -> None:
    backend = RedisStreamQueueBackend(url=isolated_redis_url)
    active = Task(
        id="task-missing-active-dispatch",
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Review abandoned task",
        summary="Canonical work is active but has no Redis dispatch entry.",
        task_type="engineering_change",
        status=TaskStatus.IN_PROGRESS,
        risk_level=RiskLevel.LOW,
        created_at="2026-09-08T00:00:00+00:00",
        updated_at="2026-09-08T00:00:00+00:00",
    )

    preview = backend.reconcile_pending([active], dry_run=True)
    applied = backend.reconcile_pending([active], dry_run=False, workers_stopped=True)

    assert preview.abandoned_in_progress_ids == (active.id,)
    assert applied.abandoned_in_progress_ids == (active.id,)
    assert backend.size(WorkerLane.ENGINEERING) == 0


def test_redis_reconciliation_removes_orphan_without_a_consumer_group(
    isolated_redis_url: str,
) -> None:
    backend = RedisStreamQueueBackend(url=isolated_redis_url)
    stream = backend._stream(WorkerLane.ENGINEERING)
    backend.client.xadd(stream, {"task_id": "orphan-without-group", "lane": "engineering"})

    applied = backend.reconcile_pending([], dry_run=False, workers_stopped=True)

    assert applied.removed_orphan_ids == ("orphan-without-group",)
    assert backend.client.xlen(stream) == 0


def test_redis_reconciliation_preserves_blocked_dispatch_for_explicit_resume(
    isolated_redis_url: str,
) -> None:
    backend = RedisStreamQueueBackend(url=isolated_redis_url)
    blocked = Task(
        id="task-blocked-awaiting-review",
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Await operator review",
        summary="The worker has blocked this task for an explicit review action.",
        task_type="engineering_change",
        status=TaskStatus.BLOCKED,
        risk_level=RiskLevel.LOW,
        created_at="2026-09-08T00:00:00+00:00",
        updated_at="2026-09-08T00:00:00+00:00",
    )
    backend.enqueue(blocked)
    assert backend.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-blocked")

    applied = backend.reconcile_pending([blocked], dry_run=False, workers_stopped=True)

    assert applied.preserved_active_ids == (blocked.id,)
    assert backend.size(WorkerLane.ENGINEERING) == 1
    assert backend.client.xpending(backend._stream(blocked.lane), backend.group)["pending"] == 1
