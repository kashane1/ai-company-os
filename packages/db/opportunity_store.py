"""Control-plane store for discovered opportunities.

A queryable home for the opportunity inbox. Core columns (status, score,
confidence) stay first-class for ranking and filtering; the full record is kept
verbatim in ``record_json`` so nested evidence/signals survive a round trip.
Mirrors the GoalStore pattern so it works on both the SQLite and Postgres
backends without change.
"""

from __future__ import annotations

from packages.db.contracts import OPPORTUNITIES_TABLE
from packages.db.control_plane_db import ControlPlaneDatabase
from packages.schemas.opportunity import OpportunityRecord, OpportunityStatus


class OpportunityStore:
    def __init__(self) -> None:
        self.db = ControlPlaneDatabase()

    def save(self, opportunity: OpportunityRecord) -> str:
        query = f"""
            INSERT INTO {OPPORTUNITIES_TABLE} (
                id, title, audience, connector, status, score, confidence,
                record_json, created_at, updated_at
            ) VALUES (
                {self.db.placeholder("id")},
                {self.db.placeholder("title")},
                {self.db.placeholder("audience")},
                {self.db.placeholder("connector")},
                {self.db.placeholder("status")},
                {self.db.placeholder("score")},
                {self.db.placeholder("confidence")},
                {self.db.placeholder("record_json")},
                {self.db.placeholder("created_at")},
                {self.db.placeholder("updated_at")}
            )
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                audience = excluded.audience,
                connector = excluded.connector,
                status = excluded.status,
                score = excluded.score,
                confidence = excluded.confidence,
                record_json = excluded.record_json,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at
        """
        self.db.execute(
            query,
            {
                "id": opportunity.id,
                "title": opportunity.title,
                "audience": opportunity.audience,
                "connector": opportunity.source.connector,
                "status": opportunity.status.value,
                "score": opportunity.score,
                "confidence": opportunity.confidence,
                "record_json": self.db.dump_json(opportunity.to_dict()),
                "created_at": opportunity.created_at,
                "updated_at": opportunity.updated_at,
            },
        )
        return opportunity.id

    def get(self, opportunity_id: str) -> OpportunityRecord:
        placeholder = self.db.placeholder("id")
        query = f"SELECT record_json FROM {OPPORTUNITIES_TABLE} WHERE id = {placeholder}"
        payload = self.db.fetch_one(query, {"id": opportunity_id})
        if payload is None:
            raise FileNotFoundError(opportunity_id)
        return OpportunityRecord.from_dict(self.db.load_json(str(payload["record_json"])))

    def exists(self, opportunity_id: str) -> bool:
        placeholder = self.db.placeholder("id")
        query = f"SELECT 1 FROM {OPPORTUNITIES_TABLE} WHERE id = {placeholder}"
        return self.db.fetch_one(query, {"id": opportunity_id}) is not None

    def list(self, *, status: OpportunityStatus | None = None) -> list[OpportunityRecord]:
        clause = ""
        params: dict[str, object] = {}
        if status is not None:
            clause = f" WHERE status = {self.db.placeholder('status')}"
            params["status"] = status.value
        # Rank: highest score first, NULL scores last, newest as tiebreaker.
        # Portable NULL handling across SQLite and Postgres.
        query = f"""
            SELECT record_json
            FROM {OPPORTUNITIES_TABLE}{clause}
            ORDER BY (score IS NULL) ASC, score DESC, created_at DESC, id DESC
        """
        rows = self.db.fetch_all(query, params)
        return [
            OpportunityRecord.from_dict(self.db.load_json(str(row["record_json"]))) for row in rows
        ]
