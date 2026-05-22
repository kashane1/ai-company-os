"""Phase 3 integration test — verification-loop composition on the
live repo.

Runs the full verification-loop runner against the current repo
state and asserts the composition is correct:

- The report has exactly 4 structural sub-checks.
- Each sub-check has a severity in the 5-state enum.
- The aggregator's verdict is one of pass / soft_fail / hard_fail.
- `reconciliation` and `skill_stocktake` are both reachable and
  return without crashing (no `error` severity on them).

This test does NOT assert a specific verdict — the real repo's
verdict depends on its current state. It DOES assert the
composition wiring is intact.
"""
from __future__ import annotations

from packages.tools.primitives.verification_loop_runner import run


def test_live_verification_loop_composition() -> None:
    report = run(since_ref="main")

    assert report.schema_version == "1"
    assert len(report.sub_checks) == 4
    names = {sc.name for sc in report.sub_checks}
    assert names == {
        "reconciliation",
        "skill_stocktake",
        "changed_surface",
        "stale_doc",
    }

    allowed_severities = {"info", "warn", "fail", "error", "skipped"}
    for sc in report.sub_checks:
        assert sc.severity in allowed_severities, (
            f"{sc.name}: severity {sc.severity!r} not in enum"
        )

    allowed_verdicts = {"pass", "soft_fail", "hard_fail"}
    assert report.verdict in allowed_verdicts

    # Reconciliation and stocktake should never crash — those are
    # pure Python with deterministic inputs. changed_surface can
    # legitimately fail on a branch with missing tests.
    core_errors = [
        sc
        for sc in report.sub_checks
        if sc.name in {"reconciliation", "skill_stocktake"}
        and sc.severity == "error"
    ]
    assert not core_errors, (
        f"core sub-checks crashed: {[sc.summary for sc in core_errors]}"
    )
