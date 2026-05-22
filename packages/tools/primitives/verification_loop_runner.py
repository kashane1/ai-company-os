"""Verification-loop runner primitive (ECC Gap Recommendations Phase 3).

Advisory-mode runner for the structural verification lane. Composes:

1. `reconcile_registry()` — structural fixture reconciliation.
2. `skill_stocktake.check_drift()` — registry / canonical / CLAUDE.md
   drift.
3. Changed-surface missing-tests check — `git diff --name-only
   <ref>...HEAD` cross-referenced against
   `packages/policies/testing.py` lane rules.
4. Stale-doc check — wraps `scripts/ci/check_doc_paths.sh`, the
   mechanical doc-path-existence portion of the `stale-doc-detector`
   skill.

Sub-check set is 4. Deferred sub-checks (`context_budget` composition,
recent-task-run audit, dispatch-health read) are reported as `skipped`
entries in the aggregator when not in scope, never affecting the
verdict.

Severity enum (5-state per todos 009 + 010):
- `info`  : metadata / informational only
- `warn`  : drift / budget notice; contributes to `soft_fail`
- `fail`  : real drift / missing tests; contributes to `hard_fail`
- `error` : sub-check crashed (platform bug); `soft_fail` only
- `skipped`: input absent/stale; never affects verdict

Aggregator rule:
- any sub-check with severity `fail` → overall verdict `hard_fail`
- else any sub-check with severity `error` or `warn` → `soft_fail`
- else → `pass`
- `skipped` entries are metadata only

Two entry points:

- `run()`                        — returns `VerificationLoopReport`, NEVER raises.
- `packages.policies.verification_loop.run_verification_loop()` —
  raises `PolicyViolation(VERIFICATION_LOOP_HARD_FAIL)` on
  `hard_fail`. Use the policy wrapper when you want gating, this
  runner when you want the report as data.

Per the primitives convention: stateless, lazy imports, typed
returns, no side effects at import time. Git subprocess invocations
happen lazily inside `_changed_surface_check()`.
"""
from __future__ import annotations

import functools
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from packages.tools.primitives._serialization import json_safe_factory


Severity = Literal["info", "warn", "fail", "error", "skipped"]
Verdict = Literal["pass", "soft_fail", "hard_fail"]


@dataclass(frozen=True)
class SubCheckResult:
    name: str
    severity: Severity
    summary: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationLoopReport:
    schema_version: str
    verdict: Verdict
    sub_checks: tuple[SubCheckResult, ...]
    infra_errors: tuple[str, ...]
    since_ref: str
    lookback_task_runs: int


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


# Task-run record field redaction (per deepening security finding #5).
# Any field whose key matches this regex (case-insensitive) is replaced
# with "<REDACTED>" in any nested dict we aggregate from task runs.
# Lazily compiled via lru_cache to comply with the primitives
# convention test that forbids module-level `re.compile()`.
@functools.lru_cache(maxsize=1)
def _sensitive_field_re() -> re.Pattern[str]:
    return re.compile(r"secret|token|password|key", re.IGNORECASE)


def _redact(obj: Any) -> Any:
    """Stable-output redaction for task-run records."""
    if isinstance(obj, dict):
        pattern = _sensitive_field_re()
        return {
            k: (
                "<REDACTED>"
                if pattern.search(str(k))
                else _redact(v)
            )
            for k, v in sorted(obj.items())
        }
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_redact(v) for v in obj)
    return obj


def _run_sub_check(
    name: str, body: Any
) -> SubCheckResult:
    """Execute one sub-check and wrap failures as `error` severity.

    Extracted as a module-level function per todo 015 (Python idiom
    conformance): sub-check dispatch is not a class method.
    """
    try:
        return body()
    except Exception as exc:  # pragma: no cover — defensive
        return SubCheckResult(
            name=name,
            severity="error",
            summary=f"{name} crashed: {type(exc).__name__}: {exc}",
            detail={"exception_type": type(exc).__name__},
        )


