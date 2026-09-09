from pathlib import Path
import sqlite3
import threading

from packages.config.settings import ensure_runtime_directories, load_runtime_paths
from packages.db.approval_store import ApprovalStore
from packages.db.goal_store import GoalStore
from packages.db.json_store import JsonStore
from packages.db.task_store import TaskStore
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.schemas.goal import GoalRecord, GoalStatus
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
    assert paths.control_plane_db_path.parent.is_dir()


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

    save_key = store.save(task)
    updated = store.set_status(
        task.id,
        TaskStatus.IN_PROGRESS,
        updated_at="2026-03-30T00:05:00+00:00",
    )

    assert save_key == task.id
    assert store.load(task.id).status is TaskStatus.IN_PROGRESS
    assert updated.updated_at == "2026-03-30T00:05:00+00:00"


def test_goal_store_round_trips_sql_backed_goal_records(isolated_repo_root: Path) -> None:
    store = GoalStore()
    goal = GoalRecord(
        id="goal-1",
        title="Ship control plane",
        summary="Persist goals and tasks.",
        description="Narrow first pass.",
        status=GoalStatus.OPEN,
        created_at="2026-03-30T00:00:00+00:00",
        updated_at="2026-03-30T00:00:00+00:00",
    )

    saved_key = store.save(goal)
    loaded = store.load(goal.id)

    assert saved_key == goal.id
    assert loaded.title == "Ship control plane"
    assert store.list()[0].id == goal.id


def test_approval_store_updates_status_with_decision_notes(isolated_repo_root: Path) -> None:
    store = ApprovalStore()
    record = ApprovalRecord(
        id="approval-1",
        status=ApprovalStatus.PENDING,
        summary="Need approval",
        created_at="2026-03-30T00:00:00+00:00",
        subject_id="release-1",
        action="submit_appstore",
        reviewed_revision="sha256:reviewed-release-inputs",
    )
    store.save(record)

    updated = store.update_status(
        record.id,
        ApprovalStatus.APPROVED,
        decided_by="founder",
        decided_at="2026-03-30T00:10:00+00:00",
        decision_notes="Looks good.",
    )

    assert updated.status is ApprovalStatus.APPROVED
    assert updated.decided_by == "founder"
    assert updated.decision_notes == "Looks good."
    assert store.load(record.id).decided_at == "2026-03-30T00:10:00+00:00"
    assert store.load(record.id).reviewed_revision == "sha256:reviewed-release-inputs"


def test_approval_store_migrates_legacy_records_without_a_reviewed_revision(
    isolated_repo_root: Path,
) -> None:
    db_path = load_runtime_paths().control_plane_db_path
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE approvals (
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
            """
        )
        connection.execute(
            """
            INSERT INTO approvals (
                id, status, summary, created_at, approval_type, subject_type, subject_id, action
            ) VALUES ('legacy-approval', 'approved', 'Legacy record', '2026-09-08T00:00:00+00:00',
                      'legacy', 'task', 'task-1', 'review_task')
            """
        )

    loaded = ApprovalStore().load("legacy-approval")

    assert loaded.reviewed_revision == ""


def test_approval_store_does_not_overwrite_a_terminal_decision(
    isolated_repo_root: Path,
) -> None:
    store = ApprovalStore()
    record = ApprovalRecord(
        id="approval-terminal",
        status=ApprovalStatus.PENDING,
        summary="Need approval",
        created_at="2026-03-30T00:00:00+00:00",
    )
    store.save(record)

    rejected = store.update_status(
        record.id,
        ApprovalStatus.REJECTED,
        decided_by="founder",
        decided_at="2026-03-30T00:10:00+00:00",
        decision_notes="No.",
    )
    later_approval = store.update_status(
        record.id,
        ApprovalStatus.APPROVED,
        decided_by="late-confirmation",
        decided_at="2026-03-30T00:11:00+00:00",
        decision_notes="Too late.",
    )

    assert rejected.status is ApprovalStatus.REJECTED
    assert later_approval.status is ApprovalStatus.REJECTED
    assert store.load(record.id).status is ApprovalStatus.REJECTED


def test_concurrent_approval_decisions_preserve_one_terminal_state(
    isolated_repo_root: Path,
) -> None:
    ApprovalStore().save(
        ApprovalRecord(
            id="approval-concurrent",
            status=ApprovalStatus.PENDING,
            summary="Need approval",
            created_at="2026-03-30T00:00:00+00:00",
        )
    )
    start = threading.Barrier(2)
    outcomes: list[ApprovalStatus] = []
    errors: list[Exception] = []

    def decide(status: ApprovalStatus) -> None:
        try:
            start.wait(timeout=2)
            outcomes.append(
                ApprovalStore().update_status(
                    "approval-concurrent",
                    status,
                    decided_by=status.value,
                ).status
            )
        except Exception as exc:  # asserted below
            errors.append(exc)

    attempts = [
        threading.Thread(target=decide, args=(ApprovalStatus.APPROVED,)),
        threading.Thread(target=decide, args=(ApprovalStatus.REJECTED,)),
    ]
    for attempt in attempts:
        attempt.start()
    for attempt in attempts:
        attempt.join(timeout=3)

    assert not errors
    assert not any(attempt.is_alive() for attempt in attempts)
    assert len(set(outcomes)) == 1
    assert ApprovalStore().load("approval-concurrent").status is outcomes[0]
