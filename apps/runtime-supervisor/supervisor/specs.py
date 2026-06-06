"""Runtime supervisor — default worker process specs.

Phase 3 (skill self-evolution) and Phase 1 (autonomous dispatch of
supervisor and gtm workers) add new entries here. Phases that add
worker lanes touch only this file + packages/schemas/task_packet.py;
they should NOT touch `core.py` or `dispatch_router.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.config.settings import ensure_runtime_directories


@dataclass(frozen=True)
class WorkerProcessSpec:
    lane: str
    worker_id: str
    script_path: Path
    log_path: Path


def default_worker_specs() -> list[WorkerProcessSpec]:
    paths = ensure_runtime_directories()
    runtime_logs_root = paths.logs_root / "runtime-supervisor"
    runtime_logs_root.mkdir(parents=True, exist_ok=True)
    return [
        WorkerProcessSpec(
            lane="engineering",
            worker_id="worker-engineering",
            script_path=paths.repo_root / "apps" / "worker-engineering" / "main.py",
            log_path=runtime_logs_root / "worker-engineering.log",
        ),
        WorkerProcessSpec(
            lane="ios",
            worker_id="worker-ios",
            script_path=paths.repo_root / "apps" / "worker-ios" / "main.py",
            log_path=runtime_logs_root / "worker-ios.log",
        ),
        WorkerProcessSpec(
            lane="appstore",
            worker_id="worker-appstore",
            script_path=paths.repo_root / "apps" / "worker-appstore" / "main.py",
            log_path=runtime_logs_root / "worker-appstore.log",
        ),
        WorkerProcessSpec(
            lane="api",
            worker_id="worker-api",
            script_path=paths.repo_root / "apps" / "api" / "server.py",
            log_path=runtime_logs_root / "worker-api.log",
        ),
        # Phase 3 — skill self-evolution worker. New lane; claim loop
        # in apps/worker-skill-evolution/main.py; policy gate in
        # packages/policies/skill_evolution.py. Appended last so the
        # four-worker ordering from the Phase 0.5c split stays stable
        # for the existing test_default_worker_specs_api.py contract
        # (that test is updated in this same PR to assert 5 specs).
        WorkerProcessSpec(
            lane="skill_evolution",
            worker_id="worker-skill-evolution",
            script_path=(
                paths.repo_root / "apps" / "worker-skill-evolution" / "main.py"
            ),
            log_path=runtime_logs_root / "worker-skill-evolution.log",
        ),
        # G1 — agency billing-event poller. Not a task-claiming worker: a periodic
        # loop that drains the Netlify Blobs "stripe-events" store and reconciles to
        # the local ledger. Lives here because launchd runs ONLY the supervisor
        # (infra/launchd/README.md) — no standalone poller plist. Appended last.
        WorkerProcessSpec(
            lane="billing_poller",
            worker_id="worker-billing-poller",
            script_path=paths.repo_root / "apps" / "worker-billing-poller" / "main.py",
            log_path=runtime_logs_root / "worker-billing-poller.log",
        ),
    ]