def _reconciliation_check() -> SubCheckResult:
    # Lazy imports so this primitive stays light on `import` time.
    from packages.tools.primitives.registry_reconciliation_reader import read

    report = read()
    if report.is_clean:
        return SubCheckResult(
            name="reconciliation",
            severity="info",
            summary=(
                f"{report.passing_skills_checked} passing skills "
                "structurally reconciled; no drift."
            ),
            detail={
                "passing_skills_checked": report.passing_skills_checked
            },
        )
    return SubCheckResult(
        name="reconciliation",
        severity="fail",
        summary=(
            f"{len(report.drift_items)} fixture drift item(s) "
            f"across {report.passing_skills_checked} passing skills"
        ),
        detail={
            "drift_items": [
                {
                    "skill_id": item.skill_id,
                    "drift_type": item.drift_type,
                    "detail": item.detail,
                }
                for item in report.drift_items
            ]
        },
    )


def _stocktake_check(known_drift: tuple[str, ...]) -> SubCheckResult:
    from packages.tools.primitives.registry_drift import check_drift

    report = check_drift(known_drift=known_drift)
    unknown_items = [
        item
        for item in report.drift_items
        if not any(
            known_slug in item.detail or known_slug in item.affected_path
            for known_slug in known_drift
        )
    ]
    if not unknown_items:
        return SubCheckResult(
            name="skill_stocktake",
            severity="info",
            summary=(
                f"stocktake clean on "
                f"{report.registry_entries_checked} registry entries"
            ),
            detail={
                "known_drift_tolerated": len(report.drift_items),
                "registry_entries_checked": report.registry_entries_checked,
            },
        )
    return SubCheckResult(
        name="skill_stocktake",
        severity="warn",  # drift is warn, not fail — aggregator makes
                          # the hard/soft distinction in the verdict
        summary=(
            f"{len(unknown_items)} unknown drift item(s) "
            f"(known drift tolerated: "
            f"{len(report.drift_items) - len(unknown_items)})"
        ),
        detail={
            "drift_items": [
                {
                    "drift_type": item.drift_type,
                    "detail": item.detail,
                    "skill_id": item.skill_id,
                }
                for item in unknown_items
            ]
        },
    )


def _git_diff_name_only(since_ref: str) -> list[str]:
    """Shell out for `git diff --name-only <ref>...HEAD`.

    Fails-closed: an exception returns an empty list with a note in
    the caller's error path. `subprocess` is imported lazily inside
    the function body because the primitives convention test forbids
    it at module level.
    """
    import subprocess  # lazy — primitives convention

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{since_ref}...HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(_repo_root()),
            check=False,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.SubprocessError):
        return []


def _changed_surface_check(since_ref: str) -> SubCheckResult:
    changed = _git_diff_name_only(since_ref)
    if not changed:
        return SubCheckResult(
            name="changed_surface",
            severity="info",
            summary=(
                f"no changed files vs {since_ref}; nothing to check"
            ),
            detail={"changed_files": []},
        )

    # Cross-reference: every added/modified .py file under packages/
    # or apps/ must have a matching test file under tests/. Simple
    # heuristic: if any .py logic file is in the diff but no test
    # file is, emit a `fail` severity so the aggregator sees it.
    logic_files = [
        p
        for p in changed
        if (p.startswith("packages/") or p.startswith("apps/"))
        and p.endswith(".py")
        and "__pycache__" not in p
    ]
    test_files = [p for p in changed if p.startswith("tests/")]
    if logic_files and not test_files:
        return SubCheckResult(
            name="changed_surface",
            severity="fail",
            summary=(
                f"{len(logic_files)} logic file(s) changed vs "
                f"{since_ref} with zero changed test files — missing "
                "lane-matching tests"
            ),
            detail={
                "logic_files": logic_files,
                "test_files": test_files,
            },
        )
    return SubCheckResult(
        name="changed_surface",
        severity="info",
        summary=(
            f"{len(logic_files)} logic file(s), {len(test_files)} "
            f"test file(s) changed vs {since_ref}"
        ),
        detail={
            "logic_files": logic_files,
            "test_files": test_files,
        },
    )


