from packages.config.settings import ensure_runtime_directories
from packages.db.json_store import JsonStore
from packages.schemas.repo import RepoRecord


class RepoStore:
    def __init__(self) -> None:
        paths = ensure_runtime_directories()
        self.store = JsonStore(paths.repo_records_root)

    def save(self, repo: RepoRecord) -> str:
        return str(self.store.save(repo.id, repo.to_dict()))

    def load(self, repo_id: str) -> RepoRecord:
        return RepoRecord.from_dict(self.store.load(repo_id))
