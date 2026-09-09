"""Zero-dependency fixture walkthrough of the ai-company-os control loop.

Runs entirely in-process with no Postgres, Redis, Codex, network, or Mac
runtime. It builds real domain schema objects (`GoalRecord`,
`TaskRun`, `ApprovalRecord`, `PostMortem`) so the emitted artifacts are
schema-valid fixtures rather than hand-written JSON. It does not invoke an
agent, make a human approval decision, or perform an irreversible action.

Flow demonstrated:

    goal -> typed task -> worker execution -> validation
         -> human approval gate -> structured audit artifact

`build_demo_run()` is imported by the end-to-end test; running this file
prints a fixture walkthrough and writes sample artifacts under
`docs/examples/`.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Allow `python scripts/demo/run_demo.py` to run standalone (no PYTHONPATH,
# no install) — keeps the zero-dependency promise.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.schemas.goal import GoalRecord, GoalStatus
from packages.schemas.postmortem import (
    PostMortem,
    PostMortemSeverity,
    PostMortemStatus,
    RootCauseCategory,
)
from packages.schemas.task_packet import WorkerLane
from packages.schemas.task_run import (
    CodexExecutionRecord,
    EngineeringResultClassification,
    GitStateSnapshot,
    TaskRun,
    TaskRunStatus,
    ValidationCheck,
    VerificationResult,
)
from packages.schemas.testing import TestingPolicyResult, TestLane, ValidationFailureCode

_T0 = "2026-05-17T18:00:00Z"
_T1 = "2026-05-17T18:02:30Z"


@dataclass(frozen=True)
class DemoRun:
    goal: GoalRecord
    task_run: TaskRun
    approval: ApprovalRecord
    postmortem: PostMortem


def _testing_policy_for_changes(changed_files: list[str]) -> TestingPolicyResult:
    """Derive the fixture's iOS testing evidence without runtime dependencies."""
    source_roots = {
        path.split("/Sources/", maxsplit=1)[0]
        for path in changed_files
        if "/Sources/" in path
    }
    if not source_roots:
        return TestingPolicyResult(
            tests_required=False,
            test_lane=TestLane.NONE,
            relevant_tests_changed=False,
            details="No logic-bearing source change was recorded.",
        )

    has_matching_test = any(
        path.startswith(f"{source_root}/Tests/")
        or path.startswith(f"{source_root}/UITests/")
        for source_root in source_roots
        for path in changed_files
    )
    return TestingPolicyResult(
        tests_required=True,
        test_lane=TestLane.IOS,
        relevant_tests_changed=has_matching_test,
        failure_code=(
            None if has_matching_test else ValidationFailureCode.MISSING_TESTS_FOR_LOGIC_CHANGE
        ),
        details=(
            "Catchbook source and lane-matching unit-test changes are recorded."
            if has_matching_test
            else "Catchbook source change has no lane-matching test change."
        ),
    )


def _ios_task_run(*, approval_id: str, succeeded: bool) -> TaskRun:
    changed_files = (
        [
            "products/catchbook-ios/Sources/LogEntry.swift",
            "products/catchbook-ios/Tests/LogEntryTests.swift",
        ]
        if succeeded
        else []
    )
    testing_policy = _testing_policy_for_changes(changed_files)
    classification = (
        EngineeringResultClassification.SAFE_FOR_REVIEW
        if succeeded
        else EngineeringResultClassification.EXECUTION_FAILED
    )
    return TaskRun(
        id="run_demo_0001",
        task_id="task_demo_0001",
        worker_lane=WorkerLane.IOS,
        repo_id="ai-company-os",
        worktree_id="wt_demo_0001",
        worktree_path="state/worktrees/ai-company-os/task_demo_0001",
        packet_path="state/artifacts/run_demo_0001/packet.json",
        execution_result_path="state/artifacts/run_demo_0001/execution.json",
        execution=CodexExecutionRecord(
            command=["codex", "exec", "--task", "task_demo_0001"],
            command_display="codex exec --task task_demo_0001",
            cwd="state/worktrees/ai-company-os/task_demo_0001",
            stdout_path="state/artifacts/run_demo_0001/stdout.log",
            stderr_path="state/artifacts/run_demo_0001/stderr.log",
            exit_code=0 if succeeded else 1,
            started_at=_T0,
            finished_at=_T1,
            timed_out=False,
            session_id="sess_demo",
        ),
        pre_run_git_state=GitStateSnapshot(
            status_lines=[],
            changed_files=[],
            diff_summary="clean worktree",
        ),
        post_run_git_state=GitStateSnapshot(
            status_lines=([f" M {path}" for path in changed_files] if succeeded else []),
            changed_files=changed_files,
            diff_summary=("2 files changed, 19 insertions(+), 3 deletions(-)" if succeeded else ""),
        ),
        diff_path="state/artifacts/run_demo_0001/diff.patch",
        classification=classification,
        review_artifact_path="state/artifacts/run_demo_0001/review.json",
        approval_id=approval_id if succeeded else None,
        status=TaskRunStatus.SUCCEEDED if succeeded else TaskRunStatus.FAILED,
        summary=(
            "Fixed catch-log timestamp rounding in LogEntry; tests added."
            if succeeded
            else "Codex execution failed before producing a reviewable diff."
        ),
        started_at=_T0,
        finished_at=_T1,
        validation_checks=[
            ValidationCheck(
                name="testing_policy",
                passed=testing_policy.failure_code is None,
                details=testing_policy.details,
                code=(testing_policy.failure_code.value if testing_policy.failure_code else None),
            ),
        ],
        verification_results=[VerificationResult(
            command=["xcodebuild", "test", "-scheme", "Catchbook"],
            cwd="state/worktrees/ai-company-os/task_demo_0001/products/catchbook-ios",
            revision="0000000000000000000000000000000000000000",
            diff_sha256="0" * 64,
            exit_code=0 if succeeded else 1,
            stdout_path="state/artifacts/run_demo_0001/verification.stdout.log",
            stderr_path="state/artifacts/run_demo_0001/verification.stderr.log",
            started_at=_T0, finished_at=_T1,
        )],
        testing_policy=testing_policy,
        failure_codes=[] if succeeded else ["EXECUTION_FAILED"],
        artifacts=["diff.patch", "review.json"],
    )


