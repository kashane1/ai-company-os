#!/usr/bin/env python3
"""Control-plane database operator helpers."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
