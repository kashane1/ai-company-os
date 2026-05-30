from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from packages.config.settings import DATABASE_URL_ENV_VAR, load_runtime_paths
from packages.db.connection import open_platform_db
from packages.db.contracts import (
    APPROVALS_TABLE,
    DISCOVERY_RUNS_TABLE,
    EVENTS_TABLE,
    EXPERIMENTS_TABLE,
    GOALS_TABLE,
    OPPORTUNITIES_TABLE,
    TASK_QUEUE_TABLE,
    TASKS_TABLE,
)

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - exercised only when postgres is configured.
    psycopg = None
    dict_row = None


@dataclass(frozen=True)
class ControlPlaneDatabaseConfig:
    backend: str
    dsn: str


class ControlPlaneDatabase:
    def __init__(self) -> None:
        self.config = self._load_config()

    def _load_config(self) -> ControlPlaneDatabaseConfig:
        paths = load_runtime_paths()
        dsn = Path(paths.control_plane_db_path).as_posix()
        raw_url = os.environ.get(DATABASE_URL_ENV_VAR)
        if not raw_url:
            return ControlPlaneDatabaseConfig(backend="sqlite", dsn=dsn)

        parsed = urlparse(raw_url)
        if parsed.scheme in {"postgres", "postgresql"}:
            return ControlPlaneDatabaseConfig(backend="postgres", dsn=raw_url)
        if parsed.scheme == "sqlite":
            sqlite_path = parsed.path or dsn
            return ControlPlaneDatabaseConfig(backend="sqlite", dsn=sqlite_path)
        raise ValueError(f"Unsupported database scheme for control plane: {parsed.scheme}")

    def placeholder(self, name: str) -> str:
        if self.config.backend == "postgres":
            return f"%({name})s"
        return f":{name}"

    @contextmanager
    def connection(self):
        if self.config.backend == "postgres":
            if psycopg is None:
                raise RuntimeError(
                    "psycopg is required when AI_COMPANY_OS_DATABASE_URL points to Postgres."
                )
            with psycopg.connect(self.config.dsn, row_factory=dict_row) as connection:
                self.ensure_schema(connection)
                yield connection
                connection.commit()
            return

        db_path = Path(self.config.dsn)
        # Route through the canonical platform bootstrap (Phase 0.5b).
        # Applies WAL, busy_timeout=30000, synchronous=NORMAL, and the
        # rest of the platform-standard pragmas consistently. See
        # packages/db/connection.py for the full rationale.
        connection = open_platform_db(db_path)
        connection.row_factory = sqlite3.Row
        try:
            self.ensure_schema(connection)
            yield connection
            connection.commit()
        finally:
            connection.close()

    def ensure_schema(self, connection: Any) -> None:
        integer_pk = (
            "INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY"
            if self.config.backend == "postgres"
            else "INTEGER PRIMARY KEY AUTOINCREMENT"
        )
        statements = [
            f"""
            CREATE TABLE IF NOT EXISTS {GOALS_TABLE} (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                parent_goal_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TASKS_TABLE} (
                id TEXT PRIMARY KEY,
                goal_id TEXT,
                repo_id TEXT NOT NULL,
                lane TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                task_type TEXT NOT NULL,
                product_id TEXT,
                status TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                requires_approval INTEGER NOT NULL,
                constraints_json TEXT NOT NULL,
                claimed_by TEXT,
                claimed_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                failed_at TEXT,
                result_summary TEXT,
                error_summary TEXT,
                approval_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {APPROVALS_TABLE} (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                task_id TEXT,
                task_run_id TEXT,
                approval_type TEXT NOT NULL,
                review_artifact_path TEXT,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                action TEXT NOT NULL,
                decided_by TEXT,
                decided_at TEXT,
                decision_notes TEXT
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {EVENTS_TABLE} (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                goal_id TEXT,
                task_id TEXT,
                approval_id TEXT,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TASK_QUEUE_TABLE} (
                id {integer_pk},
                task_id TEXT NOT NULL UNIQUE,
                lane TEXT NOT NULL,
                status TEXT NOT NULL,
                claimed_by TEXT,
                enqueued_at TEXT NOT NULL,
                claimed_at TEXT
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {OPPORTUNITIES_TABLE} (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                audience TEXT NOT NULL,
                connector TEXT NOT NULL,
                status TEXT NOT NULL,
                score REAL,
                confidence REAL,
                record_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {EXPERIMENTS_TABLE} (
                id TEXT PRIMARY KEY,
                opportunity_id TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT NOT NULL,
                metric TEXT NOT NULL,
                threshold REAL NOT NULL,
                record_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {DISCOVERY_RUNS_TABLE} (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                signals_ingested INTEGER NOT NULL,
                opportunities_touched INTEGER NOT NULL,
                record_json TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT
            )
            """,
        ]
        cursor = connection.cursor()
        for statement in statements:
            cursor.execute(statement)

    def execute(self, query: str, params: dict[str, object]) -> None:
        with self.connection() as connection:
            connection.cursor().execute(query, params)

    def fetch_one(self, query: str, params: dict[str, object]) -> dict[str, object] | None:
        with self.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return self._row_to_dict(row)

    def fetch_all(self, query: str, params: dict[str, object]) -> list[dict[str, object]]:
        with self.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def claim_task(self, lanes: Sequence[str], worker_id: str, claimed_at: str) -> str | None:
        lane_params = {f"lane_{index}": lane for index, lane in enumerate(lanes)}
        lane_clause = ", ".join(self.placeholder(name) for name in lane_params)
        query = f"""
            SELECT task_id
            FROM {TASK_QUEUE_TABLE}
            WHERE status = {self.placeholder("status")} AND lane IN ({lane_clause})
            ORDER BY enqueued_at ASC, id ASC
            LIMIT 1
        """
        params = {"status": "pending", **lane_params}

        with self.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row is None:
                return None
            task_id = self._row_to_dict(row)["task_id"]
            update_query = f"""
                UPDATE {TASK_QUEUE_TABLE}
                SET status = {self.placeholder("claimed_status")},
                    claimed_by = {self.placeholder("claimed_by")},
                    claimed_at = {self.placeholder("claimed_at")}
                WHERE task_id = {self.placeholder("task_id")}
                  AND status = {self.placeholder("pending_status")}
            """
            cursor.execute(
                update_query,
                {
                    "claimed_status": "claimed",
                    "claimed_by": worker_id,
                    "claimed_at": claimed_at,
                    "task_id": task_id,
                    "pending_status": "pending",
                },
            )
            if cursor.rowcount != 1:
                return None
            return str(task_id)

    def acknowledge_task(self, task_id: str) -> None:
        query = f"""
            DELETE FROM {TASK_QUEUE_TABLE}
            WHERE task_id = {self.placeholder("task_id")}
        """
        self.execute(query, {"task_id": task_id})

    def queue_size(self, lane: str | None = None) -> int:
        params: dict[str, object] = {}
        clause = ""
        if lane:
            clause = f" AND lane = {self.placeholder('lane')}"
            params["lane"] = lane
        query = f"""
            SELECT COUNT(*) AS count
            FROM {TASK_QUEUE_TABLE}
            WHERE status = 'pending'{clause}
        """
        row = self.fetch_one(query, params)
        return int(row["count"]) if row else 0

    def dump_json(self, payload: object) -> str:
        return json.dumps(payload, sort_keys=True)

    def load_json(self, payload: str) -> object:
        return json.loads(payload)

    def _row_to_dict(self, row: Any) -> dict[str, object] | None:
        if row is None:
            return None
        if isinstance(row, sqlite3.Row):
            return {key: row[key] for key in row.keys()}
        return dict(row)
