from dataclasses import replace

from packages.config.settings import ensure_runtime_directories
from packages.db.json_store import JsonStore
from packages.schemas.task import Task
from packages.schemas.task_packet import TaskStatus


class TaskStore:
    def __init__(self) -> None:
        paths = ensure_runtime_directories()
        self.store = JsonStore(paths.tasks_root)

    def save(self, task: Task) -> str:
        return str(self.store.save(task.id, task.to_dict()))

    def load(self, task_id: str) -> Task:
        return Task.from_dict(self.store.load(task_id))

    def set_status(self, task_id: str, status: TaskStatus, updated_at: str) -> Task:
        current = self.load(task_id)
        updated = replace(current, status=status, updated_at=updated_at)
        self.save(updated)
        return updated
