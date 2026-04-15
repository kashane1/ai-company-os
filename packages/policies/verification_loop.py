"""Verification-loop policy wrapper (ECC Gap Recommendations Phase 3).

Thin raising wrapper over
`packages.tools.primitives.verification_loop_runner.run()`. Mirrors
`packages.policies.skill_evolution.check_evolution_allowed()` — the
template noted in the plan because `release_readiness.py` still uses
bare-string raises (pre-existing debt outside this plan's scope).

Two call conventions, enforced by the module docstring:

- CI / merge-gating callers want `run_verification_loop()`. It
  raises `PolicyViolation(VERIFICATION_LOOP_HARD_FAIL)` on
  `verdict == "hard_fail"`.
- Agents / advisory callers want the runner primitive directly
  (`packages.tools.primitives.verification_loop_runner.run()`),
  which returns the report without raising. See the "caller-mapping"
  table in the plan for the full list of who calls what.

If you catch `PolicyViolation` from this module, you are in the
wrong module — use the runner primitive instead.
"""
from __future__ import annotations

from packages.policies.approvals import PolicyViolation, PolicyViolationCode
from packages.tools.primitives.verification_loop_runner import (
    VerificationLoopReport,
    report_as_dict,
    run as _run,
)


def run_verification_loop(
    *,
    since_ref: str = "main",
    lookback_task_runs: int = 20,
    known_drift: tuple[str, ...] = ("post-run-validation",),
) -> VerificationLoopReport:
    """Run the verification loop and raise on hard_fail.

    Keyword-only args so every call site reads as
    `run_verification_loop(since_ref="main")` — matches the
    `skill_evolution.check_evolution_allowed()` convention.

    Returns the full report on `pass` or `soft_fail` so callers that
    want to surface soft warnings to the operator can inspect every
    sub-check's severity. `hard_fail` always raises; callers must
    not expect a returned report in that case.
    """
    report = _run(
        since_ref=since_ref,
        lookback_task_runs=lookback_task_runs,
        known_drift=known_drift,
    )
    if report.verdict == "hard_fail":
        failed_sub_checks = [
            sc.name for sc in report.sub_checks if sc.severity == "fail"
        ]
        raise PolicyViolation(
            PolicyViolationCode.VERIFICATION_LOOP_HARD_FAIL,
            detail=(
                "verification-loop hard fail; sub-checks: "
                f"{', '.join(failed_sub_checks)}"
            ),
        )
    return report


def report_json(report: VerificationLoopReport) -> dict:
    """Serialize a report for JSON persistence."""
    return report_as_dict(report)
