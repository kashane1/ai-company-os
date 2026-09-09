from dataclasses import replace
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.db.worktree_store import WorktreeStore
from packages.schemas.task_run import EngineeringResultClassification
from packages.schemas.worktree import WorktreeMetadata, WorktreeStatus


def task_worktree_path(task_id: str, repo_name: str) -> Path:
    paths = load_runtime_paths()
    return paths.worktrees_root / repo_name / task_id


def finalize_worktree(
    worktree: WorktreeMetadata,
    *,
    classification: EngineeringResultClassification,
    validated_at: str,
) -> WorktreeMetadata:
    """Persist the same terminal worktree contract for engineering and iOS."""
    passed = classification in {
        EngineeringResultClassification.SAFE_FOR_REVIEW,
        EngineeringResultClassification.NO_CHANGE,
    }
    finalized = replace(
        worktree,
        status=WorktreeStatus.COMPLETED if passed else WorktreeStatus.FAILED,
        validated_at=validated_at,
    )
    WorktreeStore().save(finalized)
    return finalized
