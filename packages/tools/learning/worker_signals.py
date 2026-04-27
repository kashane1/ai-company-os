"""Adaptive feedback loop — read recent rejection patterns and
materialize them as TaskPacket constraint strings the supervisor folds
into freshly-decomposed packets.

CRITICAL SECURITY PROPERTY (C1 fix from review):
    Constraint output is **only** drawn from the static
    ``_FAILURE_CODE_TO_CONSTRAINT`` allowlist. ``validation_checks[*].details``
    text from TaskRun JSON files is NEVER echoed into prompt-shaped
    output. A same-uid attacker writing a crafted TaskRun cannot inject
    arbitrary imperatives into downstream worker prompts.

The mapping is treated as policy: changes go through the same review as
``packages/policies/`` edits.

Recurrence threshold (best-practices research, Reflexion/Devin/Replit):
a constraint is only injected after the same ``failure_code`` has
occurred ≥ ``min_recurrence_count`` times in the lane within the
lookback window. Single-occurrence noise is suppressed.

Stateless module-level. Lazy imports. Never raises (returns ``{}`` on
any error path so the supervisor remains hot).
"""

from __future__ import annotations

import functools
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from packages.schemas.task_packet import WorkerLane
from packages.schemas.task_run import EngineeringResultClassification
from packages.schemas.testing import ValidationFailureCode


SIGNAL_INJECTION_DISABLED_ENV_VAR = "AI_COMPANY_OS_DISABLE_SIGNAL_INJECTION"
_MEMOIZATION_TTL_SECONDS = 60


_FAILURE_CODE_TO_CONSTRAINT: dict[ValidationFailureCode, str] = {
    ValidationFailureCode.MISSING_TESTS_FOR_LOGIC_CHANGE: (
        "Recent rejection pattern: ship a test for any logic-bearing change. "
        "If the change is config-only, set a no_test_reason_code."
    ),
    ValidationFailureCode.MISSING_TESTING_METADATA: (
        "Recent rejection pattern: include testing metadata "
        "(tests_required, test_lane, no_test_reason_code) in the result."
    ),
    ValidationFailureCode.INVALID_NO_TEST_REASON_CODE: (
        "Recent rejection pattern: use only the allowed_no_test_reason_codes "
        "from the packet; do not invent new codes."
    ),
    ValidationFailureCode.INVALID_FOLLOWUP_TEST_TASK_REFERENCE: (
        "Recent rejection pattern: when claiming APPROVED_FOLLOWUP_TEST_TASK, "
        "the followup_task_id must reference a real task in this batch."
    ),
}

_ROOT_CAUSE_CONSTRAINTS: dict[str, str] = {
    "ambiguous-task-spec": (
        "Recent ambiguous-task-spec postmortem in this lane — be precise about "
        "acceptance criteria and forbidden areas before you start."
    ),
    "policy-miss": (
        "Recent policy-miss postmortem in this lane — re-read packages/policies/ "
        "for any rule your task touches."
    ),
    "tool-limitation": (
        "Recent tool-limitation postmortem in this lane — surface tool gaps "
        "explicitly rather than working around them."
    ),
    "external-dependency": (
        "Recent external-dependency postmortem in this lane — verify external "
        "service availability before relying on it."
    ),
    "worker-prompt-drift": (
        "Recent worker-prompt-drift postmortem in this lane — confirm packet "
        "constraints are honored before reporting completion."
    ),
}


@dataclass(frozen=True)
class SignalQuery:
    lookback_days: int = 30
    max_per_lane: int = 5
    min_recurrence_count: int = 3
    now_iso: str | None = None
    task_runs_root: Path | None = None
    postmortems_root: Path | None = None
    audit_log_path: Path | None = None


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _resolve_paths(query: SignalQuery) -> tuple[Path, Path, Path]:
    if query.task_runs_root and query.postmortems_root and query.audit_log_path:
        return query.task_runs_root, query.postmortems_root, query.audit_log_path
    from packages.config.settings import ensure_runtime_directories

    paths = ensure_runtime_directories()
    return (
        query.task_runs_root or paths.task_runs_root,
        query.postmortems_root or paths.postmortems_root,
        query.audit_log_path or paths.postmortem_audit_log_path,
    )


def _load_recent_task_run_failures(
    *,
    task_runs_root: Path,
    cutoff: datetime,
) -> list[tuple[str, str]]:
    """Return ``[(lane_value, failure_code), ...]`` for VALIDATION_FAILED runs.

    Skips corrupt files. Never raises.
    """
    out: list[tuple[str, str]] = []
    if not task_runs_root.exists():
        return out
    for child in task_runs_root.glob("*.json"):
        try:
            payload = json.loads(child.read_text())
        except Exception:
            continue
        classification = payload.get("classification")
        if classification != EngineeringResultClassification.VALIDATION_FAILED.value:
            continue
        finished = payload.get("finished_at") or payload.get("started_at")
        if finished:
            try:
                if _parse_iso(str(finished)) < cutoff:
                    continue
            except Exception:
                pass
        lane = str(payload.get("worker_lane", "unknown"))
        for code in payload.get("failure_codes") or []:
            out.append((lane, str(code)))
    return out


