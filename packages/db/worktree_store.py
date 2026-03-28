from packages.config.settings import ensure_runtime_directories
from packages.db.json_store import JsonStore
from packages.schemas.worktree import WorktreeMetadata


class WorktreeStore:
    def __init__(self) -> None:
        paths = ensure_runtime_directories()
        self.store = JsonStore(paths.worktree_records_root)

    def save(self, worktree: WorktreeMetadata) -> str:
        return str(self.store.save(worktree.id, worktree.to_dict()))

    def load(self, worktree_id: str) -> WorktreeMetadata:
        return WorktreeMetadata.from_dict(self.store.load(worktree_id))
