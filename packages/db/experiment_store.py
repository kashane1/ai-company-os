"""Control-plane store for validation experiments, with a small lifecycle.

Experiments move planned → approved → running → passed/failed/cancelled. The
allowed transitions are enforced here so an experiment can't, say, jump from
``planned`` straight to ``passed`` and trip the build gate without actually
running. Terminal states stamp ``completed_at``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from packages.db.contracts import EXPERIMENTS_TABLE
from packages.db.control_plane_db import ControlPlaneDatabase
from packages.schemas.experiment import ExperimentRecord, ExperimentStatus

ALLOWED_TRANSITIONS: dict[ExperimentStatus, frozenset[ExperimentStatus]] = {
    ExperimentStatus.PLANNED: frozenset({ExperimentStatus.APPROVED, ExperimentStatus.CANCELLED}),
    ExperimentStatus.APPROVED: frozenset({ExperimentStatus.RUNNING, ExperimentStatus.CANCELLED}),
    ExperimentStatus.RUNNING: frozenset(
        {ExperimentStatus.PASSED, ExperimentStatus.FAILED, ExperimentStatus.CANCELLED}
    ),
    ExperimentStatus.PASSED: frozenset(),
    ExperimentStatus.FAILED: frozenset(),
    ExperimentStatus.CANCELLED: frozenset(),
}

TERMINAL_STATUSES = frozenset(
    {ExperimentStatus.PASSED, ExperimentStatus.FAILED, ExperimentStatus.CANCELLED}
)


class InvalidExperimentTransition(ValueError):
    """Raised when a status change is not a permitted lifecycle transition."""


def is_valid_transition(current: ExperimentStatus, target: ExperimentStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


class ExperimentStore:
    def __init__(self, *, now: Callable[[], datetime] | None = None) -> None:
        self.db = ControlPlaneDatabase()
        self._now = now or (lambda: datetime.now(timezone.utc))

    def save(self, experiment: ExperimentRecord) -> str:
        query = f"""
            INSERT INTO {EXPERIMENTS_TABLE} (
                id, opportunity_id, type, status, metric, threshold,
                record_json, created_at, completed_at
            ) VALUES (
                {self.db.placeholder("id")},
                {self.db.placeholder("opportunity_id")},
                {self.db.placeholder("type")},
                {self.db.placeholder("status")},
                {self.db.placeholder("metric")},
                {self.db.placeholder("threshold")},
                {self.db.placeholder("record_json")},
                {self.db.placeholder("created_at")},
                {self.db.placeholder("completed_at")}
            )
            ON CONFLICT(id) DO UPDATE SET
                opportunity_id = excluded.opportunity_id,
                type = excluded.type,
                status = excluded.status,
                metric = excluded.metric,
                threshold = excluded.threshold,
                record_json = excluded.record_json,
                created_at = excluded.created_at,
                completed_at = excluded.completed_at
        """
        self.db.execute(
            query,
            {
                "id": experiment.id,
                "opportunity_id": experiment.opportunity_id,
                "type": experiment.type.value,
                "status": experiment.status.value,
                "metric": experiment.success_criteria.metric.value,
                "threshold": experiment.success_criteria.threshold,
                "record_json": self.db.dump_json(experiment.to_dict()),
                "created_at": experiment.created_at,
                "completed_at": experiment.completed_at or None,
            },
        )
        return experiment.id

    def get(self, experiment_id: str) -> ExperimentRecord:
        placeholder = self.db.placeholder("id")
        query = f"SELECT record_json FROM {EXPERIMENTS_TABLE} WHERE id = {placeholder}"
        payload = self.db.fetch_one(query, {"id": experiment_id})
        if payload is None:
            raise FileNotFoundError(experiment_id)
        return ExperimentRecord.from_dict(self.db.load_json(str(payload["record_json"])))

    def list(self, *, opportunity_id: str | None = None) -> list[ExperimentRecord]:
        clause = ""
        params: dict[str, object] = {}
        if opportunity_id is not None:
            clause = f" WHERE opportunity_id = {self.db.placeholder('opportunity_id')}"
            params["opportunity_id"] = opportunity_id
        query = (
            f"SELECT record_json FROM {EXPERIMENTS_TABLE}{clause} "
            "ORDER BY created_at DESC, id DESC"
        )
        rows = self.db.fetch_all(query, params)
        return [
            ExperimentRecord.from_dict(self.db.load_json(str(row["record_json"]))) for row in rows
        ]

    def transition(self, experiment_id: str, target: ExperimentStatus) -> ExperimentRecord:
        """Move an experiment to ``target`` if the transition is allowed, persist
        it, and stamp ``completed_at`` on terminal states. Raises
        :class:`InvalidExperimentTransition` otherwise."""
        current = self.get(experiment_id)
        if current.status == target:
            return current
        if not is_valid_transition(current.status, target):
            raise InvalidExperimentTransition(
                f"{current.status.value} -> {target.value} is not a permitted transition"
            )
        payload = current.to_dict()
        payload["status"] = target.value
        if target in TERMINAL_STATUSES and not current.completed_at:
            payload["completed_at"] = self._now().isoformat()
        updated = ExperimentRecord.from_dict(payload)
        self.save(updated)
        return updated
