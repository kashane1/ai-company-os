"""Verification-loop-runtime runner primitive (harness learning loop).

The verification-loop split documented at
``skills/canonical/verification-loop/skill.md:122-127`` triggers when a
4th sub-check would land. This module is the runtime-evidence half:

- **Structural drift** (``verification_loop_runner.py``) answers:
  *"Is the registry honest about what exists?"*
- **Runtime evidence** (this module) answers:
  *"Is the system behaving as we intended over time?"*

The failing party is usually the operator (founder hasn't reviewed
``OPEN`` postmortems), not the registry — different verdict semantics
than structural drift.

This runner is also load-bearing for the H1 security mitigation: the
``stale_postmortems`` sub-check cross-checks ``RESOLVED`` postmortems
against the audit log so a same-uid attacker cannot silently suppress
the staleness alarm by directly mutating ``status``.

Mirrors ``verification_loop_runner`` conventions:
- Stateless module-level.
- Lazy imports.
- Typed returns; never raises (errors become ``severity: error``).
- No I/O at import time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Severity = Literal["info", "warn", "fail", "error", "skipped"]
Verdict = Literal["pass", "soft_fail", "hard_fail"]


@dataclass(frozen=True)
class SubCheckResult:
    name: str
    severity: Severity
    summary: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationLoopRuntimeReport:
    schema_version: str
    verdict: Verdict
    sub_checks: tuple[SubCheckResult, ...]
    infra_errors: tuple[str, ...]


def _run_sub_check(name: str, body: Any) -> SubCheckResult:
    try:
        return body()
    except Exception as exc:  # pragma: no cover — defensive
        return SubCheckResult(
            name=name,
            severity="error",
            summary=f"{name} crashed: {type(exc).__name__}: {exc}",
            detail={"exception_type": type(exc).__name__},
        )


def _stale_postmortems_check(
    *,
    now_iso: str | None = None,
    threshold_days: int = 14,
) -> SubCheckResult:
    """Scan ``state/postmortems/`` for OPEN records older than ``threshold_days``.

    Severity rule:
    - 0 stale: ``info``
    - 1+ stale, none > 30 days: ``warn``
    - any > 30 days: ``warn`` (still soft_fail; never hard_fail — a stale
      postmortem is operator hygiene, not a merge blocker)

    Also: cross-check RESOLVED records against the audit log. Any
    RESOLVED postmortem with no matching audit entry → ``warn`` (H1
    mitigation: a same-uid attacker bypassing ``update_status`` would
    leave records without audit trail).
    """
    from packages.db.postmortem_store import PostMortemStore
    from packages.policies.postmortem_retention import (
        STALE_THRESHOLD_DAYS,
        CRITICAL_AGE_DAYS,
        _age_days,
        is_stale,
        now_utc_iso,
    )
    from packages.schemas.postmortem import PostMortemStatus

    threshold = threshold_days if threshold_days != 14 else STALE_THRESHOLD_DAYS
    iso = now_iso or now_utc_iso()
    store = PostMortemStore()

    all_records = list(store.list_recent(now_iso=iso, max_age_days=365))
    stale = [r for r in all_records if is_stale(r, now_iso=iso, threshold_days=threshold)]

    # H1 cross-check: every RESOLVED record must have an audit entry.
    audit_records = store.read_audit_log()
    audited_ids = {a.get("postmortem_id") for a in audit_records if a.get("new_status") == "resolved"}
    resolved_without_audit = [
        r for r in all_records
        if r.status is PostMortemStatus.RESOLVED and r.id not in audited_ids
    ]

    if not stale and not resolved_without_audit:
        return SubCheckResult(
            name="stale_postmortems",
            severity="info",
            summary=(
                f"No open postmortems older than {threshold} days; "
                f"all RESOLVED records have audit entries."
            ),
            detail={
                "open_postmortems_total": sum(1 for r in all_records if r.status is PostMortemStatus.OPEN),
                "resolved_postmortems_total": sum(1 for r in all_records if r.status is PostMortemStatus.RESOLVED),
            },
        )

    over_critical = [
        r for r in stale
        if _age_days(r, now_iso=iso) > CRITICAL_AGE_DAYS
    ]

    parts: list[str] = []
    if stale:
        parts.append(
            f"{len(stale)} open postmortem(s) older than {threshold} days"
            + (f" ({len(over_critical)} > {CRITICAL_AGE_DAYS} days)" if over_critical else "")
        )
    if resolved_without_audit:
        parts.append(
            f"{len(resolved_without_audit)} RESOLVED postmortem(s) without audit log entry"
        )

    return SubCheckResult(
        name="stale_postmortems",
        severity="warn",
        summary="; ".join(parts),
        detail={
            "stale_ids": [r.id for r in stale],
            "stale_over_critical_ids": [r.id for r in over_critical],
            "resolved_without_audit_ids": [r.id for r in resolved_without_audit],
        },
    )


def _aggregate(
    sub_checks: tuple[SubCheckResult, ...],
) -> tuple[Verdict, tuple[str, ...]]:
    infra_errors = tuple(sc.name for sc in sub_checks if sc.severity == "error")
    has_fail = any(sc.severity == "fail" for sc in sub_checks)
    if has_fail:
        return "hard_fail", infra_errors
    has_soft = any(sc.severity in ("warn", "error") for sc in sub_checks)
    if has_soft:
        return "soft_fail", infra_errors
    return "pass", infra_errors


def run(
    *,
    now_iso: str | None = None,
    threshold_days: int = 14,
) -> VerificationLoopRuntimeReport:
    """Compose the runtime-evidence sub-checks. NEVER raises."""
    sub_checks = (
        _run_sub_check(
            "stale_postmortems",
            lambda: _stale_postmortems_check(now_iso=now_iso, threshold_days=threshold_days),
        ),
    )
    verdict, infra_errors = _aggregate(sub_checks)
    return VerificationLoopRuntimeReport(
        schema_version="1",
        verdict=verdict,
        sub_checks=sub_checks,
        infra_errors=infra_errors,
    )
