from __future__ import annotations

from packages.db.control_plane_db import ControlPlaneDatabase
from packages.db.contracts import EVENTS_TABLE
from packages.schemas.event import EventRecord


class EventStore:
    def __init__(self) -> None:
        self.db = ControlPlaneDatabase()

    def append(self, event: EventRecord) -> str:
        query = f"""
            INSERT INTO {EVENTS_TABLE} (
                id, event_type, subject_type, subject_id, goal_id, task_id, approval_id, payload_json, created_at
            ) VALUES (
                {self.db.placeholder("id")},
                {self.db.placeholder("event_type")},
                {self.db.placeholder("subject_type")},
                {self.db.placeholder("subject_id")},
                {self.db.placeholder("goal_id")},
                {self.db.placeholder("task_id")},
                {self.db.placeholder("approval_id")},
                {self.db.placeholder("payload_json")},
                {self.db.placeholder("created_at")}
            )
        """
        payload = event.to_dict()
        payload["payload_json"] = self.db.dump_json(payload["payload"])
        payload.pop("payload")
        self.db.execute(query, payload)
        return event.id

    def list(self) -> list[EventRecord]:
        query = f"SELECT * FROM {EVENTS_TABLE} ORDER BY created_at ASC, id ASC"
        return [self._from_row(payload) for payload in self.db.fetch_all(query, {})]

    def list_for_subject(self, subject_type: str, subject_id: str) -> list[EventRecord]:
        query = f"""
            SELECT *
            FROM {EVENTS_TABLE}
            WHERE subject_type = {self.db.placeholder("subject_type")}
              AND subject_id = {self.db.placeholder("subject_id")}
            ORDER BY created_at ASC, id ASC
        """
        return [
            self._from_row(payload)
            for payload in self.db.fetch_all(
                query,
                {"subject_type": subject_type, "subject_id": subject_id},
            )
        ]

    def latest(self) -> EventRecord | None:
        query = f"""
            SELECT *
            FROM {EVENTS_TABLE}
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        """
        payload = self.db.fetch_one(query, {})
        if payload is None:
            return None
        return self._from_row(payload)

    def _from_row(self, payload: dict[str, object]) -> EventRecord:
        payload = dict(payload)
        payload["payload"] = self.db.load_json(str(payload.pop("payload_json")))
        return EventRecord.from_dict(payload)
