"""Phase 3 — worker-skill-evolution entrypoint.

Thin claim loop that mirrors ``apps/worker-gtm/main.py``. The worker:

- Honors the kill switch (``state/flags/skill_evolution_frozen``) before
  every claim. A running proposal is told to stop cleanly by raising
  :class:`SkillEvolutionFrozenError` mid-execution.
- Reads a proposal sidecar at
  ``state/checkpoints/platform/skill_evolution_proposals/<task_id>.json``
  to resolve ``target_skill_id``, the proposed ``diff_paths``, the
  ``target_runtimes`` the diff would set, and a short rationale.
- Runs :func:`packages.policies.skill_evolution.check_evolution_allowed`
  against a :class:`ProposedDiff` derived from the sidecar. Any policy
  rejection surfaces as ``TaskStatus.FAILED`` with the
  :class:`PolicyViolationCode` in ``failure_codes`` — the proposal is
  never staged, no approval record is written.
- Acquires a per-skill-id lock via
  :class:`packages.db.locks.skill_evolution.SkillEvolutionLockStore`.
- Stages the proposal artifact dir under
  ``state/artifacts/skill-evolution/<proposal_id>/``.
- Calls :func:`packages.tools.primitives.approvals.request_evolution_approval`
  to persist the pending :class:`ApprovalRecord` + HMAC magic-link
  token.
- Polls :func:`packages.tools.primitives.approvals.poll_evolution_approval`
  on a bounded backoff. On ``approved``, writes an ``applied.flag``
  marker to the artifact dir and completes the task (Option B's
  minimum viable "applied" signal — a reviewer cherry-picks the
  staged diff in a separate human-authored PR). On ``rejected``,
  fails the task and quarantines the artifact dir. On poll deadline,
  blocks the task and leaves the artifact staged for out-of-band
  completion.
- Releases the lock in ``finally``.

Deliberately NOT in this worker (deferred to a follow-up PR):

- ``gh pr create`` / git push — Option B means the proposal lives on
  disk as a signed artifact, not a PR.
- LLM call to draft the actual diff — the worker is the carrier
  process; the caller is responsible for producing ``diff_paths`` and
  the ``proposed_diff`` blob in the sidecar. This separation makes
  the worker's tests hermetic.
- Voyager/DSPy regression fixture gate — stubbed as
  ``NotImplementedError`` in the policy module; the signing human is
  expected to confirm regression manually in the first landing.
- Dispatch-health metrics emission — deferred to the Phase 0.5e
  ``dispatch_health.py`` writer landing.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from threading import Event
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from apps.api.control_plane import ControlPlaneService
from packages.config.settings import load_runtime_paths
from packages.db.locks.skill_evolution import (
    HEARTBEAT_INTERVAL_US,
    SkillEvolutionLock,
    SkillEvolutionLockStore,
)
from packages.policies.approvals import PolicyViolation
from packages.policies.skill_evolution import (
    ProposedDiff,
    check_evolution_allowed,
)
from packages.schemas.task import Task
from packages.schemas.task_packet import TaskResult, TaskStatus, WorkerLane
from packages.tools.primitives.approvals import (
    ApprovalRequest,
    poll_evolution_approval,
    request_evolution_approval,
)
from packages.tools.primitives.kill_switches import get_switch


WORKER_ID = "worker-skill-evolution"
KILL_SWITCH_NAME = "skill_evolution_frozen"

# Poll cadence + deadline for the in-worker approval wait. Tests pass
# much smaller values via ``execute_claimed_task``.
#
# Production default is 240 s — shorter than the 300 s P0 token TTL
# (skill_evolution_apply is in P0_ACTIONS, see
# packages/policies/approval_tokens.py) so the worker times out and
# blocks the task cleanly BEFORE the token itself expires. A reviewer
# who wants longer to decide should reject the current token with a
# note and re-enqueue the proposal for the next worker run; the
# previous 15-minute default did not match the 5-minute TTL.
DEFAULT_POLL_INTERVAL_SECONDS = 5.0
DEFAULT_MAX_WAIT_SECONDS = 240.0


class SkillEvolutionFrozenError(RuntimeError):
    """Raised mid-task when the kill switch flips to engaged.

    Matches the ``GtmFrozenError`` pattern from worker-gtm so the
    outer loop has a single exception path for "stop cleanly,
    re-queue as BLOCKED".
    """


@dataclass(frozen=True)
class WorkerLoopStats:
    worker_id: str
    processed_count: int
    idle_cycles: int
    frozen_cycles: int
    stop_reason: str


@dataclass(frozen=True)
class ProposalSidecar:
    """Structured view of the proposal sidecar file.

    Tests write this file under
    ``state/checkpoints/platform/skill_evolution_proposals/<task_id>.json``
    to hand the worker a deterministic proposal payload. Production
    callers (the higher-level supervisor that enqueues skill-evolution
    tasks) write the same shape.
    """

    target_skill_id: str
    rationale: str
    diff_paths: tuple[str, ...]
    target_runtimes: tuple[str, ...]
    added_paths: tuple[str, ...] = field(default_factory=tuple)
    removed_paths: tuple[str, ...] = field(default_factory=tuple)
    diff_blob: str = ""
    input_snapshot_sha256: str = ""


# ---------------------------------------------------------------------- #
# Pre-claim gate                                                          #
# ---------------------------------------------------------------------- #


def _refuse_if_blocked(_service: ControlPlaneService, _worker_id: str) -> str | None:
    """Pre-claim gate. Return a short reason string or ``None``.

    Mirrors ``apps/worker-gtm/main.py:_refuse_if_blocked`` — the outer
    loop counts ``frozen_cycles`` on any non-None return. Kept as a
    single composable function so future gates (e.g. per-skill
    freeze flags) can plug in without changing the loop.
    """
    switch = get_switch(KILL_SWITCH_NAME)
    if switch.engaged:
        return "frozen"
    return None


# ---------------------------------------------------------------------- #
# Sidecar IO                                                              #
# ---------------------------------------------------------------------- #


# Kebab-case identifiers for task_id and target_skill_id. These are
# used verbatim as filesystem path components, so the pattern is
# strict: lowercase letters, digits, hyphens, underscores only. No
# dots (which allow ``..``), no slashes, no spaces, no Unicode. The
# pattern must also reject empty strings and anything longer than
# 128 chars — long enough for any real id, short enough to rule out
# blob-style injection. Security-sentinel H3 + M2 on the first
# Phase 3 PR.
_SAFE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_\-]{0,127}$")


class SidecarValidationError(ValueError):
    """Raised when a proposal sidecar fails input sanitization.

    Distinct from ``ValueError`` so the worker can map it to a
    specific failure code without catching unrelated coercion errors.
    """


def _require_safe_id(value: str, *, kind: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID_PATTERN.match(value):
        raise SidecarValidationError(
            f"{kind} {value!r} is not a safe identifier; expected "
            f"kebab/snake-case matching {_SAFE_ID_PATTERN.pattern}"
        )
    return value


def _require_safe_path(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise SidecarValidationError(
            f"{field} entry must be a string, got {type(value).__name__}"
        )
    if not value:
        raise SidecarValidationError(f"{field} entry is empty")
    if "\x00" in value:
        raise SidecarValidationError(
            f"{field} entry {value!r} contains a null byte"
        )
    pp = PurePosixPath(value)
    if pp.is_absolute():
        raise SidecarValidationError(
            f"{field} entry {value!r} is absolute; only repo-relative "
            f"POSIX paths are allowed"
        )
    if ".." in pp.parts:
        raise SidecarValidationError(
            f"{field} entry {value!r} contains '..'; path traversal "
            f"is forbidden"
        )
    # Reject non-normalized forms — ``./foo``, ``foo//bar``, trailing
    # slash — so the policy layer sees a canonical path. Comparing
    # ``str(PurePosixPath(value))`` catches all of these in one shot.
    normalized = str(pp)
    if normalized != value:
        raise SidecarValidationError(
            f"{field} entry {value!r} is not in normalized POSIX form "
            f"(expected {normalized!r})"
        )
    return value


def _sidecar_path(task_id: str) -> Path:
    _require_safe_id(task_id, kind="task_id")
    paths = load_runtime_paths()
    return (
        paths.platform_state_root
        / "skill_evolution_proposals"
        / f"{task_id}.json"
    )


def load_sidecar(task_id: str) -> ProposalSidecar:
    """Read the proposal sidecar for ``task_id``.

    Raises :class:`FileNotFoundError` with a targeted message if the
    sidecar is missing — the worker converts that to a
    ``TaskStatus.FAILED`` with a ``missing_proposal_sidecar`` failure
    code.

    Raises :class:`SidecarValidationError` if any path in the sidecar
    is absolute, contains ``..``, contains a null byte, or isn't in
    normalized POSIX form. The sidecar file itself lives under
    ``state/checkpoints/platform/`` which is attacker-writable by a
    compromised sibling worker, so every field it produces must be
    treated as untrusted input. Security-sentinel H3 + M2 on the
    first Phase 3 PR.
    """
    # _sidecar_path already validates task_id.
    path = _sidecar_path(task_id)
    if not path.exists():
        raise FileNotFoundError(
            f"no proposal sidecar for task {task_id!r} at {path}"
        )
    payload = json.loads(path.read_text())

    target_skill_id = _require_safe_id(
        str(payload["target_skill_id"]), kind="target_skill_id"
    )
    # Reject any runtime that isn't a known-good slug. The policy
    # layer also enforces [claude] only, but we defend in depth.
    raw_runtimes = payload.get("target_runtimes", [])
    if not isinstance(raw_runtimes, list):
        raise SidecarValidationError(
            f"target_runtimes must be a list, got "
            f"{type(raw_runtimes).__name__}"
        )
    target_runtimes = tuple(
        _require_safe_id(str(r), kind="target_runtime") for r in raw_runtimes
    )

    def _safe_path_tuple(key: str) -> tuple[str, ...]:
        raw = payload.get(key, [])
        if not isinstance(raw, list):
            raise SidecarValidationError(
                f"{key} must be a list, got {type(raw).__name__}"
            )
        return tuple(_require_safe_path(p, field=key) for p in raw)

    return ProposalSidecar(
        target_skill_id=target_skill_id,
        rationale=str(payload.get("rationale", "")),
        diff_paths=_safe_path_tuple("diff_paths"),
        target_runtimes=target_runtimes,
        added_paths=_safe_path_tuple("added_paths"),
        removed_paths=_safe_path_tuple("removed_paths"),
        diff_blob=str(payload.get("diff_blob", "")),
        input_snapshot_sha256=str(payload.get("input_snapshot_sha256", "")),
    )


# ---------------------------------------------------------------------- #
# Artifact staging                                                        #
# ---------------------------------------------------------------------- #


def _artifact_dir_for(proposal_id: str) -> Path:
    paths = load_runtime_paths()
    return paths.artifacts_root / "skill-evolution" / proposal_id


def stage_proposal(
    *,
    task_id: str,
    sidecar: ProposalSidecar,
) -> Path:
    """Write the proposal artifacts under
    ``state/artifacts/skill-evolution/<proposal_id>/``.

    Contents after this function returns:

    - ``diff.patch`` — the raw diff blob from the sidecar (may be empty
      on tests that only exercise policy checks).
    - ``rationale.md`` — the rationale text.
    - ``input_snapshot.sha256`` — the hash the caller pinned.
    - ``manifest.json`` — machine-readable index of the other files.

    ``proposal_id`` is derived from ``task_id`` + short hash so
    concurrent proposals on the same skill (impossible at runtime due
    to the lock, but tests may want to race) don't collide.
    """
    proposal_id = f"{task_id}-{_short_hash(task_id, sidecar.target_skill_id)}"
    root = _artifact_dir_for(proposal_id)
    root.mkdir(parents=True, exist_ok=True)

    (root / "diff.patch").write_text(sidecar.diff_blob)
    rationale = f"# Proposal rationale\n\n{sidecar.rationale}\n"
    (root / "rationale.md").write_text(rationale)
    (root / "input_snapshot.sha256").write_text(
        f"{sidecar.input_snapshot_sha256}\n"
    )
    manifest = {
        "proposal_id": proposal_id,
        "task_id": task_id,
        "target_skill_id": sidecar.target_skill_id,
        "diff_paths": list(sidecar.diff_paths),
        "target_runtimes": list(sidecar.target_runtimes),
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )
    return root


def _short_hash(*parts: str) -> str:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return h[:12]


def _quarantine_artifact(artifact_dir: Path) -> Path:
    """Move a rejected/expired proposal out of the active artifacts dir.

    Uses :func:`Path.rename` (same-filesystem POSIX rename, atomic) so
    a failure during the move cannot leave the proposal in two places.
    Returns the quarantine path.
    """
    paths = load_runtime_paths()
    quarantine_root = paths.state_root / "quarantine" / "skill-evolution"
    quarantine_root.mkdir(parents=True, exist_ok=True)
    target = quarantine_root / artifact_dir.name
    if target.exists():
        # Test isolation: tolerate a stale quarantine entry from a
        # previous run by appending a short hash. Production should
        # never hit this branch because proposal_ids are task-unique.
        target = quarantine_root / f"{artifact_dir.name}-{_short_hash(str(time.time()))}"
    artifact_dir.rename(target)
    return target


# ---------------------------------------------------------------------- #
# Main work function                                                      #
# ---------------------------------------------------------------------- #


def execute_claimed_task(
    *,
    worker_id: str = WORKER_ID,
    service: ControlPlaneService | None = None,
    lock_store: SkillEvolutionLockStore | None = None,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    max_wait_seconds: float = DEFAULT_MAX_WAIT_SECONDS,
    sleep_fn=time.sleep,
    now_fn=time.monotonic,
) -> TaskResult | None:
    """Claim one task from the ``SKILL_EVOLUTION`` lane and run it to
    a terminal state or BLOCKED.

    Returns ``None`` when the kill switch is engaged or the queue is
    empty (same contract as ``worker-gtm``).
    """
    control_plane = service or ControlPlaneService()
    blocked = _refuse_if_blocked(control_plane, worker_id)
    if blocked is not None:
        return None

    task = control_plane.claim_task(
        lane=WorkerLane.SKILL_EVOLUTION, worker_id=worker_id
    )
    if task is None:
        return None

    store = lock_store or SkillEvolutionLockStore()
    return _run_one(
        task=task,
        worker_id=worker_id,
        control_plane=control_plane,
        lock_store=store,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        sleep_fn=sleep_fn,
        now_fn=now_fn,
    )


def _run_one(
    *,
    task: Task,
    worker_id: str,
    control_plane: ControlPlaneService,
    lock_store: SkillEvolutionLockStore,
    poll_interval_seconds: float,
    max_wait_seconds: float,
    sleep_fn,
    now_fn,
) -> TaskResult:
    """Inner execution for a single claimed task.

    Split from :func:`execute_claimed_task` so tests can inject a
    fake :class:`Task` and skip the queue claim. Returns the result
    the worker also submitted to the control plane so callers can
    assert on the terminal state.
    """
    # 1. Load sidecar. A missing file is a genuine missing-input case;
    #    a validation failure on attacker-writable path fields is a
    #    different failure class that should surface loudly so the
    #    operator can tell the two apart during incident review.
    try:
        sidecar = load_sidecar(task.id)
    except FileNotFoundError as exc:
        return _fail(
            task,
            worker_id,
            control_plane,
            summary=f"missing_proposal_sidecar: {exc}",
            failure_codes=["missing_proposal_sidecar"],
        )
    except SidecarValidationError as exc:
        return _fail(
            task,
            worker_id,
            control_plane,
            summary=f"sidecar_validation_failed: {exc}",
            failure_codes=["sidecar_validation_failed"],
        )

    # 2. Build a typed ProposedDiff and run the policy.
    diff = ProposedDiff(
        target_skill_id=sidecar.target_skill_id,
        paths=frozenset(sidecar.diff_paths),
        target_runtimes=sidecar.target_runtimes,
        added_paths=frozenset(sidecar.added_paths),
        removed_paths=frozenset(sidecar.removed_paths),
    )
    try:
        check_evolution_allowed(diff, lock_store=lock_store)
    except PolicyViolation as exc:
        return _fail(
            task,
            worker_id,
            control_plane,
            summary=f"policy_denied: {exc.code}: {exc}",
            failure_codes=[exc.code],
        )

    # 3. Acquire the per-skill-id lock. A None return means the
    #    lock is held by another live worker — the policy check
    #    above would typically catch this, but the two are not the
    #    same (the policy check is racy; the lock is authoritative).
    lock = lock_store.acquire(
        skill_id=sidecar.target_skill_id, worker_id=worker_id
    )
    if lock is None:
        return _fail(
            task,
            worker_id,
            control_plane,
            summary=(
                "concurrent_evolution_in_progress: lock held by another "
                "worker — re-queue after review"
            ),
            failure_codes=["concurrent_evolution_in_progress"],
        )

    staged_dir: Path | None = None
    approval: ApprovalRequest | None = None
    try:
        # 4. Stage the proposal to disk.
        staged_dir = stage_proposal(task_id=task.id, sidecar=sidecar)

        # 5. Request human approval via the HMAC primitive.
        approval = request_evolution_approval(
            proposal_id=staged_dir.name,
            target_skill_id=sidecar.target_skill_id,
            rationale=sidecar.rationale,
            artifact_dir=staged_dir,
            task_id=task.id,
        )

        # 6. Poll the approval with bounded backoff. Kill switch
        #    and lock heartbeat are checked on every cycle.
        decision = _poll_with_heartbeat(
            approval_id=approval.approval_id,
            lock=lock,
            lock_store=lock_store,
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            sleep_fn=sleep_fn,
            now_fn=now_fn,
        )

        if decision == "approved":
            # Option B "applied" marker — the signed proposal is
            # ready for a reviewer to cherry-pick. A follow-up PR
            # will add an automated apply step if the terminal
            # review UX feels too thin.
            (staged_dir / "applied.flag").write_text(
                json.dumps(
                    {
                        "approval_id": approval.approval_id,
                        "approved_at": _now_iso(),
                    },
                    indent=2,
                )
            )
            return _complete(
                task,
                worker_id,
                control_plane,
                summary=(
                    f"skill_evolution_approved: {sidecar.target_skill_id} "
                    f"approval_id={approval.approval_id}"
                ),
                approval_id=approval.approval_id,
                artifacts=[str(staged_dir)],
            )
        if decision == "rejected":
            quarantined = _quarantine_artifact(staged_dir)
            staged_dir = None  # already moved — don't re-touch below
            return _fail(
                task,
                worker_id,
                control_plane,
                summary=(
                    f"skill_evolution_rejected: {sidecar.target_skill_id} "
                    f"quarantined={quarantined}"
                ),
                failure_codes=["skill_evolution_rejected"],
                approval_id=approval.approval_id,
            )
        # decision == "timeout"
        return _block(
            task,
            worker_id,
            control_plane,
            summary=(
                f"skill_evolution_awaiting_approval: staged_dir={staged_dir} "
                f"approval_id={approval.approval_id}"
            ),
            approval_id=approval.approval_id,
            artifacts=[str(staged_dir)],
        )
    except SkillEvolutionFrozenError:
        # Kill switch flipped mid-poll. Block cleanly, leave the
        # proposal staged — a reviewer can still sign it after the
        # switch is cleared.
        return _block(
            task,
            worker_id,
            control_plane,
            summary=(
                "paused:frozen — skill_evolution kill switch engaged "
                "mid-task"
            ),
            approval_id=approval.approval_id if approval else None,
            artifacts=[str(staged_dir)] if staged_dir else [],
        )
    finally:
        # Release the lock regardless of outcome. The store's release
        # is idempotent — a False return means someone else stole the
        # lock, which is already surfaced by the heartbeat check.
        lock_store.release(skill_id=lock.skill_id, token=lock.token)


def _poll_with_heartbeat(
    *,
    approval_id: str,
    lock: SkillEvolutionLock,
    lock_store: SkillEvolutionLockStore,
    poll_interval_seconds: float,
    max_wait_seconds: float,
    sleep_fn,
    now_fn,
) -> str:
    """Block until the approval flips or the deadline fires.

    Returns one of ``"approved"``, ``"rejected"``, ``"timeout"``.
    Raises :class:`SkillEvolutionFrozenError` if the kill switch
    engages mid-poll.
    """
    start = now_fn()
    # Heartbeat cadence converted from microseconds to seconds — the
    # lock store's cadence is the authoritative one.
    heartbeat_period = HEARTBEAT_INTERVAL_US / 1_000_000 / 2
    last_heartbeat = start

    while True:
        # Kill switch check first — the freeze signal is the
        # strongest stop condition and should preempt a pending
        # approval that just landed.
        if get_switch(KILL_SWITCH_NAME).engaged:
            raise SkillEvolutionFrozenError(
                "kill switch engaged mid-poll"
            )

        decision = poll_evolution_approval(approval_id=approval_id)
        if decision.outcome == "approved":
            return "approved"
        if decision.outcome == "rejected":
            return "rejected"

        now = now_fn()
        if now - start >= max_wait_seconds:
            return "timeout"

        if now - last_heartbeat >= heartbeat_period:
            if not lock_store.heartbeat(
                skill_id=lock.skill_id, token=lock.token
            ):
                # Lock was stolen. Treat as a hard failure — a
                # competing worker is now racing on the same skill.
                raise RuntimeError(
                    f"skill-evolution lock on {lock.skill_id!r} was "
                    f"stolen mid-poll; abandoning"
                )
            last_heartbeat = now

        sleep_fn(poll_interval_seconds)


# ---------------------------------------------------------------------- #
# Terminal transitions                                                    #
# ---------------------------------------------------------------------- #


def _complete(
    task: Task,
    worker_id: str,
    control_plane: ControlPlaneService,
    *,
    summary: str,
    approval_id: str | None = None,
    artifacts: list[str] | None = None,
) -> TaskResult:
    control_plane.submit_task_result(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary=summary,
        worker_id=worker_id,
        approval_id=approval_id,
    )
    return TaskResult(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary=summary,
        approval_id=approval_id,
        artifacts=artifacts or [],
    )


def _fail(
    task: Task,
    worker_id: str,
    control_plane: ControlPlaneService,
    *,
    summary: str,
    failure_codes: list[str],
    approval_id: str | None = None,
) -> TaskResult:
    control_plane.submit_task_result(
        task_id=task.id,
        status=TaskStatus.FAILED,
        summary=summary,
        worker_id=worker_id,
        approval_id=approval_id,
    )
    return TaskResult(
        task_id=task.id,
        status=TaskStatus.FAILED,
        summary=summary,
        approval_id=approval_id,
        failure_codes=failure_codes,
    )


def _block(
    task: Task,
    worker_id: str,
    control_plane: ControlPlaneService,
    *,
    summary: str,
    approval_id: str | None = None,
    artifacts: list[str] | None = None,
) -> TaskResult:
    control_plane.submit_task_result(
        task_id=task.id,
        status=TaskStatus.BLOCKED,
        summary=summary,
        worker_id=worker_id,
        approval_id=approval_id,
    )
    return TaskResult(
        task_id=task.id,
        status=TaskStatus.BLOCKED,
        summary=summary,
        approval_id=approval_id,
        artifacts=artifacts or [],
    )


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------- #
# Outer loop                                                              #
# ---------------------------------------------------------------------- #


def run_worker_loop(
    *,
    worker_id: str = WORKER_ID,
    service: ControlPlaneService | None = None,
    poll_interval_seconds: float = 2.0,
    stop_event: Event | None = None,
    sleep_fn=time.sleep,
    max_iterations: int | None = None,
) -> WorkerLoopStats:
    control_plane = service or ControlPlaneService()
    stop_signal = stop_event or Event()
    processed = 0
    idle = 0
    frozen = 0
    iters = 0
    stop_reason = "stopped"

    while not stop_signal.is_set():
        try:
            blocked = _refuse_if_blocked(control_plane, worker_id)
            if blocked is not None:
                frozen += 1
                sleep_fn(poll_interval_seconds)
                iters += 1
                if max_iterations is not None and iters >= max_iterations:
                    stop_reason = "frozen"
                    break
                continue

            result = execute_claimed_task(
                worker_id=worker_id, service=control_plane
            )
        except KeyboardInterrupt:
            stop_reason = "interrupted"
            break
        except Exception:
            processed += 1
            stop_reason = "failed"
            iters += 1
            if max_iterations is not None and iters >= max_iterations:
                break
            continue

        iters += 1
        if result is None:
            idle += 1
            sleep_fn(poll_interval_seconds)
            stop_reason = "idle"
            if max_iterations is not None and iters >= max_iterations:
                break
            continue
        processed += 1
        stop_reason = "processed"
        if max_iterations is not None and iters >= max_iterations:
            break

    return WorkerLoopStats(
        worker_id=worker_id,
        processed_count=processed,
        idle_cycles=idle,
        frozen_cycles=frozen,
        stop_reason=stop_reason,
    )


if __name__ == "__main__":
    try:
        stats = run_worker_loop()
    except KeyboardInterrupt:
        stats = WorkerLoopStats(
            worker_id=WORKER_ID,
            processed_count=0,
            idle_cycles=0,
            frozen_cycles=0,
            stop_reason="interrupted",
        )
    print(json.dumps({"stats": asdict(stats)}, default=str))
