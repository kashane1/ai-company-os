from pathlib import Path

from packages.config.settings import ensure_runtime_directories, load_runtime_paths
from packages.db.approval_store import ApprovalStore
from packages.db.json_store import JsonStore
from packages.db.task_store import TaskStore
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.schemas.task import Task
from packages.schemas.task_packet import RiskLevel, TaskStatus, WorkerLane


def test_load_runtime_paths_uses_isolated_repo_root(isolated_repo_root: Path) -> None:
    paths = load_runtime_paths()

    assert paths.repo_root == isolated_repo_root
    assert paths.state_root == isolated_repo_root / "state"
    assert paths.tasks_root == isolated_repo_root / "state" / "checkpoints" / "platform" / "tasks"


def test_ensure_runtime_directories_creates_expected_directories(
    isolated_repo_root: Path,
) -> None:
    paths = ensure_runtime_directories()

    assert paths.engineering_artifacts_root.is_dir()
    assert paths.ios_logs_root.is_dir()
    assert paths.release_records_root.is_dir()


def test_json_store_round_trips_payload(tmp_path: Path) -> None:
    store = JsonStore(tmp_path / "records")

    saved_path = store.save("record-1", {"title": "hello", "count": 2})
    payload = store.load("record-1")

    assert saved_path == tmp_path / "records" / "record-1.json"
    assert payload == {"count": 2, "title": "hello"}


def test_task_store_saves_and_updates_status(isolated_repo_root: Path) -> None:
    store = TaskStore()
    task = Task(
        id="task-eng-1",
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Write tests",
        summary="Add platform tests.",
        task_type="engineering_change",
        risk_level=RiskLevel.LOW,
        created_at="2026-03-30T00:00:00+00:00",
        updated_at="2026-03-30T00:00:00+00:00",
    )

    save_path = store.save(task)
    updated = store.set_status(
        task.id,
        TaskStatus.IN_PROGRESS,
        updated_at="2026-03-30T00:05:00+00:00",
    )

    assert Path(save_path).exists()
    assert store.load(task.id).status is TaskStatus.IN_PROGRESS
    assert updated.updated_at == "2026-03-30T00:05:00+00:00"


def test_approval_store_updates_status_with_decision_notes(isolated_repo_root: Path) -> None:
    store = ApprovalStore()
    record = ApprovalRecord(
        id="approval-1",
        status=ApprovalStatus.PENDING,
        summary="Need approval",
        created_at="2026-03-30T00:00:00+00:00",
        subject_id="release-1",
        action="submit_appstore",
    )
    store.save(record)

    updated = store.update_status(
        record.id,
        ApprovalStatus.APPROVED,
        decided_at="2026-03-30T00:10:00+00:00",
        decision_notes="Looks good.",
    )

    assert updated.status is ApprovalStatus.APPROVED
    assert updated.decision_notes == "Looks good."
    assert store.load(record.id).decided_at == "2026-03-30T00:10:00+00:00"
