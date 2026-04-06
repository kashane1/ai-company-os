from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
ENGINEERING_APP = ROOT / "apps" / "worker-engineering"
for entry in (ROOT, ENGINEERING_APP):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from engineering.runner import execute_task, result_as_dict
from apps.api.control_plane import ControlPlaneService
from packages.config.products import load_product_configs
from packages.config.settings import ensure_runtime_directories, load_runtime_paths
from packages.db.approval_store import ApprovalStore
from packages.db.product_store import ProductStore
from packages.db.release_store import ReleaseStore
from packages.db.task_store import TaskStore
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.schemas.product import (
    ProductArtifactRecord,
    ProductArtifactStatus,
    ProductArtifactType,
    ProductRecord,
    ProductStatus,
)
from packages.schemas.release import (
    BuildCandidate,
    BuildStatus,
    MetadataDraft,
    MetadataStatus,
    ReleaseRecord,
    ReleaseStatus,
    ScreenshotSet,
    ScreenshotStatus,
    StoreChannelStatus,
)
from packages.schemas.task import Task
from packages.schemas.task_packet import RiskLevel, WorkerLane

FISHING_FOUNDERS_PACK_SOURCE = "/Users/simons/Desktop/founders-pack-fishing-journal.rtf"
APPSTORE_RELEASE_PREP_ACTION = "prepare_testflight"
FISHING_RELEASE_ID_PREFIX = "release-fishing-logbook-v"


def create_engineering_task(
    title: str,
    summary: str,
    repo_id: str,
    task_id: str | None = None,
) -> Task:
    now = datetime.now(UTC).isoformat()
    resolved_task_id = task_id or datetime.now(UTC).strftime("task-eng-%Y%m%d%H%M%S")
    task = Task(
        id=resolved_task_id,
        repo_id=repo_id,
        lane=WorkerLane.ENGINEERING,
        title=title,
        summary=summary,
        task_type="engineering_change",
        risk_level=RiskLevel.LOW,
        constraints=[
            "Operate only inside the managed worktree.",
            "Persist every step of the run to state.",
            "Do not require approval for this low-risk scaffold task.",
            "Leave all changes uncommitted for manual inspection.",
        ],
        created_at=now,
        updated_at=now,
    )
    TaskStore().save(task)
    return task


def build_product_artifacts(product_id: str) -> list[ProductArtifactRecord]:
    docs_root = ROOT / "docs" / "products" / product_id
    return [
        ProductArtifactRecord(
            artifact_type=ProductArtifactType.FOUNDER_BRIEF,
            path=str(docs_root / "founder-brief.md"),
            source_origin=FISHING_FOUNDERS_PACK_SOURCE,
            status=ProductArtifactStatus.IMPORTED,
        ),
        ProductArtifactRecord(
            artifact_type=ProductArtifactType.PRODUCT_BRIEF,
            path=str(docs_root / "product-brief.md"),
            derived_from=ProductArtifactType.FOUNDER_BRIEF,
        ),
        ProductArtifactRecord(
            artifact_type=ProductArtifactType.MVP_SPEC,
            path=str(docs_root / "mvp-spec.md"),
            derived_from=ProductArtifactType.PRODUCT_BRIEF,
        ),
        ProductArtifactRecord(
            artifact_type=ProductArtifactType.BACKLOG,
            path=str(docs_root / "backlog.md"),
            derived_from=ProductArtifactType.MVP_SPEC,
        ),
        ProductArtifactRecord(
            artifact_type=ProductArtifactType.IOS_ARCHITECTURE,
            path=str(docs_root / "ios-architecture.md"),
            derived_from=ProductArtifactType.MVP_SPEC,
        ),
        ProductArtifactRecord(
            artifact_type=ProductArtifactType.APPSTORE_POSITIONING,
            path=str(docs_root / "app-store-positioning.md"),
            derived_from=ProductArtifactType.PRODUCT_BRIEF,
        ),
        ProductArtifactRecord(
            artifact_type=ProductArtifactType.INSIGHT_RULES,
            path=str(docs_root / "insight-rules.md"),
            derived_from=ProductArtifactType.MVP_SPEC,
        ),
        ProductArtifactRecord(
            artifact_type=ProductArtifactType.INSIGHT_ACCEPTANCE_CASES,
            path=str(docs_root / "insight-acceptance-cases.md"),
            derived_from=ProductArtifactType.INSIGHT_RULES,
        ),
    ]


