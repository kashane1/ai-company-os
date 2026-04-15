"""Phase 3 — end-to-end integration test for worker-skill-evolution.

Drives one real claim through :func:`execute_claimed_task` against:

- An isolated control-plane DB under ``tmp_path``.
- An isolated state root (``AI_COMPANY_OS_REPO_ROOT`` redirected).
- A deterministic HMAC signing secret.
- The real :class:`ApprovalStore` and :class:`ApprovalTokenStore`.
- A registry override that declares a ``demo-evolvable-skill`` entry
  with ``self_evolvable: true`` so the allowlist check passes.

The worker is imported via ``importlib.util.spec_from_file_location``
because its directory (``apps/worker-skill-evolution/``) is not a
normal Python package on sys.path, matching the pattern used by the
other worker-app tests in this repo.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from packages.config.settings import (
    TEST_REPO_ROOT_ENV_VAR,
    ensure_runtime_directories,
)
from packages.db.approval_store import ApprovalStore
from packages.db.locks.skill_evolution import SkillEvolutionLockStore
from packages.db.control_plane_db import ControlPlaneDatabase
from packages.policies.skill_evolution import ProposedDiff
from packages.schemas.approval import ApprovalStatus
from packages.schemas.task_packet import TaskStatus, WorkerLane
from packages.tools.skills.loader import SkillSpec


REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------- #
# Module loader — worker lives outside sys.path                           #
# ---------------------------------------------------------------------- #


def _load_worker_module():
    module_path = REPO_ROOT / "apps" / "worker-skill-evolution" / "main.py"
    spec = importlib.util.spec_from_file_location(
        "skill_evolution_worker_main", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def worker():
    return _load_worker_module()


# ---------------------------------------------------------------------- #
# Test environment — isolated repo root, fake registry                    #
# ---------------------------------------------------------------------- #


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.setenv(
        "AI_COMPANY_OS_APPROVAL_SIGNING_KEY", "11" * 32
    )
    ensure_runtime_directories()
    (tmp_path / "state" / "flags").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def stub_registry(monkeypatch):
    """Replace ``packages.tools.skills.loader.load_registry`` with a
    stub that returns one allowlisted skill so the worker's policy
    check passes without touching the real ``skills/registry.yaml``.
    """
    stub_specs = [
        SkillSpec(
            id="demo-evolvable-skill",
            name="Demo Evolvable Skill",
            kind="agentic",
            path="canonical/demo-evolvable-skill/skill.md",
            owner_agent="test",
            target_runtimes=("claude",),
            stage="active",
            fixture_status="passing",
            source="internal",
            self_evolvable=True,
        ),
    ]
    # Patch the symbol used by packages.policies.skill_evolution.
    import packages.policies.skill_evolution as pol

    monkeypatch.setattr(pol, "load_registry", lambda: list(stub_specs))
    return stub_specs


@pytest.fixture
def control_plane(isolated_env):
    from apps.api.control_plane import ControlPlaneService

    return ControlPlaneService()


def _enqueue_evolution_task(
    control_plane,
    *,
    task_id: str = "task-evo-1",
    goal_id: str = "goal-phase3-test",
) -> None:
    goal = control_plane.create_goal(
        title="phase 3 test",
        summary="exercise worker-skill-evolution end-to-end",
        goal_id=goal_id,
    )
    control_plane.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.SKILL_EVOLUTION,
        title="evolve demo-evolvable-skill",
        summary="patch the validator to handle edge case",
        task_type="SKILL_EVOLUTION_PROPOSAL",
        task_id=task_id,
    )


def _write_sidecar(worker_module, task_id: str, *, target: str = "demo-evolvable-skill") -> None:
    sidecar = worker_module.ProposalSidecar(
        target_skill_id=target,
        rationale="fixing a fixture edge case",
        diff_paths=(
            f"skills/canonical/{target}/skill.md",
            f"skills/canonical/{target}/validator.py",
            f"skills/canonical/{target}/fixtures/new_case.yaml",
        ),
        target_runtimes=("claude",),
        diff_blob="--- a/x\n+++ b/x\n+new line\n",
        input_snapshot_sha256="deadbeef",
    )
    worker_module.write_sidecar(task_id, sidecar)


# ---------------------------------------------------------------------- #
# Happy path — approve within deadline                                    #
# ---------------------------------------------------------------------- #


def test_end_to_end_approved(
    worker, control_plane, stub_registry, isolated_env, monkeypatch
) -> None:
    """The worker stages artifacts, requests approval, polls. We flip
    the approval to ``approved`` on the second poll. The worker must
    complete the task and write the ``applied.flag`` marker."""
    _enqueue_evolution_task(control_plane, task_id="task-ok-1")
    _write_sidecar(worker, "task-ok-1")

    # Share an isolated lock store so tests don't race against a
    # long-lived singleton across the process.
    lock_store = SkillEvolutionLockStore(ControlPlaneDatabase())

    # Fake clock — every call advances 1 s. The worker's inner poll
    # uses monotonic via now_fn and sleeps via sleep_fn.
    ticks = {"value": 0.0}

    def fake_now() -> float:
        return ticks["value"]

    approvals = ApprovalStore()

    def fake_sleep(seconds: float) -> None:
        ticks["value"] += seconds
        # On the second poll iteration, flip the underlying approval
        # record to approved. This simulates a reviewer signing the
        # HMAC token out-of-band.
        pending = approvals.db.fetch_all(
            f"SELECT id FROM approvals WHERE status = {approvals.db.placeholder('s')} "
            f"AND approval_type = {approvals.db.placeholder('t')}",
            {"s": "pending", "t": "skill_evolution"},
        )
        for row in pending:
            approvals.update_status(
                row["id"],
                ApprovalStatus.APPROVED,
                decided_by="test-reviewer",
                decided_at="2026-04-14T00:00:00+00:00",
                decision_notes="simulated sign",
            )

    result = worker.execute_claimed_task(
        worker_id="worker-skill-evolution",
        service=control_plane,
        lock_store=lock_store,
        poll_interval_seconds=0.01,
        max_wait_seconds=10.0,
        sleep_fn=fake_sleep,
        now_fn=fake_now,
    )

    assert result is not None
    assert result.status is TaskStatus.COMPLETED
    assert result.approval_id is not None

    # applied.flag written to the staged dir.
    artifact_dirs = list((isolated_env / "state" / "artifacts" / "skill-evolution").iterdir())
    assert len(artifact_dirs) == 1
    assert (artifact_dirs[0] / "applied.flag").exists()
    assert (artifact_dirs[0] / "diff.patch").exists()
    assert (artifact_dirs[0] / "rationale.md").exists()

    # Lock released.
    assert not lock_store.is_locked(skill_id="demo-evolvable-skill")


# ---------------------------------------------------------------------- #
# Rejected path                                                           #
# ---------------------------------------------------------------------- #


def test_end_to_end_rejected_quarantines_artifacts(
    worker, control_plane, stub_registry, isolated_env
) -> None:
    _enqueue_evolution_task(control_plane, task_id="task-rej-1")
    _write_sidecar(worker, "task-rej-1")

    approvals = ApprovalStore()
    lock_store = SkillEvolutionLockStore(ControlPlaneDatabase())

    ticks = {"value": 0.0}

    def fake_now() -> float:
        return ticks["value"]

    def fake_sleep(seconds: float) -> None:
        ticks["value"] += seconds
        pending = approvals.db.fetch_all(
            f"SELECT id FROM approvals WHERE status = {approvals.db.placeholder('s')} "
            f"AND approval_type = {approvals.db.placeholder('t')}",
            {"s": "pending", "t": "skill_evolution"},
        )
        for row in pending:
            approvals.update_status(
                row["id"],
                ApprovalStatus.REJECTED,
                decided_by="test-reviewer",
                decided_at="2026-04-14T00:00:00+00:00",
                decision_notes="not compelling",
            )

    result = worker.execute_claimed_task(
        worker_id="worker-skill-evolution",
        service=control_plane,
        lock_store=lock_store,
        poll_interval_seconds=0.01,
        max_wait_seconds=10.0,
        sleep_fn=fake_sleep,
        now_fn=fake_now,
    )

    assert result is not None
    assert result.status is TaskStatus.FAILED
    assert "skill_evolution_rejected" in result.failure_codes

    # Artifact dir moved to quarantine; active dir empty.
    active = isolated_env / "state" / "artifacts" / "skill-evolution"
    assert not any(active.iterdir())
    quarantine = (
        isolated_env / "state" / "quarantine" / "skill-evolution"
    )
    assert quarantine.exists()
    assert any(quarantine.iterdir())


# ---------------------------------------------------------------------- #
# Timeout path — no decision before deadline                              #
# ---------------------------------------------------------------------- #


def test_end_to_end_timeout_blocks_task(
    worker, control_plane, stub_registry, isolated_env
) -> None:
    _enqueue_evolution_task(control_plane, task_id="task-wait-1")
    _write_sidecar(worker, "task-wait-1")

    lock_store = SkillEvolutionLockStore(ControlPlaneDatabase())

    ticks = {"value": 0.0}

    def fake_now() -> float:
        return ticks["value"]

    def fake_sleep(seconds: float) -> None:
        ticks["value"] += seconds

    result = worker.execute_claimed_task(
        worker_id="worker-skill-evolution",
        service=control_plane,
        lock_store=lock_store,
        poll_interval_seconds=0.1,
        max_wait_seconds=0.3,
        sleep_fn=fake_sleep,
        now_fn=fake_now,
    )

    assert result is not None
    assert result.status is TaskStatus.BLOCKED
    assert result.approval_id is not None

    # Staged artifact left in place (not quarantined).
    active = isolated_env / "state" / "artifacts" / "skill-evolution"
    dirs = list(active.iterdir())
    assert len(dirs) == 1
    assert not (dirs[0] / "applied.flag").exists()

    # Lock released so a retry is unblocked.
    assert not lock_store.is_locked(skill_id="demo-evolvable-skill")


# ---------------------------------------------------------------------- #
# Policy rejection — missing sidecar                                      #
# ---------------------------------------------------------------------- #


def test_missing_sidecar_fails_fast(
    worker, control_plane, stub_registry, isolated_env
) -> None:
    _enqueue_evolution_task(control_plane, task_id="task-nosidecar-1")
    # Intentionally no sidecar.

    lock_store = SkillEvolutionLockStore(ControlPlaneDatabase())
    result = worker.execute_claimed_task(
        worker_id="worker-skill-evolution",
        service=control_plane,
        lock_store=lock_store,
        poll_interval_seconds=0.01,
        max_wait_seconds=1.0,
    )
    assert result is not None
    assert result.status is TaskStatus.FAILED
    assert "missing_proposal_sidecar" in result.failure_codes

    # Nothing staged, no approval record.
    active = isolated_env / "state" / "artifacts" / "skill-evolution"
    if active.exists():
        assert not any(active.iterdir())


# ---------------------------------------------------------------------- #
# Policy rejection — allowlist                                            #
# ---------------------------------------------------------------------- #


def test_policy_denied_on_non_self_evolvable_target(
    worker, control_plane, isolated_env, monkeypatch
) -> None:
    """Stub the registry with a target that has ``self_evolvable: false``
    and confirm the worker surfaces ``SKILL_NOT_SELF_EVOLVABLE`` without
    staging any artifacts or issuing an approval request."""
    import packages.policies.skill_evolution as pol

    locked = SkillSpec(
        id="locked-skill",
        name="Locked Skill",
        kind="agentic",
        path="canonical/locked-skill/skill.md",
        owner_agent="test",
        target_runtimes=("claude",),
        stage="active",
        fixture_status="passing",
        source="internal",
        self_evolvable=False,
    )
    monkeypatch.setattr(pol, "load_registry", lambda: [locked])

    _enqueue_evolution_task(control_plane, task_id="task-denied-1")
    _write_sidecar(worker, "task-denied-1", target="locked-skill")

    lock_store = SkillEvolutionLockStore(ControlPlaneDatabase())
    result = worker.execute_claimed_task(
        worker_id="worker-skill-evolution",
        service=control_plane,
        lock_store=lock_store,
        poll_interval_seconds=0.01,
        max_wait_seconds=1.0,
    )
    assert result is not None
    assert result.status is TaskStatus.FAILED
    assert "skill_not_self_evolvable" in result.failure_codes

    # No approval record ever created.
    approvals = ApprovalStore()
    with pytest.raises(FileNotFoundError):
        approvals.load("skill-evo-task-denied-1")


# ---------------------------------------------------------------------- #
# Kill switch                                                             #
# ---------------------------------------------------------------------- #


def test_refuses_to_claim_when_kill_switch_engaged(
    worker, control_plane, stub_registry, isolated_env
) -> None:
    _enqueue_evolution_task(control_plane, task_id="task-frozen-1")
    _write_sidecar(worker, "task-frozen-1")

    # Engage the kill switch before the claim.
    (isolated_env / "state" / "flags" / "skill_evolution_frozen").write_text("x")

    result = worker.execute_claimed_task(
        worker_id="worker-skill-evolution",
        service=control_plane,
    )
    # Pre-claim gate returns None — task remains in the queue.
    assert result is None

    # No artifact dir, no approval record.
    active = isolated_env / "state" / "artifacts" / "skill-evolution"
    if active.exists():
        assert not any(active.iterdir())
