from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
ENGINEERING_APP = ROOT / "apps" / "worker-engineering"
for entry in (ROOT, ENGINEERING_APP):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from ios.runner import execute_task
from packages.schemas.task_packet import TaskResult


def execute(task_id: str) -> TaskResult:
    return execute_task(task_id)