def build_demo_run(*, succeeded: bool = True) -> DemoRun:
    """Build a schema-valid fixture for an end-to-end control-loop record.

    `succeeded=False` exercises the failure path: no approval is granted
    and a PostMortem audit record is emitted instead.
    """
    goal = GoalRecord(
        id="goal_demo_0001",
        title="Fix catch-log timestamp rounding in Catchbook",
        summary="Times are rounded to the hour; users want minute precision.",
        description="Bug reported by a TestFlight user on the Catchbook iOS app.",
        status=GoalStatus.COMPLETED if succeeded else GoalStatus.FAILED,
        created_at=_T0,
        updated_at=_T1,
        completed_at=_T1 if succeeded else None,
    )

    approval = ApprovalRecord(
        id="appr_demo_0001",
        status=ApprovalStatus.APPROVED if succeeded else ApprovalStatus.PENDING,
        summary="iOS change to Catchbook LogEntry awaiting human review.",
        created_at=_T1,
        task_id="task_demo_0001",
        task_run_id="run_demo_0001",
        approval_type="ios_review",
        review_artifact_path="state/artifacts/run_demo_0001/review.json",
        subject_type="task_run",
        subject_id="run_demo_0001",
        action="merge_pr",
        decided_by="founder" if succeeded else None,
        decided_at=_T1 if succeeded else None,
        decision_notes="Diff and tests reviewed; safe to merge." if succeeded else None,
    )

    task_run = _ios_task_run(approval_id=approval.id, succeeded=succeeded)

    postmortem = PostMortem(
        id="pm_demo_0001",
        created_at=_T1,
        updated_at=_T1,
        failure_code="execution_failed",
        lane="ios",
        task_id="task_demo_0001",
        task_run_id="run_demo_0001",
        excerpt_redacted="codex exec aborted: transient upstream error",
        redaction_hits=0,
        severity=PostMortemSeverity.WARN,
        root_cause_category=RootCauseCategory.EXTERNAL_DEPENDENCY,
        remediation_action="Retry with backoff; surface as VALIDATION_FAILED if persistent.",
        owner="founder",
        status=PostMortemStatus.OPEN,
        notes="Emitted automatically on the failure path of the demo run.",
    )

    return DemoRun(goal=goal, task_run=task_run, approval=approval, postmortem=postmortem)


def _narrate(run: DemoRun) -> None:
    g, tr, ap = run.goal, run.task_run, run.approval
    print("ai-company-os — control-loop fixture walkthrough (zero external dependencies)")
    print("=" * 64)
    print(f"1. GOAL       {g.id}: {g.title}")
    print(f"               status={g.status.value}")
    print(f"2. TASK        fixture route: lane={tr.worker_lane.value}")
    print(f"3. EXECUTE     recorded command (not run): {tr.execution.command_display}")
    print(f"               recorded exit={tr.execution.exit_code} classification={tr.classification.value}")
    checks = ", ".join(f"{c.name}={'pass' if c.passed else 'FAIL'}" for c in tr.validation_checks)
    print(f"4. VALIDATE    fixture checks (not executed): {checks}")
    print(f"5. APPROVAL    fixture gate {ap.id}: status={ap.status.value} action={ap.action}")
    if ap.status is ApprovalStatus.APPROVED:
        print(f"               recorded decider={ap.decided_by}: {ap.decision_notes}")
        print("               no approval is requested or performed by this walkthrough")
    else:
        print("               PAUSED — awaiting human decision (no irreversible action taken)")
    print(f"6. AUDIT       fixture task_run {tr.id}: status={tr.status.value}")
    print("               deterministic sample artifacts written to docs/examples/")
    print("=" * 64)


def _write_samples(repo_root: Path) -> list[Path]:
    out_dir = repo_root / "docs" / "examples"
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = build_demo_run(succeeded=True)
    failed = build_demo_run(succeeded=False)
    written: list[Path] = []
    targets = {
        "sample-task-run.json": ok.task_run.to_dict(),
        "sample-approval.json": ok.approval.to_dict(),
        "sample-postmortem.json": failed.postmortem.to_dict(),
    }
    for name, payload in targets.items():
        path = out_dir / name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        written.append(path)
    return written


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    run = build_demo_run(succeeded=True)
    _narrate(run)
    written = _write_samples(repo_root)
    print("Sample artifacts:")
    for path in written:
        print(f"  - {path.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
