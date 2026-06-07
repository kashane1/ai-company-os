"""Execute a planned retainer run — and gate every outward action.

Two responsibilities the planner (``retainer_ops``) deliberately doesn't have:

1. **Run the safe prep actions.** ``plan_retainer_run`` only produces a list of
   action strings; this runs the ones with a registered executor (drafting,
   health checks — all local artifact generation, nothing outward), records a
   per-action outcome, and marks each complete (``mark_action_complete``).

2. **Gate the outward actions.** The irreversible/outward steps (ad go-live,
   review SMS, client-site deploy) live in ``run.blocked_approvals`` and are NEVER
   auto-run. :func:`assert_outward_action_allowed` is the single sanctioned entry
   point for performing one — it routes to the matching policy gate, so the gates
   are enforced from production code (not only tests). Without a granted approval
   it raises ``PolicyViolation``.

Safe actions and outward actions are kept strictly apart: an executor here can
only ever produce a draft/artifact for operator review. Going live stays behind
:func:`assert_outward_action_allowed`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from packages.agency.approvals import RETAINER_APPROVALS
from packages.agency.retainer_ops import RetainerRun, mark_action_complete
from packages.db.approval_store import ApprovalStore
from packages.policies.agency_gates import (
    assert_ad_campaign_go_live,
    assert_retainer_approval_granted,
    assert_review_sms_allowed,
)

# An executor takes the planned run and returns a human-readable detail string.
# It may raise ActionPreconditionError to signal "skipped — missing input", or any
# other exception to signal a failure (recorded per-action, never aborts the run).
RetainerActionExecutor = Callable[[RetainerRun], str]


class ActionPreconditionError(RuntimeError):
    """An executor's inputs aren't ready yet (e.g. an unapproved matrix) — skip it."""


def assert_outward_action_allowed(
    approval_key: str,
    *,
    product_id: str,
    approval_id: str,
    store: ApprovalStore | None = None,
    daily_budget: float | None = None,
    monthly_budget: float | None = None,
    docs_root: Path | None = None,
    template_approved: bool = False,
    quiet_hours_configured: bool = True,
    frequency_cap_days: int = 90,
) -> None:
    """Authorize one outward/irreversible retainer action, or raise ``PolicyViolation``.

    The single production entry point that wires the policy gates: any code that
    performs an outward step (ad go-live, review SMS, client-site deploy, …) must
    call this first. Routes ``approval_key`` to its specific gate; unknown keys
    raise ``ValueError`` so a typo can't silently skip enforcement.
    """
    if approval_key == "ad_campaign_go_live":
        assert_ad_campaign_go_live(
            approval_id,
            product_id=product_id,
            daily_budget=daily_budget,
            monthly_budget=monthly_budget,
            store=store,
        )
    elif approval_key == "review_sms_activation":
        if docs_root is None:
            raise ValueError("review_sms_activation requires docs_root")
        assert_review_sms_allowed(
            docs_root=docs_root,
            product_id=product_id,
            approval_id=approval_id,
            template_approved=template_approved,
            quiet_hours_configured=quiet_hours_configured,
            frequency_cap_days=frequency_cap_days,
            store=store,
        )
    elif approval_key in RETAINER_APPROVALS:
        assert_retainer_approval_granted(
            approval_id,
            product_id=product_id,
            approval_type=approval_key,
            store=store,
        )
    else:
        raise ValueError(f"unknown outward action {approval_key!r}")


@dataclass(frozen=True)
class ActionOutcome:
    action: str
    status: str  # "done" | "skipped" | "failed"
    detail: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"action": self.action, "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class ExecutionReport:
    product_id: str
    month: str
    outcomes: list[ActionOutcome] = field(default_factory=list)
    # Outward steps the executor deliberately did NOT run — each needs a granted
    # approval via assert_outward_action_allowed before it can go live.
    pending_approvals: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        """True when no action failed (skips are fine — they're operator-run/blocked)."""
        return all(o.status != "failed" for o in self.outcomes)

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "month": self.month,
            "ok": self.ok(),
            "outcomes": [o.to_dict() for o in self.outcomes],
            "pending_approvals": list(self.pending_approvals),
        }


def execute_retainer_run(
    run: RetainerRun,
    *,
    executors: dict[str, RetainerActionExecutor],
    state_root: Path | None = None,
    mark_complete: bool = True,
) -> ExecutionReport:
    """Run the safe prep actions of a planned run; surface outward steps as pending.

    Each planned action with a registered executor runs and is marked complete;
    actions without one are skipped as "operator-run". A precondition error skips
    that action; any other exception is recorded as a failure and the run
    continues (one bad action never aborts the month). Outward actions are not run
    here — they're returned as ``pending_approvals``.
    """
    outcomes: list[ActionOutcome] = []
    for action in run.planned_actions:
        executor = executors.get(action)
        if executor is None:
            outcomes.append(
                ActionOutcome(action, "skipped", "no executor registered — operator-run")
            )
            continue
        try:
            detail = executor(run)
        except ActionPreconditionError as exc:
            outcomes.append(ActionOutcome(action, "skipped", f"precondition: {exc}"))
            continue
        except Exception as exc:  # noqa: BLE001 - per-action failure is recorded, never aborts the month
            outcomes.append(ActionOutcome(action, "failed", str(exc)))
            continue
        outcomes.append(ActionOutcome(action, "done", detail))
        if mark_complete and state_root is not None:
            mark_action_complete(state_root, run.product_id, run.month, action)
    return ExecutionReport(
        product_id=run.product_id,
        month=run.month,
        outcomes=outcomes,
        pending_approvals=list(run.blocked_approvals),
    )


def default_safe_executors(
    *, state_root: Path, as_of: date
) -> dict[str, RetainerActionExecutor]:
    """The safe, self-contained executors wired by default.

    Only ``check_lead_health`` is fully safe to auto-run today (it assesses already-
    drained local lead data). The other planned actions need operator-supplied
    inputs (intake, approved matrices) and remain unregistered → reported as
    "operator-run" until each grows a vetted executor.
    """
    from packages.agency.lead_health import assess_lead_health, load_leads_from_dir

    def _check_lead_health(run: RetainerRun) -> str:
        leads_dir = state_root / "clients" / run.product_id / "leads"
        health = assess_lead_health(
            load_leads_from_dir(leads_dir),
            product_id=run.product_id,
            as_of=as_of,
            lead_capture_expected="contact_forms" in run.services,
        )
        return (
            f"lead health: {health.status.value}; "
            f"{health.undelivered_in_window} undelivered in window"
        )

    return {"check_lead_health": _check_lead_health}
