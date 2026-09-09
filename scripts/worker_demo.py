#!/usr/bin/env python3
"""Run a real local ledger worker on synthetic input in a new disposable root."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="new output directory; existing paths refused")
    parser.add_argument("--exercise-failure", action="store_true",
                        help="cause a local write failure, preserve it, then run a replacement task")
    args = parser.parse_args()
    if args.output:
        output = args.output.resolve()
        if output.exists():
            parser.error(f"output already exists: {output}")
        output.mkdir(parents=True)
    else:
        output = Path(tempfile.mkdtemp(prefix="ai-company-os-worker-demo-"))

    # Establish isolation before importing application modules or loading config.
    os.environ["AI_COMPANY_OS_REPO_ROOT"] = str(output)
    os.environ["AI_COMPANY_OS_QUEUE_BACKEND"] = "database"
    os.environ.pop("AI_COMPANY_OS_DATABASE_URL", None)
    os.environ.pop("AI_COMPANY_OS_REDIS_URL", None)

    def local_only(event: str, _args: tuple) -> None:
        if event in {"socket.connect", "socket.connect_ex", "subprocess.Popen", "os.system"}:
            raise RuntimeError(f"offline worker demo refuses {event}")

    sys.addaudithook(local_only)
    source = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(source))
    from apps.api.control_plane import ControlPlaneService
    from packages.schemas.task_packet import TaskStatus, WorkerLane

    worker_path = source / "apps/worker-outreach/main.py"
    spec = importlib.util.spec_from_file_location("employer_outreach_worker", worker_path)
    assert spec and spec.loader
    worker = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = worker
    spec.loader.exec_module(worker)

    records = output / "state/prospects/records"
    records.mkdir(parents=True)
    (records / "synthetic-example.json").write_text(json.dumps({
        "place_id": "synthetic-bicycle-workshop",
        "display_name": "Example Bicycle Workshop (synthetic)",
        "composite_cohort": "A_gold",
        "contact_email": "review@example.invalid",
        "mockup_url": "https://example.invalid/synthetic-preview",
    }, indent=2))
    service = ControlPlaneService()
    failed_attempt = None

    def enqueue(title: str, parent: str | None = None):
        goal = service.create_goal(title=title, summary="Refresh a synthetic local ledger.",
                                   parent_goal_id=parent)
        task = service.create_task_for_goal(
            goal_id=goal.id, repo_id="ai-company-os", lane=WorkerLane.OUTREACH,
            title=title, summary="Materialize one synthetic prospect into local JSON/Markdown.",
            task_type="OUTREACH_LEDGER_REFRESH",
        )
        return goal, task

    if args.exercise_failure:
        goal, task = enqueue("Demonstrate a local write failure")
        obstruction = output / "state/prospects/outreach-lane/client-status.json"
        obstruction.mkdir(parents=True)
        try:
            worker.execute_claimed_task(worker_id="demo-failed-worker", service=service)
        except OSError:
            pass
        failed_task = service.tasks.load(task.id)
        if failed_task.status is not TaskStatus.FAILED:
            raise RuntimeError("failure exercise did not persist the expected failed task")
        failed_attempt = {"task": failed_task.to_dict(), "goal": service.goals.load(goal.id).to_dict()}
        obstruction.rmdir()

    goal, task = enqueue("Refresh the example ledger", failed_attempt["goal"]["id"] if failed_attempt else None)
    result = worker.execute_claimed_task(worker_id="demo-worker", service=service)
    persisted = service.tasks.load(task.id)
    if result is None or persisted.status is not TaskStatus.COMPLETED:
        raise RuntimeError(f"worker did not complete: {persisted.error_summary}")
    validation = service._run_post_run_validation(
        task_id=task.id, summary=result.summary,
        artifacts=result.artifacts, events=["task_claimed"],
    )
    if validation["verdict"] != "ok":
        raise RuntimeError(f"evidence recheck failed: {validation}")
    report = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "input_kind": "synthetic", "execution_kind": "real local outreach ledger worker",
        "worker_source_sha256": hashlib.sha256(worker_path.read_bytes()).hexdigest(),
        "external_model_invoked": False, "network_and_subprocess_calls_blocked": True,
        "task": persisted.to_dict(), "goal": service.goals.load(goal.id).to_dict(),
        "validation": validation, "artifacts": result.artifacts,
        "events": [event.to_dict() for event in service.list_events()],
        "failed_attempt": failed_attempt,
    }
    (output / "execution-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Real worker execution passed. Inspect {output / 'execution-report.json'}")
    print("Input is synthetic. No model, message sending, approval, or release was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
