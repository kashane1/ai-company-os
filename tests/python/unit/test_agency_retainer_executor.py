"""Retainer executor: safe-action execution + outward-action gate enforcement."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from packages.agency.retainer_executor import (
    ActionPreconditionError,
    assert_outward_action_allowed,
    default_safe_executors,
    execute_retainer_run,
)
from packages.agency.retainer_ops import RetainerRun, plan_retainer_run, write_retainer_run
from packages.db.approval_store import ApprovalStore
from packages.policies.approvals import PolicyViolation
from packages.schemas.approval import ApprovalRecord, ApprovalStatus


def _run(planned, blocked=(), services=("hosting", "contact_forms")) -> RetainerRun:
    return RetainerRun(
        product_id="joe-site",
        month="2026-06",
        services=list(services),
        planned_actions=list(planned),
        blocked_approvals=list(blocked),
        billing_status="active",
    )


# --- execute_retainer_run -------------------------------------------------------


def test_runs_registered_executor_and_marks_complete(tmp_path: Path) -> None:
    run = _run(["check_lead_health"])
    write_retainer_run(tmp_path, run)
    calls: list[str] = []

    def _exec(r):
        calls.append(r.product_id)
        return "did the thing"

    report = execute_retainer_run(
        run, executors={"check_lead_health": _exec}, state_root=tmp_path
    )
    assert calls == ["joe-site"]
    assert report.ok()
    assert report.outcomes[0].status == "done"
    # Completion is tracked on disk.
    from packages.agency.retainer_ops import read_retainer_run

    persisted = read_retainer_run(tmp_path, "joe-site", "2026-06")
    assert persisted.completed_actions == ["check_lead_health"]


def test_unregistered_action_is_skipped_as_operator_run() -> None:
    run = _run(["draft_google_ads"])
    report = execute_retainer_run(run, executors={}, mark_complete=False)
    assert report.outcomes[0].status == "skipped"
    assert "operator-run" in report.outcomes[0].detail


def test_precondition_error_skips_that_action() -> None:
    def _needs_input(_r):
        raise ActionPreconditionError("matrix not approved")

    report = execute_retainer_run(
        _run(["run_local_seo"]), executors={"run_local_seo": _needs_input}, mark_complete=False
    )
    assert report.outcomes[0].status == "skipped"
    assert "matrix not approved" in report.outcomes[0].detail
    assert report.ok()  # a skip is not a failure


def test_executor_exception_is_recorded_as_failure_and_does_not_abort() -> None:
    def _boom(_r):
        raise RuntimeError("kaboom")

    def _fine(_r):
        return "ok"

    report = execute_retainer_run(
        _run(["draft_gbp_changeset", "check_lead_health"]),
        executors={"draft_gbp_changeset": _boom, "check_lead_health": _fine},
        mark_complete=False,
    )
    statuses = {o.action: o.status for o in report.outcomes}
    assert statuses == {"draft_gbp_changeset": "failed", "check_lead_health": "done"}
    assert not report.ok()


def test_blocked_approvals_are_surfaced_not_executed() -> None:
    run = _run(["draft_google_ads"], blocked=["ad_campaign_go_live"])
    report = execute_retainer_run(run, executors={}, mark_complete=False)
    assert report.pending_approvals == ["ad_campaign_go_live"]


# --- assert_outward_action_allowed (gate enforcement) ---------------------------


def test_outward_action_refused_without_approval() -> None:
    # Ad go-live needs budget caps AND a granted approval — refuse on missing caps.
    with pytest.raises(PolicyViolation):
        assert_outward_action_allowed(
            "ad_campaign_go_live",
            product_id="joe-site",
            approval_id="a1",
            daily_budget=None,
            monthly_budget=None,
        )


def test_unknown_outward_action_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown outward action"):
        assert_outward_action_allowed("teleport_client", product_id="joe-site", approval_id="a1")


def test_outward_action_allowed_with_granted_approval(isolated_repo_root, tmp_path: Path) -> None:
    artifact = tmp_path / "ads.md"
    artifact.write_text("draft", encoding="utf-8")
    store = ApprovalStore()
    store.save(
        ApprovalRecord(
            id="appr-ads",
            status=ApprovalStatus.APPROVED,
            summary="Launch ads",
            created_at="2026-06-03T00:00:00+00:00",
            approval_type="ad_campaign_go_live",
            subject_type="client_site",
            subject_id="joe-site",
            action="launch_google_ads_campaign",
            review_artifact_path=str(artifact),
        )
    )
    # With caps + a correctly-scoped granted approval, the gate passes (no raise).
    assert_outward_action_allowed(
        "ad_campaign_go_live",
        product_id="joe-site",
        approval_id="appr-ads",
        daily_budget=50,
        monthly_budget=1000,
        store=store,
    )


def test_review_sms_outward_requires_docs_root() -> None:
    with pytest.raises(ValueError, match="docs_root"):
        assert_outward_action_allowed(
            "review_sms_activation", product_id="joe-site", approval_id="a1"
        )


# --- default_safe_executors -----------------------------------------------------


def test_default_executors_run_lead_health(tmp_path: Path) -> None:
    # An undelivered lead on a contact_forms client -> the executor reports it.
    leads = tmp_path / "clients" / "joe-site" / "leads"
    leads.mkdir(parents=True)
    (leads / "a.json").write_text(
        '{"submission_id":"a","received_at":"2026-06-05T00:00:00Z","notified_at":null}'
    )
    run = _run(["check_lead_health"])
    write_retainer_run(tmp_path, run)

    execs = default_safe_executors(state_root=tmp_path, as_of=date(2026, 6, 7))
    report = execute_retainer_run(run, executors=execs, state_root=tmp_path)

    outcome = report.outcomes[0]
    assert outcome.status == "done"
    assert "alert" in outcome.detail and "1 undelivered" in outcome.detail


def test_default_executors_does_not_auto_run_outward_drafts() -> None:
    # The growth drafts are NOT wired by default (need operator input) -> skipped.
    record = {
        "id": "joe-site",
        "client": {
            "billing_status": "active",
            "services": ["hosting", "contact_forms", "google_ads", "local_seo"],
        },
    }
    run = plan_retainer_run(record, month="2026-06")
    execs = default_safe_executors(state_root=Path("/tmp"), as_of=date(2026, 6, 7))
    report = execute_retainer_run(run, executors=execs, mark_complete=False)

    by_action = {o.action: o.status for o in report.outcomes}
    assert by_action["check_lead_health"] == "done"
    assert by_action["draft_google_ads"] == "skipped"
    assert by_action["run_local_seo"] == "skipped"
    # The ad go-live stays gated, never executed.
    assert "ad_campaign_go_live" in report.pending_approvals