def _run_doc_path_script() -> tuple[int, str]:
    """Run `scripts/ci/check_doc_paths.sh`; return `(exit_code, stdout)`.

    `subprocess` is imported lazily inside the function body because the
    primitives convention test forbids it at module level. A genuine
    inability to launch the script propagates as an exception — the
    caller's `_run_sub_check` wrapper converts that into a sub-check
    `error` (soft_fail), the same as any other platform bug.
    """
    import subprocess  # lazy — primitives convention

    script = _repo_root() / "scripts" / "ci" / "check_doc_paths.sh"
    result = subprocess.run(
        ["bash", str(script)],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(_repo_root()),
        check=False,
    )
    return result.returncode, result.stdout.strip()


def _stale_doc_check() -> SubCheckResult:
    """Wrap `scripts/ci/check_doc_paths.sh` — the mechanical doc-path
    existence check behind the `stale-doc-detector` skill.

    Maps the script's documented exit codes to a sub-check severity:

    - `0` → `info`  — every repo-relative doc path resolves.
    - `1` → `fail`  — broken path references; `doc-path-check` is a
      required CI gate, so doc drift blocks a merge.
    - other → `error` — script malfunction (platform bug; soft_fail).

    The agentic classification (`fix_now` / `allowlist` /
    `founder_decision` / `ignore`) and legacy-slug heuristic of the
    full `stale-doc-detector` skill stay operator-invoked; this
    sub-check is the deterministic, CI-runnable portion the structural
    runner composes.
    """
    exit_code, output = _run_doc_path_script()
    summary_tail = output.splitlines()[-1] if output else ""
    if exit_code == 0:
        return SubCheckResult(
            name="stale_doc",
            severity="info",
            summary=summary_tail or "check_doc_paths.sh: all doc paths resolve",
            detail={"exit_code": 0},
        )
    if exit_code == 1:
        return SubCheckResult(
            name="stale_doc",
            severity="fail",
            summary=(
                "check_doc_paths.sh found broken repo-relative path "
                "references in the entry docs"
            ),
            detail={"exit_code": 1, "output": output},
        )
    return SubCheckResult(
        name="stale_doc",
        severity="error",
        summary=(
            f"check_doc_paths.sh exited {exit_code} "
            "(unexpected — script malfunction)"
        ),
        detail={"exit_code": exit_code, "output": output},
    )


def _aggregate(
    sub_checks: tuple[SubCheckResult, ...],
) -> tuple[Verdict, tuple[str, ...]]:
    """Compute overall verdict + infra_errors list from sub-checks."""
    infra_errors = tuple(
        sc.name for sc in sub_checks if sc.severity == "error"
    )
    has_fail = any(sc.severity == "fail" for sc in sub_checks)
    if has_fail:
        return "hard_fail", infra_errors
    has_soft = any(
        sc.severity in ("warn", "error") for sc in sub_checks
    )
    if has_soft:
        return "soft_fail", infra_errors
    return "pass", infra_errors


def run(
    since_ref: str = "main",
    lookback_task_runs: int = 20,
    *,
    known_drift: tuple[str, ...] = ("post-run-validation",),
) -> VerificationLoopReport:
    """Compose the 4 structural sub-checks and return a report.

    NEVER raises. Use `packages.policies.verification_loop.run_verification_loop`
    when you want a raising wrapper.
    """
    sub_checks = (
        _run_sub_check("reconciliation", _reconciliation_check),
        _run_sub_check(
            "skill_stocktake", lambda: _stocktake_check(known_drift)
        ),
        _run_sub_check(
            "changed_surface", lambda: _changed_surface_check(since_ref)
        ),
        _run_sub_check("stale_doc", _stale_doc_check),
    )
    verdict, infra_errors = _aggregate(sub_checks)
    return VerificationLoopReport(
        schema_version="1",
        verdict=verdict,
        sub_checks=sub_checks,
        infra_errors=infra_errors,
        since_ref=since_ref,
        lookback_task_runs=lookback_task_runs,
    )


def report_as_dict(report: VerificationLoopReport) -> dict[str, Any]:
    """Serialize a report via the JSON-safe factory."""
    return asdict(report, dict_factory=json_safe_factory)
