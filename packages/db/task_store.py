from dataclasses import replace

from packages.db.contracts import TASKS_TABLE
from packages.db.control_plane_db import ControlPlaneDatabase
from packages.schemas.task import Task
from packages.schemas.task_packet import TaskStatus


class TaskStore:
    def __init__(self) -> None:
        self.db = ControlPlaneDatabase()

    def save(self, task: Task) -> str:
        query = f"""
            INSERT INTO {TASKS_TABLE} (
                id, goal_id, repo_id, lane, title, summary, task_type, product_id,
                status, risk_level, requires_approval, constraints_json, claimed_by,
                claimed_at, started_at, completed_at,
                failed_at, result_summary, error_summary, approval_id, created_at, updated_at
            ) VALUES (
                {self.db.placeholder("id")},
                {self.db.placeholder("goal_id")},
                {self.db.placeholder("repo_id")},
                {self.db.placeholder("lane")},
                {self.db.placeholder("title")},
                {self.db.placeholder("summary")},
                {self.db.placeholder("task_type")},
                {self.db.placeholder("product_id")},
                {self.db.placeholder("status")},
                {self.db.placeholder("risk_level")},
                {self.db.placeholder("requires_approval")},
                {self.db.placeholder("constraints_json")},
                {self.db.placeholder("claimed_by")},
                {self.db.placeholder("claimed_at")},
                {self.db.placeholder("started_at")},
                {self.db.placeholder("completed_at")},
                {self.db.placeholder("failed_at")},
                {self.db.placeholder("result_summary")},
                {self.db.placeholder("error_summary")},
                {self.db.placeholder("approval_id")},
                {self.db.placeholder("created_at")},
                {self.db.placeholder("updated_at")}
            )
            ON CONFLICT(id) DO UPDATE SET
                goal_id = excluded.goal_id,
                repo_id = excluded.repo_id,
                lane = excluded.lane,
                title = excluded.title,
                summary = excluded.summary,
                task_type = excluded.task_type,
                product_id = excluded.product_id,
                status = excluded.status,
                risk_level = excluded.risk_level,
                requires_approval = excluded.requires_approval,
                constraints_json = excluded.constraints_json,
                claimed_by = excluded.claimed_by,
                claimed_at = excluded.claimed_at,
                started_at = excluded.started_at,
                completed_at = excluded.completed_at,
                failed_at = excluded.failed_at,
                result_summary = excluded.result_summary,
                error_summary = excluded.error_summary,
                approval_id = excluded.approval_id,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at
        """
        payload = task.to_dict()
        payload["requires_approval"] = 1 if task.requires_approval else 0
        payload["constraints_json"] = self.db.dump_json(task.constraints)
        payload.pop("constraints")
        self.db.execute(query, payload)
        return task.id

    def load(self, task_id: str) -> Task:
        query = f"""
            SELECT *
            FROM {TASKS_TABLE}
            WHERE id = {self.db.placeholder("id")}
        """
        payload = self.db.fetch_one(query, {"id": task_id})
        if payload is None:
            raise FileNotFoundError(task_id)
        return self._from_row(payload)

    def list_for_goal(self, goal_id: str) -> list[Task]:
        query = f"""
            SELECT *
            FROM {TASKS_TABLE}
            WHERE goal_id = {self.db.placeholder("goal_id")}
            ORDER BY created_at ASC, id ASC
        """
        return [
            self._from_row(payload)
            for payload in self.db.fetch_all(query, {"goal_id": goal_id})
        ]

    def list_recent(self, *, limit: int = 50) -> list[Task]:
        query = f"""
            SELECT *
            FROM {TASKS_TABLE}
            ORDER BY updated_at DESC, created_at DESC, id DESC
            LIMIT {self.db.placeholder("limit")}
        """
        return [
            self._from_row(payload)
            for payload in self.db.fetch_all(query, {"limit": limit})
        ]

    def count_by_status(self) -> dict[str, int]:
        query = f"""
            SELECT status, COUNT(*) AS count
            FROM {TASKS_TABLE}
            GROUP BY status
        """
        rows = self.db.fetch_all(query, {})
        return {str(row["status"]): int(row["count"]) for row in rows}

    def latest_for_lane(self, lane: str) -> Task | None:
        query = f"""
            SELECT *
            FROM {TASKS_TABLE}
            WHERE lane = {self.db.placeholder("lane")}
            ORDER BY updated_at DESC, created_at DESC, id DESC
            LIMIT 1
        """
        payload = self.db.fetch_one(query, {"lane": lane})
        if payload is None:
            return None
        return self._from_row(payload)

    def list_for_lane(self, lane: str) -> list[Task]:
        query = f"""
            SELECT *
            FROM {TASKS_TABLE}
            WHERE lane = {self.db.placeholder("lane")}
            ORDER BY updated_at DESC, created_at DESC, id DESC
        """
        return [self._from_row(payload) for payload in self.db.fetch_all(query, {"lane": lane})]

    def set_status(self, task_id: str, status: TaskStatus, updated_at: str) -> Task:
        current = self.load(task_id)
        updated = replace(current, status=status, updated_at=updated_at)
        self.save(updated)
        return updated

    def claim(self, task_id: str, *, worker_id: str, claimed_at: str) -> Task:
        current = self.load(task_id)
        updated = replace(
            current,
            status=TaskStatus.IN_PROGRESS,
            claimed_by=worker_id,
            claimed_at=claimed_at,
            started_at=claimed_at,
            updated_at=claimed_at,
        )
        self.save(updated)
        return updated

    def complete(
        self,
        task_id: str,
        *,
        summary: str,
        completed_at: str,
        approval_id: str | None = None,
    ) -> Task:
        current = self.load(task_id)
        updated = replace(
            current,
            status=TaskStatus.COMPLETED,
            completed_at=completed_at,
            result_summary=summary,
            approval_id=approval_id,
            updated_at=completed_at,
        )
        self.save(updated)
        return updated

    def fail(self, task_id: str, *, error_summary: str, failed_at: str) -> Task:
        current = self.load(task_id)
        updated = replace(
            current,
            status=TaskStatus.FAILED,
            failed_at=failed_at,
            error_summary=error_summary,
            updated_at=failed_at,
        )
        self.save(updated)
        return updated

    def _from_row(self, payload: dict[str, object]) -> Task:
        payload = dict(payload)
        payload["requires_approval"] = bool(payload.get("requires_approval", 0))
        payload["constraints"] = self.db.load_json(str(payload.pop("constraints_json", "[]")))
        return Task.from_dict(payload)
