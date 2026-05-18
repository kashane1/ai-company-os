"""Typed tool/task surface: malformed or unknown contracts are rejected
at the schema boundary, not deep inside a run.

This is the executable form of the claim in docs/FOR-EMPLOYERS.md: tools
and task contracts are enum-constrained typed schemas, so an unknown
action or a malformed argument cannot construct a valid record.
"""

from __future__ import annotations

import pytest

from packages.schemas.approval import ApprovalRecord
from packages.schemas.task_packet import WorkerLane
from packages.schemas.task_run import TaskRun


def _valid_task_run_payload() -> dict:
    return {
        "id": "run_1",
        "task_id": "task_1",
        "worker_lane": "engineering",
        "repo_id": "repo_1",
        "worktree_id": "wt_1",
        "worktree_path": "state/worktrees/wt_1",
        "packet_path": "p.json",
        "execution_result_path": "e.json",
        "execution": {
            "command": ["codex"],
            "command_display": "codex",
            "cwd": ".",
            "stdout_path": "o.log",
            "stderr_path": "e.log",
            "exit_code": 0,
            "started_at": "2026-05-17T00:00:00Z",
            "finished_at": "2026-05-17T00:01:00Z",
        },
        "pre_run_git_state": {"status_lines": [], "changed_files": [], "diff_summary": ""},
        "post_run_git_state": {"status_lines": [], "changed_files": [], "diff_summary": ""},
        "diff_path": "d.patch",
        "classification": "safe_for_review",
        "review_artifact_path": "r.json",
        "approval_id": None,
        "status": "succeeded",
        "summary": "ok",
        "started_at": "2026-05-17T00:00:00Z",
        "finished_at": "2026-05-17T00:01:00Z",
    }


def test_unknown_worker_lane_rejected_at_boundary():
    """An unknown tool/lane cannot be named — the enum rejects it."""
    WorkerLane("engineering")  # known value constructs fine
    with pytest.raises(ValueError):
        WorkerLane("definitely_not_a_real_lane")


def test_valid_task_run_round_trips_faithfully():
    original = TaskRun.from_dict(_valid_task_run_payload())
    assert TaskRun.from_dict(original.to_dict()).to_dict() == original.to_dict()


def test_malformed_classification_rejected_at_boundary():
    payload = _valid_task_run_payload()
    payload["classification"] = "totally_invalid_classification"
    with pytest.raises(ValueError):
        TaskRun.from_dict(payload)


def test_incomplete_task_contract_rejected_at_boundary():
    payload = _valid_task_run_payload()
    del payload["worker_lane"]
    with pytest.raises(KeyError):
        TaskRun.from_dict(payload)


def test_malformed_approval_status_rejected_at_boundary():
    with pytest.raises(ValueError):
        ApprovalRecord.from_dict(
            {
                "id": "a1",
                "status": "not_a_status",
                "summary": "s",
                "created_at": "2026-05-17T00:00:00Z",
            }
        )
