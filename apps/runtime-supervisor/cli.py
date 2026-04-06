from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from main import load_supervisor_status, request_supervisor_shutdown
from apps.api.platform import APPSTORE_RELEASE_PREP_ACTION, seed_appstore_release_prep
from packages.config.settings import ensure_runtime_directories
from packages.db.event_store import EventStore
from packages.db.release_store import ReleaseStore
from packages.db.task_store import TaskStore
from packages.schemas.task_packet import WorkerLane


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate the local runtime supervisor.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("start")
    subparsers.add_parser("status")
    subparsers.add_parser("stop")
    inspect_parser = subparsers.add_parser("inspect-appstore-release")
    inspect_parser.add_argument("--release-id")
    seed_parser = subparsers.add_parser("seed-appstore-release")
    seed_parser.add_argument("--release-id", required=True)
    seed_parser.add_argument(
        "--action",
        default=APPSTORE_RELEASE_PREP_ACTION,
        choices=(APPSTORE_RELEASE_PREP_ACTION,),
    )
    seed_parser.add_argument("--build-number", default="1")
    return parser


def start_supervisor_process() -> dict[str, object]:
    status = load_supervisor_status()
    if status.get("state") == "running":
        return {
            "runtime_state": "running",
            "started": False,
            "reason": "already_running",
            "workers": status.get("workers", []),
        }

    paths = ensure_runtime_directories()
    runtime_logs_root = paths.logs_root / "runtime-supervisor"
    runtime_logs_root.mkdir(parents=True, exist_ok=True)
    log_path = runtime_logs_root / "supervisor.log"

    with log_path.open("a", encoding="utf-8") as handle:
        process = subprocess.Popen(
            [sys.executable, str(APP_ROOT / "main.py")],
            cwd=str(paths.repo_root),
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )

    started_status = status
    for _ in range(10):
        time.sleep(0.1)
        started_status = load_supervisor_status()
        if started_status.get("state") == "running":
            break

    return {
        "runtime_state": started_status.get("state", "not_started"),
        "started": True,
        "supervisor_pid": process.pid,
        "log_path": str(log_path),
        "workers": started_status.get("workers", []),
    }


def build_work_summary() -> dict[str, object]:
    task_store = TaskStore()
    event_store = EventStore()
    release_store = ReleaseStore()

    status_counts = task_store.count_by_status()
    tasks_by_status = {
        "pending": status_counts.get("pending", 0),
        "running": status_counts.get("in_progress", 0),
        "blocked": status_counts.get("blocked", 0),
        "completed": status_counts.get("completed", 0),
        "failed": status_counts.get("failed", 0),
    }

    latest_event = None
    event = event_store.latest()
    if event is not None:
        latest_event = {
            "event_type": event.event_type,
            "task_id": event.task_id,
            "worker_id": event.payload.get("worker_id"),
            "lane": event.payload.get("lane"),
            "created_at": event.created_at,
            "source": "control_plane.events",
        }

    latest_tasks: dict[str, dict[str, object]] = {}
    release_summary = None
    for lane in (WorkerLane.ENGINEERING, WorkerLane.IOS, WorkerLane.APPSTORE):
        task = task_store.latest_for_lane(lane.value)
        if task is None:
            continue
        latest_tasks[lane.value] = {
            "task_id": task.id,
            "task_type": task.task_type,
            "status": task.status.value,
            "updated_at": task.updated_at,
            "source": "control_plane.tasks",
        }
        if lane is WorkerLane.APPSTORE:
            release_id = next(
                (
                    constraint.split("=", 1)[1]
                    for constraint in task.constraints
                    if constraint.startswith("release_id=")
                ),
                None,
            )
            if release_id:
                try:
                    release = release_store.load_release_record(release_id)
                except FileNotFoundError:
                    release_summary = {
                        "release_id": release_id,
                        "state": "missing",
                        "source": "lane_owned.release_records",
                    }
                else:
                    release_summary = {
                        "release_id": release.id,
                        "status": release.status.value,
                        "testflight_status": release.testflight_status.value,
                        "source": "lane_owned.release_records",
                    }

    return {
        "sources": {
            "task_state": "control_plane.sqlite.tasks",
            "event_state": "control_plane.sqlite.events",
            "release_state": "lane_owned.json.release_records",
        },
        "tasks_by_status": tasks_by_status,
        "latest_event": latest_event,
        "latest_tasks_by_lane": latest_tasks,
        "release_summary": release_summary,
    }


