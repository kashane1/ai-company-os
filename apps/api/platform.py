from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
ENGINEERING_APP = ROOT / "apps" / "worker-engineering"
for entry in (ROOT, ENGINEERING_APP):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from engineering.runner import execute_task, result_as_dict
from packages.config.settings import ensure_runtime_directories, load_runtime_paths
from packages.db.task_store import TaskStore
from packages.schemas.task import Task
from packages.schemas.task_packet import RiskLevel, WorkerLane


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
    return run_engineering_task(task)
