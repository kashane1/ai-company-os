from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from packages.db.control_plane_db import ControlPlaneDatabase
from packages.db.contracts import TASK_QUEUE_TABLE
from packages.schemas.task import Task
from packages.schemas.task_packet import WorkerLane


@dataclass(frozen=True)
class ClaimedTask:
    task_id: str
    lane: WorkerLane
    worker_id: str
    claimed_at: str


class TaskQueue:
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
        return ClaimedTask(task_id=task_id, lane=lanes[0], worker_id=worker_id, claimed_at=claimed_at)

    def acknowledge(self, task_id: str) -> None:
        self.db.acknowledge_task(task_id)

    def size(self, lane: WorkerLane | None = None) -> int:
        return self.db.queue_size(lane.value if lane else None)