def register_product(product_id: str) -> ProductRecord:
    config = load_product_configs()[product_id]
    now = datetime.now(UTC).isoformat()
    product = ProductRecord(
        id=config.id,
        name=config.name,
        slug=config.slug,
        platform=config.platform,
        repo_id=config.repo_id,
        source_path=config.source_path,
        docs_root=config.docs_root,
        status=ProductStatus.READY_FOR_IMPLEMENTATION,
        artifacts=build_product_artifacts(product_id),
        created_at=now,
        updated_at=now,
    )
    ProductStore().save(product)
    return product


def create_ios_task(
    title: str,
    summary: str,
    *,
    product_id: str = "fishing-logbook",
    repo_id: str = "fishing-logbook-ios",
    task_type: str = "ios_feature",
    task_id: str | None = None,
) -> Task:
    now = datetime.now(UTC).isoformat()
    resolved_task_id = task_id or datetime.now(UTC).strftime("task-ios-%Y%m%d%H%M%S")
    task = Task(
        id=resolved_task_id,
        repo_id=repo_id,
        lane=WorkerLane.IOS,
        title=title,
        summary=summary,
        task_type=task_type,
        product_id=product_id,
        risk_level=RiskLevel.MEDIUM,
        constraints=[
            "Operate only inside the managed worktree.",
            "Persist every step of the run to state.",
            "Use docs/products/fishing-logbook as the product source of truth.",
            "Do not implement release automation in this lane.",
            "Leave all changes uncommitted for manual inspection.",
        ],
        created_at=now,
        updated_at=now,
    )
    TaskStore().save(task)
    return task


def scaffold_release_state(
    *,
    product_id: str = "fishing-logbook",
    repo_id: str = "fishing-logbook-ios",
    version: str = "0.1.0",
    build_number: str = "1",
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    release_store = ReleaseStore()
    docs_root = ROOT / "docs" / "products" / product_id

    build_candidate = BuildCandidate(
        id=f"build-{product_id}-{version}-b{build_number}",
        product_id=product_id,
        repo_id=repo_id,
        source_task_run_id="pending-ios-build",
        version=version,
        build_number=build_number,
        artifact_paths=[],
        status=BuildStatus.DRAFT,
        created_at=now,
    )
    metadata_draft = MetadataDraft(
        id=f"metadata-{product_id}-en-US",
        product_id=product_id,
        locale="en-US",
        path=str(docs_root / "app-store-positioning.md"),
        status=MetadataStatus.READY,
        created_at=now,
    )
    screenshot_set = ScreenshotSet(
        id=f"screenshots-{product_id}-iphone",
        product_id=product_id,
        locale="en-US",
        device_family="iphone",
        asset_paths=[],
        status=ScreenshotStatus.DRAFT,
        created_at=now,
    )
    release_record = ReleaseRecord(
        id=f"release-{product_id}-v{version}",
        product_id=product_id,
        build_candidate_id=build_candidate.id,
        metadata_draft_id=metadata_draft.id,
        screenshot_set_id=screenshot_set.id,
        testflight_status=StoreChannelStatus.NOT_STARTED,
        appstore_status=StoreChannelStatus.NOT_STARTED,
        status=ReleaseStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )

    release_store.save_build_candidate(build_candidate)
    release_store.save_metadata_draft(metadata_draft)
    release_store.save_screenshot_set(screenshot_set)
    release_store.save_release_record(release_record)

    return {
        "build_candidate": build_candidate.to_dict(),
        "metadata_draft": metadata_draft.to_dict(),
        "screenshot_set": screenshot_set.to_dict(),
        "release_record": release_record.to_dict(),
    }


def ensure_release_state(
    release_id: str,
    *,
    build_number: str = "1",
) -> dict[str, object]:
    release_store = ReleaseStore()
    try:
        release_record = release_store.load_release_record(release_id)
    except FileNotFoundError:
        if not release_id.startswith(FISHING_RELEASE_ID_PREFIX):
            raise ValueError(
                f"Unsupported release id format: {release_id}. "
                f"Expected prefix {FISHING_RELEASE_ID_PREFIX}."
            )
        version = release_id.removeprefix(FISHING_RELEASE_ID_PREFIX)
        release_state = scaffold_release_state(version=version, build_number=build_number)
        return {
            "release_id": release_id,
            "release_state_status": "scaffolded",
            "release_record": release_state["release_record"],
        }
    return {
        "release_id": release_record.id,
        "release_state_status": "existing",
        "release_record": release_record.to_dict(),
    }


def seed_appstore_release_prep(
    *,
    release_id: str,
    action: str = APPSTORE_RELEASE_PREP_ACTION,
    build_number: str = "1",
) -> dict[str, object]:
    if action != APPSTORE_RELEASE_PREP_ACTION:
        raise ValueError(f"Unsupported App Store seed action: {action}")

    release_state = ensure_release_state(release_id, build_number=build_number)
    service = ControlPlaneService()
    goal = service.create_goal(
        title=f"Prepare TestFlight state for {release_id}",
        summary=f"Queue one App Store release-prep task for {release_id}.",
        description=(
            "Operator-seeded local runtime work for the App Store lane. "
            f"Action: {action}."
        ),
    )
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="fishing-logbook-ios",
        lane=WorkerLane.APPSTORE,
        title=f"Prepare TestFlight state for {release_id}",
        summary=f"Use the App Store lane to prepare release state for {release_id}.",
        task_type="appstore_release",
        product_id="fishing-logbook",
        constraints=[
            f"release_id={release_id}",
            f"release_action={action}",
        ],
    )
    return {
        "goal_id": goal.id,
        "task_id": task.id,
        "release_id": release_id,
        "action": action,
        "task_status": task.status.value,
        "release_state_status": release_state["release_state_status"],
        "next_command": "./scripts/runtime status",
    }


