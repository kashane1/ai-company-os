from dataclasses import replace

from packages.db.control_plane_db import ControlPlaneDatabase
from packages.db.contracts import GOALS_TABLE
from packages.schemas.goal import GoalRecord, GoalStatus


class GoalStore:
    def __init__(self) -> None:
        self.db = ControlPlaneDatabase()

    def save(self, goal: GoalRecord) -> str:
        query = f"""
            INSERT INTO {GOALS_TABLE} (
                id, title, summary, description, status, parent_goal_id, created_at, updated_at, completed_at
            ) VALUES (
                {self.db.placeholder("id")},
                {self.db.placeholder("title")},
                {self.db.placeholder("summary")},
                {self.db.placeholder("description")},
                {self.db.placeholder("status")},
                {self.db.placeholder("parent_goal_id")},
                {self.db.placeholder("created_at")},
                {self.db.placeholder("updated_at")},
                {self.db.placeholder("completed_at")}
            )
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                summary = excluded.summary,
                description = excluded.description,
                status = excluded.status,
                parent_goal_id = excluded.parent_goal_id,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                completed_at = excluded.completed_at
        """
        payload = goal.to_dict()
        self.db.execute(query, payload)
        return goal.id

    def load(self, goal_id: str) -> GoalRecord:
        query = f"""
            SELECT *
            FROM {GOALS_TABLE}
            WHERE id = {self.db.placeholder("id")}
        """
        payload = self.db.fetch_one(query, {"id": goal_id})
        if payload is None:
            raise FileNotFoundError(goal_id)
        return GoalRecord.from_dict(payload)

    def list(self) -> list[GoalRecord]:
        query = f"SELECT * FROM {GOALS_TABLE} ORDER BY created_at DESC, id DESC"
        return [GoalRecord.from_dict(payload) for payload in self.db.fetch_all(query, {})]

    def set_status(
        self,
        goal_id: str,
        status: GoalStatus,
        *,
        updated_at: str,
        completed_at: str | None = None,
    ) -> GoalRecord:
        current = self.load(goal_id)
        updated = replace(
            current,
            status=status,
            updated_at=updated_at,
            completed_at=completed_at,
        )
        self.save(updated)
        return updated