def _load_recent_open_postmortems(
    *,
    postmortems_root: Path,
    cutoff: datetime,
) -> list[tuple[str, str]]:
    """Return ``[(lane, root_cause_category), ...]`` for OPEN postmortems
    with non-UNKNOWN root cause."""
    out: list[tuple[str, str]] = []
    if not postmortems_root.exists():
        return out
    for child in postmortems_root.glob("*.json"):
        if child.name == "index.json":
            continue
        try:
            payload = json.loads(child.read_text())
        except Exception:
            continue
        if payload.get("status") != "open":
            continue
        category = payload.get("root_cause_category", "unknown")
        if category == "unknown":
            continue
        created = payload.get("created_at")
        if created:
            try:
                if _parse_iso(str(created)) < cutoff:
                    continue
            except Exception:
                pass
        lane = str(payload.get("lane", "unknown"))
        out.append((lane, str(category)))
    return out


def categorize_rejection_pattern(
    *,
    task_run_failures: list[tuple[str, str]],
    open_postmortem_categories: list[tuple[str, str]] | None = None,
    min_recurrence_count: int = 3,
    max_per_lane: int = 5,
) -> dict[str, list[str]]:
    """Pure function: classify (lane, failure_code) pairs into constraint strings.

    Recurrence threshold suppresses single-occurrence noise.
    Output strings are drawn ONLY from the static allowlist (C1 fix).
    """
    by_lane: dict[str, dict[str, int]] = {}
    for lane, code in task_run_failures:
        by_lane.setdefault(lane, {}).setdefault(code, 0)
        by_lane[lane][code] += 1

    code_to_str: dict[str, str] = {
        member.value: text for member, text in _FAILURE_CODE_TO_CONSTRAINT.items()
    }

    result: dict[str, list[str]] = {}
    for lane, code_counts in by_lane.items():
        constraints: list[str] = []
        # Stable selection: most-frequent first, then lexical for determinism.
        ranked = sorted(code_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        for code, count in ranked:
            if count < min_recurrence_count:
                continue
            constraint = code_to_str.get(code)
            if constraint is None:
                continue
            constraints.append(constraint)
            if len(constraints) >= max_per_lane:
                break
        if constraints:
            result[lane] = constraints

    # Postmortem-derived constraints: at most ONE generic per lane per category.
    for lane, category in open_postmortem_categories or []:
        text = _ROOT_CAUSE_CONSTRAINTS.get(category)
        if text is None:
            continue
        bucket = result.setdefault(lane, [])
        if text not in bucket and len(bucket) < max_per_lane:
            bucket.append(text)

    return result


@functools.lru_cache(maxsize=8)
def _cached_signals(query_key: tuple, now_bucket: int) -> dict[str, list[str]]:
    return _compute_signals(query_key)


def _compute_signals(query_key: tuple) -> dict[str, list[str]]:
    (
        lookback_days,
        max_per_lane,
        min_recurrence_count,
        now_iso,
        task_runs_root_str,
        postmortems_root_str,
        audit_log_str,
    ) = query_key
    if not now_iso:
        now_iso = datetime.now(timezone.utc).isoformat()
    cutoff = _parse_iso(now_iso) - _timedelta_days(lookback_days)
    task_runs_root = Path(task_runs_root_str)
    postmortems_root = Path(postmortems_root_str)
    failures = _load_recent_task_run_failures(
        task_runs_root=task_runs_root, cutoff=cutoff
    )
    pm_categories = _load_recent_open_postmortems(
        postmortems_root=postmortems_root, cutoff=cutoff
    )
    return categorize_rejection_pattern(
        task_run_failures=failures,
        open_postmortem_categories=pm_categories,
        min_recurrence_count=min_recurrence_count,
        max_per_lane=max_per_lane,
    )


def _timedelta_days(days: int):
    from datetime import timedelta

    return timedelta(days=days)


def load_recent_signals(query: SignalQuery | None = None) -> dict[str, list[str]]:
    """Return lane-keyed list of imperative constraint strings.

    Empty dict on cold start (no task_runs and no postmortems). Never
    raises. Honors ``AI_COMPANY_OS_DISABLE_SIGNAL_INJECTION=1`` kill-switch.
    """
    if os.environ.get(SIGNAL_INJECTION_DISABLED_ENV_VAR) == "1":
        return {}
    query = query or SignalQuery()
    try:
        task_runs_root, postmortems_root, audit_log_path = _resolve_paths(query)
        query_key = (
            query.lookback_days,
            query.max_per_lane,
            query.min_recurrence_count,
            query.now_iso,
            str(task_runs_root),
            str(postmortems_root),
            str(audit_log_path),
        )
        now_bucket = int(time.time() / _MEMOIZATION_TTL_SECONDS)
        return _cached_signals(query_key, now_bucket)
    except Exception:
        return {}


def augment_packet_constraints(
    *,
    lane: str,
    base_constraints: list[str],
    signals_provider=load_recent_signals,
) -> list[str]:
    """Append signal-derived constraints to a packet's constraints list.

    Idempotent: existing strings are not duplicated. Never raises.
    """
    try:
        signals = signals_provider()
    except Exception:
        return list(base_constraints)
    extras = signals.get(lane) or signals.get("unknown") or []
    out = list(base_constraints)
    for extra in extras:
        if extra not in out:
            out.append(extra)
    return out
