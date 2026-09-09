#!/usr/bin/env python3
"""Control-plane database operator helpers."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.api.control_plane import ControlPlaneService  # noqa: E402
from packages.config.settings import DATABASE_URL_ENV_VAR, load_runtime_paths  # noqa: E402
from packages.db.contracts import (  # noqa: E402
    APPROVALS_TABLE,
    DISCOVERY_RUNS_TABLE,
    EVENTS_TABLE,
    EXPERIMENTS_TABLE,
    GOALS_TABLE,
    OPPORTUNITIES_TABLE,
    TASK_QUEUE_TABLE,
    TASKS_TABLE,
)
from packages.db.control_plane_db import ControlPlaneDatabase  # noqa: E402
from packages.schemas.task import Task  # noqa: E402
from packages.schemas.task_packet import TaskStatus, WorkerLane  # noqa: E402

TABLES = (
    GOALS_TABLE,
    TASKS_TABLE,
    APPROVALS_TABLE,
    EVENTS_TABLE,
    TASK_QUEUE_TABLE,
    OPPORTUNITIES_TABLE,
    EXPERIMENTS_TABLE,
    DISCOVERY_RUNS_TABLE,
)


def _cmd_status(_: argparse.Namespace) -> int:
    db = ControlPlaneDatabase()
    info = db.health_info()
    print(f"backend: {info['backend']}")
    print(f"dsn: {info['dsn']}")
    print(f"schema: {info['schema']}")
    return 0


def _cmd_init(_: argparse.Namespace) -> int:
    ControlPlaneDatabase().health_info()
    print("control-plane schema ready")
    return 0


def _cmd_migrate_sqlite(args: argparse.Namespace) -> int:
    source = Path(args.source or load_runtime_paths().control_plane_db_path)
    if not source.exists():
        print(f"source sqlite database not found: {source}", file=sys.stderr)
        return 1
    if not os.environ.get(DATABASE_URL_ENV_VAR, "").startswith(("postgres://", "postgresql://")):
        print(
            f"set {DATABASE_URL_ENV_VAR}=postgresql://... before migrating",
            file=sys.stderr,
        )
        return 1

    target = ControlPlaneDatabase()
    copied = 0
    with sqlite3.connect(source) as sqlite:
        sqlite.row_factory = sqlite3.Row
        for table in TABLES:
            if not _sqlite_table_exists(sqlite, table):
                continue
            rows = [dict(row) for row in sqlite.execute(f"SELECT * FROM {table}").fetchall()]
            if not rows:
                continue
            for row in rows:
                _upsert(target, table, row)
            copied += len(rows)
            print(f"{table}: {len(rows)} row(s)")
    print(f"copied {copied} row(s) into {target.config.redacted_dsn}")
    return 0


def _all_canonical_tasks(service: ControlPlaneService) -> list[Task]:
    """Read every lane without the dashboard's bounded recent-task query."""
    return [
        task
        for lane in WorkerLane
        for task in service.tasks.list_for_lane(lane.value)
    ]


def _cmd_reconcile_queue(args: argparse.Namespace) -> int:
    if args.apply and not args.workers_stopped:
        print("--apply requires --workers-stopped", file=sys.stderr)
        return 2
    service = ControlPlaneService()
    with service.tasks.db.transaction():
        report = service.queue.reconcile_pending(
            _all_canonical_tasks(service),
            dry_run=not args.apply,
            workers_stopped=args.workers_stopped,
        )
    print(json.dumps(asdict(report), sort_keys=True))
    return 0


def _cmd_recover_task(args: argparse.Namespace) -> int:
    if not args.reason.strip():
        print("--reason must not be empty", file=sys.stderr)
        return 2
    service = ControlPlaneService()
    try:
        task = service.tasks.load(args.task_id)
    except FileNotFoundError:
        print(f"task not found: {args.task_id}", file=sys.stderr)
        return 1
    if task.status not in {TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED}:
        print("only in-progress or blocked tasks can be recovered", file=sys.stderr)
        return 1
    if not task.goal_id:
        print("task recovery requires a parent goal", file=sys.stderr)
        return 1
    if not args.apply:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "task_id": task.id,
                    "status": task.status.value,
                    "reason": args.reason,
                    "action": "fail old task and create a pending replacement under a child goal",
                },
                sort_keys=True,
            )
        )
        return 0
    if not args.workers_stopped:
        print("--apply requires --workers-stopped", file=sys.stderr)
        return 2
    try:
        failed, recovery_goal, replacement = service.abandon_task(
            task_id=task.id,
            reason=args.reason,
            workers_stopped=args.workers_stopped,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "dry_run": False,
                "abandoned_task_id": failed.id,
                "recovery_goal_id": recovery_goal.id,
                "replacement_task_id": replacement.id,
                "replacement_status": replacement.status.value,
            },
            sort_keys=True,
        )
    )
    return 0


def _sqlite_table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _upsert(db: ControlPlaneDatabase, table: str, row: dict[str, object]) -> None:
    columns = list(row)
    placeholders = ", ".join(db.placeholder(column) for column in columns)
    names = ", ".join(columns)
    conflict = "task_id" if table == TASK_QUEUE_TABLE else "id"
    updates = ", ".join(
        f"{column} = excluded.{column}"
        for column in columns
        if column != conflict
    )
    db.execute(
        f"""
        INSERT INTO {table} ({names})
        VALUES ({placeholders})
        ON CONFLICT({conflict}) DO UPDATE SET {updates}
        """,
        row,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Control-plane DB helpers")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status").set_defaults(func=_cmd_status)
    sub.add_parser("init").set_defaults(func=_cmd_init)
    migrate = sub.add_parser("migrate-sqlite")
    migrate.add_argument("--source", help="source sqlite path (default: runtime control plane)")
    migrate.set_defaults(func=_cmd_migrate_sqlite)
    reconcile = sub.add_parser("reconcile-queue", help="reconcile Redis dispatch from canonical tasks")
    reconcile.add_argument("--apply", action="store_true", help="apply the reviewed repair plan")
    reconcile.add_argument(
        "--workers-stopped",
        action="store_true",
        help="confirm every worker is stopped before applying repairs",
    )
    reconcile.set_defaults(func=_cmd_reconcile_queue)
    recover = sub.add_parser("recover-task", help="replace an abandoned stopped-worker task")
    recover.add_argument("task_id")
    recover.add_argument("--reason", required=True)
    recover.add_argument("--apply", action="store_true", help="fail the old task and create replacement")
    recover.add_argument(
        "--workers-stopped",
        action="store_true",
        help="confirm every worker is stopped before applying recovery",
    )
    recover.set_defaults(func=_cmd_recover_task)
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