def create_release_approval(
    release_id: str,
    action: str,
    *,
    summary: str | None = None,
) -> ApprovalRecord:
    approval = ApprovalRecord(
        id=f"approval-{release_id}-{action}",
        status=ApprovalStatus.PENDING,
        summary=summary or f"Approval required for release action {action}.",
        created_at=datetime.now(UTC).isoformat(),
        approval_type="release_action",
        subject_type="release",
        subject_id=release_id,
        action=action,
    )
    ApprovalStore().save(approval)
    return approval


def bootstrap_fishing_product() -> dict[str, object]:
    product = register_product("fishing-logbook")
    release_state = scaffold_release_state()
    return {
        "product": product.to_dict(),
        "release_state": release_state,
    }


def run_engineering_task(task: Task) -> dict[str, object]:
    ensure_runtime_directories()
    result = execute_task(task.id)
    paths = load_runtime_paths()
    persisted_task = TaskStore().load(task.id)
    return {
        "route": "worker-engineering",
        "task_input": task.to_dict(),
        "task_record": persisted_task.to_dict(),
        "result": result_as_dict(result),
        "records": {
            "task": str(paths.tasks_root / f"{task.id}.json"),
            "task_run": str(paths.task_runs_root / f"{result.run_id}.json"),
            "repo": str(paths.repo_records_root / f"{task.repo_id}.json"),
            "worktree": str(paths.worktree_records_root / f"worktree-{task.id}.json"),
            "approval": str(paths.approvals_root / f"{result.approval_id}.json")
            if result.approval_id
            else None,
            "review_artifact": result.review_artifact_path,
        },
    }


def demo_platform_flow() -> dict[str, object]:
    task = create_engineering_task(
        title="Trace the first engineering task flow",
        summary=(
            "Update docs/engineering-flow.md with one short sentence noting that task runs persist "
            "Codex stdout, stderr, exit code, and diff artifacts. Keep the change minimal."
        ),
        repo_id="ai-company-os",
    )
    return {
        "engineering_demo": run_engineering_task(task),
        "fishing_product": bootstrap_fishing_product(),
    }
