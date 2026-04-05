from dataclasses import replace

from packages.db.control_plane_db import ControlPlaneDatabase
from packages.db.contracts import APPROVALS_TABLE
from packages.schemas.approval import ApprovalRecord, ApprovalStatus


class ApprovalStore:
    def __init__(self) -> None:
        self.db = ControlPlaneDatabase()

    def save(self, approval: ApprovalRecord) -> str:
        query = f"""
            INSERT INTO {APPROVALS_TABLE} (
                id, status, summary, created_at, task_id, task_run_id, approval_type,
                review_artifact_path, subject_type, subject_id, action, decided_by, decided_at, decision_notes
            ) VALUES (
                {self.db.placeholder("id")},
                {self.db.placeholder("status")},
                {self.db.placeholder("summary")},
                {self.db.placeholder("created_at")},
                {self.db.placeholder("task_id")},
                {self.db.placeholder("task_run_id")},
                {self.db.placeholder("approval_type")},
                {self.db.placeholder("review_artifact_path")},
                {self.db.placeholder("subject_type")},
                {self.db.placeholder("subject_id")},
                {self.db.placeholder("action")},
                {self.db.placeholder("decided_by")},
                {self.db.placeholder("decided_at")},
                {self.db.placeholder("decision_notes")}
            )
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                summary = excluded.summary,
                created_at = excluded.created_at,
                task_id = excluded.task_id,
                task_run_id = excluded.task_run_id,
                approval_type = excluded.approval_type,
                review_artifact_path = excluded.review_artifact_path,
                subject_type = excluded.subject_type,
                subject_id = excluded.subject_id,
                action = excluded.action,
                decided_by = excluded.decided_by,
                decided_at = excluded.decided_at,
                decision_notes = excluded.decision_notes
        """
        self.db.execute(query, approval.to_dict())
        return approval.id

    def load(self, approval_id: str) -> ApprovalRecord:
        query = f"""
            SELECT *
            FROM {APPROVALS_TABLE}
            WHERE id = {self.db.placeholder("id")}
        """
        payload = self.db.fetch_one(query, {"id": approval_id})
        if payload is None:
            raise FileNotFoundError(approval_id)
        return ApprovalRecord.from_dict(payload)

    def update_status(
        self,
        approval_id: str,
        status: ApprovalStatus,
        *,
        decided_by: str | None = None,
        decided_at: str | None = None,
        decision_notes: str | None = None,
    ) -> ApprovalRecord:
        current = self.load(approval_id)
        updated = replace(
            current,
            status=status,
            decided_by=decided_by,
            decided_at=decided_at,
            decision_notes=decision_notes,
        )
        self.save(updated)
        return updated
