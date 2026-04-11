from pathlib import Path

from apps.api import platform
from apps.api.control_plane import ControlPlaneService
from packages.db.approval_store import ApprovalStore
from packages.db.product_store import ProductStore
from packages.db.release_store import ReleaseStore
from packages.db.task_store import TaskStore
from packages.schemas.approval import ApprovalStatus
from packages.schemas.product import ProductStatus
from packages.schemas.release import BuildStatus, MetadataStatus, ReleaseStatus, ScreenshotStatus
from packages.schemas.task_packet import RiskLevel, WorkerLane


def test_create_engineering_and_ios_tasks_persist_to_isolated_state(
    isolated_repo_root: Path,
) -> None:
    engineering_task = platform.create_engineering_task(
        "Add tests",
        "Create initial coverage harness.",
        repo_id="ai-company-os",
        task_id="task-eng-123",
    )
    ios_task = platform.create_ios_task(
        "Test fishing app",
        "Add logic tests for the app.",
        task_id="task-ios-123",
    )
    store = TaskStore()

    assert engineering_task.lane is WorkerLane.ENGINEERING
    assert engineering_task.risk_level is RiskLevel.LOW
    assert store.load("task-eng-123").title == "Add tests"

    assert ios_task.lane is WorkerLane.IOS
    assert ios_task.risk_level is RiskLevel.MEDIUM
    assert store.load("task-ios-123").product_id == "catchbook"


def test_register_product_uses_isolated_repo_root(
    isolated_repo_root: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform, "ROOT", isolated_repo_root)

    product = platform.register_product("catchbook")
    stored = ProductStore().load("catchbook")

    assert product.status is ProductStatus.READY_FOR_IMPLEMENTATION
    assert stored.source_path == str(isolated_repo_root / "products" / "catchbook-ios")
    assert stored.docs_root == str(isolated_repo_root / "docs" / "products" / "catchbook")
    assert stored.artifacts[0].path == str(
        isolated_repo_root / "docs" / "products" / "catchbook" / "founder-brief.md"
    )


def test_scaffold_release_state_and_create_release_approval_persist_records(
    isolated_repo_root: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform, "ROOT", isolated_repo_root)

    payload = platform.scaffold_release_state(version="1.2.0", build_number="42")
    approval = platform.create_release_approval(
        "release-catchbook-v1.2.0",
        "submit_appstore",
    )
    release_store = ReleaseStore()

    build_candidate = release_store.load_build_candidate("build-catchbook-1.2.0-b42")
    metadata_draft = release_store.load_metadata_draft("metadata-catchbook-en-US")
    screenshot_set = release_store.load_screenshot_set("screenshots-catchbook-iphone")
    release_record = release_store.load_release_record("release-catchbook-v1.2.0")
    stored_approval = ApprovalStore().load(approval.id)

    assert payload["release_record"]["id"] == "release-catchbook-v1.2.0"
    assert build_candidate.status is BuildStatus.DRAFT
    assert metadata_draft.status is MetadataStatus.READY
    assert screenshot_set.status is ScreenshotStatus.DRAFT
    assert release_record.status is ReleaseStatus.DRAFT
    assert stored_approval.status is ApprovalStatus.PENDING
    assert stored_approval.action == "submit_appstore"


def test_seed_appstore_release_prep_scaffolds_release_and_queues_task(
    isolated_repo_root: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform, "ROOT", isolated_repo_root)

    summary = platform.seed_appstore_release_prep(
        release_id="release-catchbook-v1.3.0",
        build_number="7",
    )
    release_store = ReleaseStore()
    task_store = TaskStore()
    service = ControlPlaneService()

    release_record = release_store.load_release_record("release-catchbook-v1.3.0")
    task = task_store.load(summary["task_id"])
    goal = service.list_goals()[0]

    assert summary == {
        "action": "prepare_testflight",
        "goal_id": goal.id,
        "next_command": "./scripts/runtime status",
        "release_id": "release-catchbook-v1.3.0",
        "release_state_status": "scaffolded",
        "task_id": task.id,
        "task_status": "pending",
    }
    assert release_record.id == "release-catchbook-v1.3.0"
    assert task.lane is WorkerLane.APPSTORE
    assert task.task_type == "appstore_release"
    assert task.constraints == [
        "release_id=release-catchbook-v1.3.0",
        "release_action=prepare_testflight",
    ]
    assert goal.title == "Prepare TestFlight state for release-catchbook-v1.3.0"


def test_seed_appstore_release_prep_reuses_existing_release_record(
    isolated_repo_root: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform, "ROOT", isolated_repo_root)
    platform.scaffold_release_state(version="1.4.0", build_number="2")

    summary = platform.seed_appstore_release_prep(
        release_id="release-catchbook-v1.4.0",
        build_number="99",
    )
    release_store = ReleaseStore()
    build_candidate = release_store.load_build_candidate("build-catchbook-1.4.0-b2")
    task = TaskStore().load(summary["task_id"])

    assert summary["release_state_status"] == "existing"
    assert build_candidate.build_number == "2"
    assert task.constraints == [
        "release_id=release-catchbook-v1.4.0",
        "release_action=prepare_testflight",
    ]
