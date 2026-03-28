from packages.config.settings import ensure_runtime_directories
from packages.db.json_store import JsonStore
from packages.schemas.task_run import TaskRun


class TaskRunStore:
    def __init__(self) -> None:
        paths = ensure_runtime_directories()
        self.store = JsonStore(paths.task_runs_root)

    def save(self, task_run: TaskRun) -> str:
        return str(self.store.save(task_run.id, task_run.to_dict()))

    def load(self, run_id: str) -> TaskRun:
        return TaskRun.from_dict(self.store.load(run_id))
