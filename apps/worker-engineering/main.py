from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from engineering.runner import execute_task
from packages.schemas.task_packet import TaskResult


def execute(task_id: str) -> TaskResult:
    return execute_task(task_id)
