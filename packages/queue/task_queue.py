from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from packages.config.settings import QUEUE_BACKEND_ENV_VAR, REDIS_URL_ENV_VAR
from packages.db.contracts import TASK_QUEUE_TABLE
from packages.db.control_plane_db import ControlPlaneDatabase
from packages.schemas.task import Task
from packages.schemas.task_packet import TaskStatus, WorkerLane

try:
    import redis
except ImportError:  # pragma: no cover - only hit if optional runtime dep is absent.
    redis = None


@dataclass(frozen=True)
class ClaimedTask:
    task_id: str
    lane: WorkerLane
    worker_id: str
    claimed_at: str


class QueueClaimOwnershipError(RuntimeError):
    """Raised when a worker no longer owns a Redis stream claim."""


@dataclass(frozen=True)
class QueueReconciliationReport:
    """Planned or applied repairs against canonical task state."""

    dry_run: bool
    removed_orphan_ids: tuple[str, ...]
    removed_terminal_ids: tuple[str, ...]
    enqueued_missing_ids: tuple[str, ...]
    preserved_active_ids: tuple[str, ...]
    uncommitted_claim_ids: tuple[str, ...] = ()
    requeued_uncommitted_claim_ids: tuple[str, ...] = ()
    abandoned_in_progress_ids: tuple[str, ...] = ()


class QueueBackend(Protocol):
    name: str

    def enqueue(self, task: Task) -> None:
        ...

    def claim_next(self, *, lanes: list[WorkerLane], worker_id: str) -> ClaimedTask | None:
        ...

    def assert_claim_owner(self, task_id: str, *, worker_id: str) -> None:
        ...

    def acknowledge(self, task_id: str, *, worker_id: str | None = None) -> bool:
        ...

    def size(self, lane: WorkerLane | None = None) -> int:
        ...

    def counts_by_lane(self) -> dict[str, int]:
        ...

    def metrics_by_lane(self) -> dict[str, dict[str, int]]:
        ...

    def reconcile_pending(
        self,
        tasks: list[Task],
        *,
        dry_run: bool = True,
        workers_stopped: bool = False,
    ) -> QueueReconciliationReport:
        ...


