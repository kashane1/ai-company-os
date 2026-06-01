from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from packages.config.settings import QUEUE_BACKEND_ENV_VAR, REDIS_URL_ENV_VAR
from packages.db.contracts import TASK_QUEUE_TABLE
from packages.db.control_plane_db import ControlPlaneDatabase
from packages.schemas.task import Task
from packages.schemas.task_packet import WorkerLane

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


class QueueBackend(Protocol):
    name: str

    def enqueue(self, task: Task) -> None:
        ...

    def claim_next(self, *, lanes: list[WorkerLane], worker_id: str) -> ClaimedTask | None:
        ...

    def acknowledge(self, task_id: str) -> None:
        ...

    def size(self, lane: WorkerLane | None = None) -> int:
        ...

    def counts_by_lane(self) -> dict[str, int]:
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

    def acknowledge(self, task_id: str) -> None:
        self.db.acknowledge_task(task_id)

    def size(self, lane: WorkerLane | None = None) -> int:
        return self.db.queue_size(lane.value if lane else None)

    def counts_by_lane(self) -> dict[str, int]:
        return self.db.queue_counts_by_lane()


class RedisStreamQueueBackend:
    """Redis Streams dispatch backend with Postgres/SQLite as canonical task store."""

    name = "redis"
    group = "ai-company-os-workers"
    claim_hash = "ai-company-os:queue:claims"

    def __init__(self, *, url: str | None = None) -> None:
        if redis is None:
            raise RuntimeError("redis package is required for AI_COMPANY_OS_QUEUE_BACKEND=redis")
        self.url = url or os.environ.get(REDIS_URL_ENV_VAR, "redis://127.0.0.1:6379/0")
        self.client = redis.Redis.from_url(self.url, decode_responses=True)

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
        streams = {self._stream(lane): ">" for lane in lanes}
        for stream in streams:
            self._ensure_group(stream)
        response = self.client.xreadgroup(
            self.group,
            worker_id,
            streams,
            count=1,
            block=1,
        )
        if not response:
            return None
        stream, messages = response[0]
        message_id, payload = messages[0]
        lane = WorkerLane(str(payload["lane"]))
        task_id = str(payload["task_id"])
        claimed_at = datetime.now(UTC).isoformat()
        self.client.hset(self.claim_hash, task_id, f"{stream}|{message_id}")
        return ClaimedTask(task_id=task_id, lane=lane, worker_id=worker_id, claimed_at=claimed_at)

    def acknowledge(self, task_id: str) -> None:
        claim = self.client.hget(self.claim_hash, task_id)
        if not claim:
            return
        stream, message_id = str(claim).split("|", 1)
        self.client.xack(stream, self.group, message_id)
        self.client.xdel(stream, message_id)
        self.client.hdel(self.claim_hash, task_id)

    def size(self, lane: WorkerLane | None = None) -> int:
        if lane is not None:
            return int(self.client.xlen(self._stream(lane)))
        return sum(self.size(lane) for lane in WorkerLane)

    def counts_by_lane(self) -> dict[str, int]:
        return {
            lane.value: count
            for lane in WorkerLane
            if (count := self.size(lane)) > 0
        }

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

    def acknowledge(self, task_id: str) -> None:
        self.backend.acknowledge(task_id)

    def size(self, lane: WorkerLane | None = None) -> int:
        return self.backend.size(lane)

    def counts_by_lane(self) -> dict[str, int]:
        return self.backend.counts_by_lane()
