from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from apps.api.control_plane import ControlPlaneService
from apps.api.platform import scaffold_release_state
from packages.db.release_store import ReleaseStore
from packages.db.task_store import TaskStore
from packages.schemas.task_packet import TaskStatus, WorkerLane


def load_runtime_supervisor_cli():
    module_path = Path(__file__).resolve().parents[3] / "apps" / "runtime-supervisor" / "cli.py"
    spec = importlib.util.spec_from_file_location("runtime_supervisor_cli", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_runtime_supervisor_main():
    module_path = Path(__file__).resolve().parents[3] / "apps" / "runtime-supervisor" / "main.py"
    spec = importlib.util.spec_from_file_location("runtime_supervisor_main_for_cli", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid


def test_runtime_supervisor_cli_starts_supervisor_process(
    isolated_repo_root: Path,
    capsys,
    monkeypatch,
) -> None:
    runtime_supervisor_cli = load_runtime_supervisor_cli()
    statuses = iter(
        [
            {"state": "not_started", "workers": []},
            {
                "state": "running",
                "workers": [
                    {"lane": "engineering", "worker_id": "worker-engineering", "state": "running"}
                ],
            },
        ]
    )
    spawned_commands: list[list[str]] = []

    monkeypatch.setattr(runtime_supervisor_cli, "load_supervisor_status", lambda: next(statuses))
    monkeypatch.setattr(
        runtime_supervisor_cli.subprocess,
        "Popen",
        lambda command, **kwargs: (
            spawned_commands.append(command),
            FakeProcess(pid=4242),
        )[1],
    )
    monkeypatch.setattr(runtime_supervisor_cli.time, "sleep", lambda seconds: None)

    exit_code = runtime_supervisor_cli.main(["start"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["runtime_state"] == "running"
    assert payload["started"] is True
    assert payload["supervisor_pid"] == 4242
    assert payload["workers"][0]["lane"] == "engineering"
    assert spawned_commands[0][1].endswith("apps/runtime-supervisor/main.py")


def test_runtime_supervisor_cli_reports_not_started_when_no_status_exists(
    isolated_repo_root: Path,
    capsys,
) -> None:
    runtime_supervisor_cli = load_runtime_supervisor_cli()

    exit_code = runtime_supervisor_cli.main(["status"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["state"] == "not_started"
    assert payload["workers"] == []
    assert payload["work_summary"]["tasks_by_status"] == {
        "blocked": 0,
        "completed": 0,
        "failed": 0,
        "pending": 0,
        "running": 0,
    }
    assert payload["work_summary"]["latest_event"] is None
    assert payload["work_summary"]["latest_tasks_by_lane"] == {}
    assert payload["work_summary"]["release_summary"] is None


def test_runtime_supervisor_cli_reports_last_known_worker_states(
    isolated_repo_root: Path,
    capsys,
) -> None:
    runtime_supervisor_main = load_runtime_supervisor_main()
    runtime_supervisor_cli = load_runtime_supervisor_cli()

    status_payload = {
        "state": "running",
        "started_at": "2026-04-05T00:00:00+00:00",
        "updated_at": "2026-04-05T00:01:00+00:00",
        "workers": [
            {
                "lane": "engineering",
                "worker_id": "worker-engineering",
                "pid": 1001,
                "state": "running",
                "last_known_status": "running",
                "started_at": "2026-04-05T00:00:00+00:00",
                "exited_at": None,
                "exit_code": None,
            }
        ],
    }
    paths = runtime_supervisor_main.ensure_runtime_directories()
    status_path = paths.platform_state_root / "runtime-supervisor-status.json"
    status_path.write_text(json.dumps(status_payload), encoding="utf-8")

    exit_code = runtime_supervisor_cli.main(["status"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["state"] == "running"
    assert payload["workers"][0]["lane"] == "engineering"
    assert payload["workers"][0]["last_known_status"] == "running"


def test_runtime_supervisor_cli_requests_clean_shutdown(
    isolated_repo_root: Path,
    capsys,
) -> None:
    runtime_supervisor_main = load_runtime_supervisor_main()
    runtime_supervisor_cli = load_runtime_supervisor_cli()
    paths = runtime_supervisor_main.ensure_runtime_directories()
    status_path = paths.platform_state_root / "runtime-supervisor-status.json"
    status_path.write_text(
        json.dumps(
            {
                "state": "running",
                "workers": [
                    {"lane": "engineering", "worker_id": "worker-engineering", "state": "running"}
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = runtime_supervisor_cli.main(["stop"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    stop_request_path = paths.platform_state_root / "runtime-supervisor-stop.json"
    request_payload = json.loads(stop_request_path.read_text())

    assert exit_code == 0
    assert payload["runtime_state"] == "running"
    assert payload["stop_requested"] is True
    assert payload["workers"][0]["lane"] == "engineering"
    assert request_payload["reason"] == "operator_requested_shutdown"


def test_runtime_supervisor_cli_seeds_appstore_release_and_prints_summary(
    isolated_repo_root: Path,
    capsys,
) -> None:
    runtime_supervisor_cli = load_runtime_supervisor_cli()

    exit_code = runtime_supervisor_cli.main(
        [
            "seed-appstore-release",
            "--release-id",
            "release-fishing-logbook-v0.9.0",
            "--action",
            "prepare_testflight",
            "--build-number",
            "8",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    release_record = ReleaseStore().load_release_record("release-fishing-logbook-v0.9.0")
    task = TaskStore().load(payload["task_id"])

    assert exit_code == 0
    assert payload["release_id"] == "release-fishing-logbook-v0.9.0"
    assert payload["action"] == "prepare_testflight"
    assert payload["task_status"] == "pending"
    assert payload["release_state_status"] == "scaffolded"
    assert payload["next_command"] == "./scripts/runtime status"
    assert release_record.id == "release-fishing-logbook-v0.9.0"
    assert task.constraints == [
        "release_id=release-fishing-logbook-v0.9.0",
        "release_action=prepare_testflight",
    ]


def test_runtime_supervisor_cli_inspect_appstore_release_reports_no_match(
    isolated_repo_root: Path,
    capsys,
) -> None:
    runtime_supervisor_cli = load_runtime_supervisor_cli()

    exit_code = runtime_supervisor_cli.main(
        ["inspect-appstore-release", "--release-id", "release-fishing-logbook-v9.9.9"]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["found"] is False
    assert payload["release_id"] == "release-fishing-logbook-v9.9.9"
    assert payload["message"] == "No matching App Store task found."
    assert payload["log_paths"]["worker_appstore"].endswith("state/logs/runtime-supervisor/worker-appstore.log")
    assert payload["sources"]["task_state"] == "control_plane.sqlite.tasks"


def test_runtime_supervisor_cli_inspect_appstore_release_reports_latest_overall(
    isolated_repo_root: Path,
    capsys,
) -> None:
    runtime_supervisor_cli = load_runtime_supervisor_cli()
    service = ControlPlaneService()
    goal = service.create_goal(title="Inspect latest", summary="Inspect latest")
    older = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="fishing-logbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Older task",
        summary="Older task",
        task_type="appstore_release",
        constraints=["release_id=release-fishing-logbook-v0.3.0", "release_action=prepare_testflight"],
    )
    newer = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="fishing-logbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Newer task",
        summary="Newer task",
        task_type="appstore_release",
        constraints=["release_id=release-fishing-logbook-v0.4.0", "release_action=prepare_testflight"],
    )

    exit_code = runtime_supervisor_cli.main(["inspect-appstore-release"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["found"] is True
    assert payload["release_id"] == "release-fishing-logbook-v0.4.0"
    assert payload["task"]["task_id"] == newer.id
    assert payload["task"]["task_type"] == "appstore_release"
    assert payload["task"]["status"] == "pending"
    assert payload["task"]["created_at"] == newer.created_at
    assert payload["task"]["updated_at"] == newer.updated_at
    assert payload["latest_event"]["event_type"] == "task_created"
    assert payload["latest_event"]["task_id"] == newer.id
    assert older.id != newer.id


def test_runtime_supervisor_cli_inspect_appstore_release_filters_by_release_and_reports_release_state(
    isolated_repo_root: Path,
    capsys,
) -> None:
    runtime_supervisor_cli = load_runtime_supervisor_cli()
    service = ControlPlaneService()
    release_state = scaffold_release_state(version="0.5.0", build_number="6")
    release_id = release_state["release_record"]["id"]
    goal = service.create_goal(title="Inspect release", summary="Inspect release")
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="fishing-logbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Release task",
        summary="Release task",
        task_type="appstore_release",
        constraints=[f"release_id={release_id}", "release_action=prepare_testflight"],
    )
    claimed = service.claim_task(lane=WorkerLane.APPSTORE, worker_id="worker-appstore")
    assert claimed is not None
    service.submit_task_result(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="Prepared release state for action prepare_testflight.",
        worker_id="worker-appstore",
    )

    exit_code = runtime_supervisor_cli.main(["inspect-appstore-release", "--release-id", release_id])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["found"] is True
    assert payload["release_id"] == release_id
    assert payload["task"]["task_id"] == task.id
    assert payload["task"]["status"] == "completed"
    assert payload["latest_event"]["event_type"] == "task_completed"
    assert payload["latest_event"]["worker_id"] == "worker-appstore"
    assert payload["release"] == {
        "release_id": release_id,
        "source": "lane_owned.release_records",
        "status": "draft",
        "testflight_status": "not_started",
    }
    assert payload["log_paths"]["supervisor"].endswith("state/logs/runtime-supervisor/supervisor.log")


def test_runtime_supervisor_cli_reports_queued_task_in_work_summary(
    isolated_repo_root: Path,
    capsys,
) -> None:
    runtime_supervisor_cli = load_runtime_supervisor_cli()
    service = ControlPlaneService()
    goal = service.create_goal(title="Queue task", summary="Queue task summary")
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="fishing-logbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Prepare TestFlight",
        summary="Queued appstore task",
        task_type="appstore_release",
        constraints=["release_id=release-fishing-logbook-v0.1.9", "release_action=prepare_testflight"],
    )

    exit_code = runtime_supervisor_cli.main(["status"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["work_summary"]["tasks_by_status"]["pending"] == 1
    assert payload["work_summary"]["latest_event"]["event_type"] == "task_created"
    assert payload["work_summary"]["latest_event"]["task_id"] == task.id
    assert payload["work_summary"]["latest_tasks_by_lane"]["appstore"] == {
        "source": "control_plane.tasks",
        "status": "pending",
        "task_id": task.id,
        "task_type": "appstore_release",
        "updated_at": task.updated_at,
    }
    assert payload["work_summary"]["release_summary"] == {
        "release_id": "release-fishing-logbook-v0.1.9",
        "source": "lane_owned.release_records",
        "state": "missing",
    }


def test_runtime_supervisor_cli_reports_completed_task_latest_event_and_release_summary(
    isolated_repo_root: Path,
    capsys,
) -> None:
    runtime_supervisor_cli = load_runtime_supervisor_cli()
    service = ControlPlaneService()
    release_state = scaffold_release_state(version="0.2.0", build_number="4")
    release_id = release_state["release_record"]["id"]
    goal = service.create_goal(title="Run task", summary="Run task summary")
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="fishing-logbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Prepare TestFlight",
        summary="Complete appstore task",
        task_type="appstore_release",
        constraints=[f"release_id={release_id}", "release_action=prepare_testflight"],
    )
    claimed = service.claim_task(lane=WorkerLane.APPSTORE, worker_id="worker-appstore")
    assert claimed is not None
    service.submit_task_result(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="Prepared release state for action prepare_testflight.",
        worker_id="worker-appstore",
    )

    exit_code = runtime_supervisor_cli.main(["status"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["work_summary"]["tasks_by_status"] == {
        "blocked": 0,
        "completed": 1,
        "failed": 0,
        "pending": 0,
        "running": 0,
    }
    assert payload["work_summary"]["latest_event"]["event_type"] == "task_completed"
    assert payload["work_summary"]["latest_event"]["task_id"] == task.id
    assert payload["work_summary"]["latest_event"]["worker_id"] == "worker-appstore"
    assert payload["work_summary"]["latest_event"]["lane"] is None
    assert payload["work_summary"]["latest_tasks_by_lane"]["appstore"]["status"] == "completed"
    assert payload["work_summary"]["latest_tasks_by_lane"]["appstore"]["task_id"] == task.id
    assert payload["work_summary"]["release_summary"] == {
        "release_id": release_id,
        "source": "lane_owned.release_records",
        "status": "draft",
        "testflight_status": "not_started",
    }


def test_runtime_supervisor_cli_reports_latest_task_per_lane(
    isolated_repo_root: Path,
    capsys,
) -> None:
    runtime_supervisor_cli = load_runtime_supervisor_cli()
    service = ControlPlaneService()
    goal = service.create_goal(title="Lane coverage", summary="Lane coverage")
    engineering = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Engineering task",
        summary="Engineering task summary",
        task_type="engineering_change",
    )
    ios = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="fishing-logbook-ios",
        lane=WorkerLane.IOS,
        title="iOS task",
        summary="iOS task summary",
        task_type="ios_change",
    )

    exit_code = runtime_supervisor_cli.main(["status"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["work_summary"]["latest_tasks_by_lane"]["engineering"]["task_id"] == engineering.id
    assert payload["work_summary"]["latest_tasks_by_lane"]["engineering"]["task_type"] == "engineering_change"
    assert payload["work_summary"]["latest_tasks_by_lane"]["ios"]["task_id"] == ios.id
    assert payload["work_summary"]["latest_tasks_by_lane"]["ios"]["task_type"] == "ios_change"