class DatabaseQueueBackend:
    name = "database"

    def __init__(self) -> None:
        self.db = ControlPlaneDatabase()

    def enqueue(self, task: Task) -> None:
        query = f"""
            INSERT INTO {TASK_QUEUE_TABLE} (
                task_id, lane, status, claimed_by, enqueued_at, claimed_at
            ) VALUES (
                {self.db.placeholder("task_id")},
                {self.db.placeholder("lane")},
                {self.db.placeholder("status")},
                {self.db.placeholder("claimed_by")},
                {self.db.placeholder("enqueued_at")},
                {self.db.placeholder("claimed_at")}
            )
            ON CONFLICT(task_id) DO UPDATE SET
                lane = excluded.lane,
                status = excluded.status,
                claimed_by = excluded.claimed_by,
                enqueued_at = excluded.enqueued_at,
                claimed_at = excluded.claimed_at
        """
        self.db.execute(
            query,
            {
                "task_id": task.id,
                "lane": task.lane.value,
                "status": "pending",
                "claimed_by": None,
                "enqueued_at": task.created_at or datetime.now(UTC).isoformat(),
                "claimed_at": None,
            },
        )

    def claim_next(self, *, lanes: list[WorkerLane], worker_id: str) -> ClaimedTask | None:
        claimed_at = datetime.now(UTC).isoformat()
        task_id = self.db.claim_task([lane.value for lane in lanes], worker_id, claimed_at)
        if task_id is None:
            return None
        return ClaimedTask(
            task_id=task_id,
            lane=lanes[0],
            worker_id=worker_id,
            claimed_at=claimed_at,
        )

    def assert_claim_owner(self, task_id: str, *, worker_id: str) -> None:
        """The database queue's task transition supplies its ownership fence."""

    def acknowledge(self, task_id: str, *, worker_id: str | None = None) -> bool:
        self.db.acknowledge_task(task_id)
        return True

    def size(self, lane: WorkerLane | None = None) -> int:
        """Return dispatchable database rows; claimed rows are reported by metrics."""
        return self.db.queue_size(lane.value if lane else None)

    def counts_by_lane(self) -> dict[str, int]:
        """Return dispatchable database rows grouped by lane."""
        return self.db.queue_counts_by_lane()

    def metrics_by_lane(self) -> dict[str, dict[str, int]]:
        """Return database queue depth split between pending and claimed rows."""
        query = f"""
            SELECT lane, status, COUNT(*) AS count
            FROM {TASK_QUEUE_TABLE}
            WHERE status IN ('pending', 'claimed')
            GROUP BY lane, status
        """
        metrics: dict[str, dict[str, int]] = {}
        for row in self.db.fetch_all(query, {}):
            lane = str(row["lane"])
            status = str(row["status"])
            count = int(row["count"])
            lane_metrics = metrics.setdefault(
                lane,
                {"queued": 0, "inflight": 0, "total": 0},
            )
            metric = "queued" if status == "pending" else "inflight"
            lane_metrics[metric] += count
            lane_metrics["total"] += count
        return metrics

    def reconcile_pending(
        self,
        tasks: list[Task],
        *,
        dry_run: bool = True,
        workers_stopped: bool = False,
    ) -> QueueReconciliationReport:
        """The database queue shares canonical storage and needs no repair pass."""
        return QueueReconciliationReport(
            dry_run=dry_run,
            removed_orphan_ids=(),
            removed_terminal_ids=(),
            enqueued_missing_ids=(),
            preserved_active_ids=(),
        )