def build_status_payload() -> dict[str, object]:
    status = load_supervisor_status()
    status["work_summary"] = build_work_summary()
    return status


def _extract_release_id(constraints: list[str]) -> str | None:
    return next(
        (
            constraint.split("=", 1)[1]
            for constraint in constraints
            if constraint.startswith("release_id=")
        ),
        None,
    )


def inspect_appstore_release(*, release_id: str | None = None) -> dict[str, object]:
    paths = ensure_runtime_directories()
    task_store = TaskStore()
    event_store = EventStore()
    release_store = ReleaseStore()

    tasks = task_store.list_for_lane(WorkerLane.APPSTORE.value)
    if release_id is not None:
        tasks = [task for task in tasks if _extract_release_id(task.constraints) == release_id]

    if not tasks:
        return {
            "found": False,
            "release_id": release_id,
            "sources": {
                "task_state": "control_plane.sqlite.tasks",
                "event_state": "control_plane.sqlite.events",
                "release_state": "lane_owned.json.release_records",
                "runtime_logs": "state/logs/runtime-supervisor/*.log",
            },
            "log_paths": {
                "worker_appstore": str(paths.logs_root / "runtime-supervisor" / "worker-appstore.log"),
                "supervisor": str(paths.logs_root / "runtime-supervisor" / "supervisor.log"),
            },
            "message": "No matching App Store task found.",
        }

    task = tasks[0]
    resolved_release_id = _extract_release_id(task.constraints)
    events = event_store.list_for_subject("task", task.id)
    latest_event = events[-1] if events else None

    release_summary = None
    if resolved_release_id is not None:
        try:
            release = release_store.load_release_record(resolved_release_id)
        except FileNotFoundError:
            release_summary = {
                "release_id": resolved_release_id,
                "status": "missing",
                "testflight_status": None,
                "source": "lane_owned.release_records",
            }
        else:
            release_summary = {
                "release_id": release.id,
                "status": release.status.value,
                "testflight_status": release.testflight_status.value,
                "source": "lane_owned.release_records",
            }

    return {
        "found": True,
        "release_id": resolved_release_id,
        "task": {
            "task_id": task.id,
            "task_type": task.task_type,
            "status": task.status.value,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "source": "control_plane.tasks",
        },
        "latest_event": {
            "event_type": latest_event.event_type,
            "created_at": latest_event.created_at,
            "task_id": latest_event.task_id,
            "worker_id": latest_event.payload.get("worker_id"),
            "lane": latest_event.payload.get("lane"),
            "source": "control_plane.events",
        }
        if latest_event is not None
        else None,
        "release": release_summary,
        "log_paths": {
            "worker_appstore": str(paths.logs_root / "runtime-supervisor" / "worker-appstore.log"),
            "supervisor": str(paths.logs_root / "runtime-supervisor" / "supervisor.log"),
        },
        "sources": {
            "task_state": "control_plane.sqlite.tasks",
            "event_state": "control_plane.sqlite.events",
            "release_state": "lane_owned.json.release_records",
            "runtime_logs": "state/logs/runtime-supervisor/*.log",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "start":
        print(json.dumps(start_supervisor_process(), indent=2, sort_keys=True))
        return 0

    if args.command == "status":
        print(json.dumps(build_status_payload(), indent=2, sort_keys=True))
        return 0

    if args.command == "stop":
        status = load_supervisor_status()
        response = {
            "runtime_state": status.get("state", "not_started"),
            "stop_requested": True,
            "request": request_supervisor_shutdown(),
            "workers": status.get("workers", []),
        }
        print(json.dumps(response, indent=2, sort_keys=True))
        return 0

    if args.command == "seed-appstore-release":
        summary = seed_appstore_release_prep(
            release_id=args.release_id,
            action=args.action,
            build_number=args.build_number,
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    if args.command == "inspect-appstore-release":
        print(json.dumps(inspect_appstore_release(release_id=args.release_id), indent=2, sort_keys=True))
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