class RedisStreamQueueBackend:
    """Redis Streams dispatch backend with bounded pending-work recovery.

    Redis Streams provides at-least-once delivery. Pending recovery is an
    explicit experimental opt-in because, without execution heartbeats or
    claim tokens, a lease can expire while a healthy long-running worker is
    still active. The claim owner check fences stale *different-worker*
    acknowledgements, but is not an exactly-once external-effect guarantee and
    cannot distinguish a restarted process that reuses the same worker ID.
    """

    name = "redis"
    group = "ai-company-os-workers"
    claim_hash = "ai-company-os:queue:claims"
    default_reclaim_min_idle_ms = 60_000
    _ACK_IF_OWNER = """
local current = redis.call('HGET', KEYS[1], ARGV[1])
if current ~= ARGV[2] then return 0 end
local pending = redis.call('XPENDING', KEYS[2], ARGV[3], ARGV[4], ARGV[4], 1)
if #pending == 0 then return 0 end
if pending[1][2] ~= ARGV[5] then return 0 end
redis.call('XACK', KEYS[2], ARGV[3], ARGV[4])
redis.call('XDEL', KEYS[2], ARGV[4])
redis.call('HDEL', KEYS[1], ARGV[1])
return 1
"""

    def __init__(
        self,
        *,
        url: str | None = None,
        enable_recovery: bool = False,
        reclaim_min_idle_ms: int = default_reclaim_min_idle_ms,
    ) -> None:
        if redis is None:
            raise RuntimeError("redis package is required for AI_COMPANY_OS_QUEUE_BACKEND=redis")
        if reclaim_min_idle_ms <= 0:
            raise ValueError("reclaim_min_idle_ms must be positive")
        self.url = url or os.environ.get(REDIS_URL_ENV_VAR, "redis://127.0.0.1:6379/0")
        self.client = redis.Redis.from_url(self.url, decode_responses=True)
        self.enable_recovery = enable_recovery
        self.reclaim_min_idle_ms = reclaim_min_idle_ms
        self._reclaim_cursors: dict[str, str] = {}

    def enqueue(self, task: Task) -> None:
        stream = self._stream(task.lane)
        self._ensure_group(stream)
        self.client.xadd(
            stream,
            {
                "task_id": task.id,
                "lane": task.lane.value,
                "enqueued_at": task.created_at or datetime.now(UTC).isoformat(),
            },
        )

    def claim_next(self, *, lanes: list[WorkerLane], worker_id: str) -> ClaimedTask | None:
        streams = [self._stream(lane) for lane in lanes]
        for stream in streams:
            self._ensure_group(stream)
        if self.enable_recovery:
            for stream in streams:
                reclaimed = self.client.xautoclaim(
                    stream,
                    self.group,
                    worker_id,
                    self.reclaim_min_idle_ms,
                    start_id=self._reclaim_cursors.get(stream, "0-0"),
                    count=1,
                )
                next_cursor, messages, _ = reclaimed
                self._reclaim_cursors[stream] = str(next_cursor)
                if messages:
                    return self._record_claim(stream, messages[0], worker_id)
        response = self.client.xreadgroup(
            self.group,
            worker_id,
            {stream: ">" for stream in streams},
            count=1,
            block=1,
        )
        if not response:
            return None
        stream, messages = response[0]
        return self._record_claim(str(stream), messages[0], worker_id)

    def assert_claim_owner(self, task_id: str, *, worker_id: str) -> None:
        """Raise unless this worker still owns the live Redis pending entry."""
        claim = self._claim_for(task_id)
        if claim is None or claim[2] != worker_id:
            raise QueueClaimOwnershipError(f"worker {worker_id!r} does not own task {task_id!r}")
        stream, message_id, _ = claim
        pending = self.client.xpending_range(
            stream,
            self.group,
            min=message_id,
            max=message_id,
            count=1,
        )
        if not pending or str(pending[0]["consumer"]) != worker_id:
            raise QueueClaimOwnershipError(f"worker {worker_id!r} lost task {task_id!r}")

    def acknowledge(self, task_id: str, *, worker_id: str | None = None) -> bool:
        """Acknowledge only the currently owned pending entry.

        A caller without a worker ID is refused so a stale completion cannot
        ACK a task reclaimed by another worker.
        """
        if not worker_id:
            return False
        raw_claim = self.client.hget(self.claim_hash, task_id)
        if not raw_claim:
            return False
        claim = self._claim_for(task_id)
        if claim is None or claim[2] != worker_id:
            return False
        stream, message_id, _ = claim
        return bool(
            self.client.eval(
                self._ACK_IF_OWNER,
                2,
                self.claim_hash,
                stream,
                task_id,
                str(raw_claim),
                self.group,
                message_id,
                worker_id,
            )
        )

    def _record_claim(
        self,
        stream: str,
        message: tuple[str, dict[str, str]],
        worker_id: str,
    ) -> ClaimedTask:
        message_id, payload = message
        lane = WorkerLane(str(payload["lane"]))
        task_id = str(payload["task_id"])
        claimed_at = datetime.now(UTC).isoformat()
        self.client.hset(self.claim_hash, task_id, f"{stream}|{message_id}|{worker_id}")
        return ClaimedTask(task_id=task_id, lane=lane, worker_id=worker_id, claimed_at=claimed_at)

    def _claim_for(self, task_id: str) -> tuple[str, str, str] | None:
        raw_claim = self.client.hget(self.claim_hash, task_id)
        if not raw_claim:
            return None
        parts = str(raw_claim).split("|", 2)
        if len(parts) != 3:
            return None
        return parts[0], parts[1], parts[2]

    def size(self, lane: WorkerLane | None = None) -> int:
        """Return outstanding stream entries, including consumer-group pending work."""
        if lane is not None:
            return int(self.client.xlen(self._stream(lane)))
        return sum(self.size(lane) for lane in WorkerLane)

    def counts_by_lane(self) -> dict[str, int]:
        """Return dispatchable stream entries grouped by lane."""
        return {
            lane: lane_metrics["queued"]
            for lane, lane_metrics in self.metrics_by_lane().items()
            if lane_metrics["queued"] > 0
        }

    def metrics_by_lane(self) -> dict[str, dict[str, int]]:
        """Return stream depth split into dispatchable and pending work."""
        metrics: dict[str, dict[str, int]] = {}
        for lane in WorkerLane:
            stream = self._stream(lane)
            if not self.client.exists(stream):
                continue
            total = int(self.client.xlen(stream))
            inflight = 0
            if self._group_exists(stream):
                pending = self.client.xpending(stream, self.group)
                inflight = min(int(pending["pending"]), total)
            if total:
                metrics[lane.value] = {
                    "queued": total - inflight,
                    "inflight": inflight,
                    "total": total,
                }
        return metrics

    def reconcile_pending(
        self,
        tasks: list[Task],
        *,
        dry_run: bool = True,
        workers_stopped: bool = False,
    ) -> QueueReconciliationReport:
        """Plan or repair Redis dispatch from canonical task records.

        Applying repairs requires an explicit stopped-worker maintenance
        guard. Active nonterminal entries are preserved. This method never
        reclaims their ownership; recovery remains a separate explicit opt-in.
        A pending task with a Redis pending-entry list (PEL) claim indicates
        that Redis dispatch claimed it but canonical claiming did not finish.
        It may be reset only while workers are stopped. A canonical in-progress
        task missing a dispatch entry is reported for operator review and is
        never automatically requeued. Blocked tasks and their dispatch entries
        are preserved; resuming blocked work requires a separate explicit
        enqueue/recovery action.
        """
        if not dry_run and not workers_stopped:
            raise ValueError("workers_stopped=True is required to apply Redis reconciliation")
        canonical = {task.id: task for task in tasks}
        seen_by_lane: set[tuple[WorkerLane, str]] = set()
        seen_task_ids: set[str] = set()
        orphan_ids: list[str] = []
        terminal_ids: list[str] = []
        active_ids: list[str] = []
        uncommitted_claim_ids: list[str] = []
        removals: list[tuple[str, str, str]] = []
        uncommitted_removals: list[tuple[str, str, str]] = []
        terminal_statuses = {TaskStatus.COMPLETED, TaskStatus.FAILED}

        for lane in WorkerLane:
            stream = self._stream(lane)
            if not self.client.exists(stream):
                continue
            for message_id, payload in self.client.xrange(stream, "-", "+"):
                task_id = str(payload.get("task_id", ""))
                task = canonical.get(task_id)
                if task is None:
                    orphan_ids.append(task_id or f"{stream}:{message_id}")
                    removals.append((stream, str(message_id), task_id))
                    continue
                if task.status in terminal_statuses:
                    terminal_ids.append(task_id)
                    removals.append((stream, str(message_id), task_id))
                    continue
                if task.status is TaskStatus.PENDING and task.lane is lane:
                    seen_task_ids.add(task_id)
                    if self._is_pending_entry(stream, str(message_id)):
                        uncommitted_claim_ids.append(task_id)
                        uncommitted_removals.append((stream, str(message_id), task_id))
                        continue
                    seen_by_lane.add((lane, task_id))
                    continue
                seen_task_ids.add(task_id)
                active_ids.append(task_id)

        missing = [
            task
            for task in tasks
            if task.status is TaskStatus.PENDING
            and (
                (task.lane, task.id) not in seen_by_lane
                and task.id not in uncommitted_claim_ids
            )
        ]
        pending_repairs = [canonical[task_id] for task_id in sorted(set(uncommitted_claim_ids))]
        abandoned_in_progress_ids = sorted(
            task.id
            for task in tasks
            if task.status is TaskStatus.IN_PROGRESS and task.id not in seen_task_ids
        )
        report = QueueReconciliationReport(
            dry_run=dry_run,
            removed_orphan_ids=tuple(sorted(orphan_ids)),
            removed_terminal_ids=tuple(sorted(terminal_ids)),
            enqueued_missing_ids=tuple(sorted(task.id for task in missing)),
            preserved_active_ids=tuple(sorted(active_ids)),
            uncommitted_claim_ids=tuple(sorted(set(uncommitted_claim_ids))),
            requeued_uncommitted_claim_ids=tuple(sorted(task.id for task in pending_repairs)),
            abandoned_in_progress_ids=tuple(abandoned_in_progress_ids),
        )
        if dry_run:
            return report
        for stream, message_id, task_id in removals:
            self._remove_dispatch_entry(stream, message_id, task_id)
        for stream, message_id, task_id in uncommitted_removals:
            self._remove_dispatch_entry(stream, message_id, task_id)
        for task in [*missing, *pending_repairs]:
            self.enqueue(task)
        return report

    def _remove_dispatch_entry(self, stream: str, message_id: str, task_id: str) -> None:
        if self._group_exists(stream):
            self.client.xack(stream, self.group, message_id)
        self.client.xdel(stream, message_id)
        claim = self._claim_for(task_id)
        if claim is not None and claim[:2] == (stream, message_id):
            self.client.hdel(self.claim_hash, task_id)

    def _is_pending_entry(self, stream: str, message_id: str) -> bool:
        if not self._group_exists(stream):
            return False
        return bool(
            self.client.xpending_range(
                stream,
                self.group,
                min=message_id,
                max=message_id,
                count=1,
            )
        )

    def _group_exists(self, stream: str) -> bool:
        try:
            groups = self.client.xinfo_groups(stream)
        except Exception as exc:
            if "no such key" in str(exc).lower():
                return False
            raise
        return any(str(group.get("name")) == self.group for group in groups)

    def _stream(self, lane: WorkerLane) -> str:
        return f"ai-company-os:queue:{lane.value}"

    def _ensure_group(self, stream: str) -> None:
        try:
            self.client.xgroup_create(stream, self.group, id="0", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise


def active_queue_backend_name() -> str:
    return os.environ.get(QUEUE_BACKEND_ENV_VAR, "database").strip().lower() or "database"


def build_queue_backend() -> QueueBackend:
    backend = active_queue_backend_name()
    if backend == "database":
        return DatabaseQueueBackend()
    if backend == "redis":
        return RedisStreamQueueBackend()
    raise ValueError(f"Unsupported queue backend: {backend}")


class TaskQueue:
    def __init__(self, backend: QueueBackend | None = None) -> None:
        self.backend = backend or build_queue_backend()
        self.db = getattr(self.backend, "db", ControlPlaneDatabase())

    def enqueue(self, task: Task) -> None:
        self.backend.enqueue(task)

    def claim_next(self, *, lanes: list[WorkerLane], worker_id: str) -> ClaimedTask | None:
        return self.backend.claim_next(lanes=lanes, worker_id=worker_id)

    def assert_claim_owner(self, task_id: str, *, worker_id: str) -> None:
        self.backend.assert_claim_owner(task_id, worker_id=worker_id)

    def acknowledge(self, task_id: str, *, worker_id: str | None = None) -> bool:
        return self.backend.acknowledge(task_id, worker_id=worker_id)

    def size(self, lane: WorkerLane | None = None) -> int:
        return self.backend.size(lane)

    def counts_by_lane(self) -> dict[str, int]:
        return self.backend.counts_by_lane()

    def metrics_by_lane(self) -> dict[str, dict[str, int]]:
        return self.backend.metrics_by_lane()

    def reconcile_pending(
        self,
        tasks: list[Task],
        *,
        dry_run: bool = True,
        workers_stopped: bool = False,
    ) -> QueueReconciliationReport:
        return self.backend.reconcile_pending(
            tasks,
            dry_run=dry_run,
            workers_stopped=workers_stopped,
        )
