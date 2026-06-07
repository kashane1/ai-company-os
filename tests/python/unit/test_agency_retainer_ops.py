import json

import pytest

from packages.agency.retainer_ops import (
    mark_action_complete,
    outstanding_actions,
    plan_retainer_run,
    read_retainer_run,
    write_retainer_run,
)


def _record() -> dict[str, object]:
    return {
        "id": "joes-plumbing-site",
        "client": {
            "billing_status": "active",
            "services": ["local_seo", "monthly_reporting", "google_ads", "reviews"],
        },
    }


def test_plan_retainer_run_lists_actions_and_blocked_approvals() -> None:
    run = plan_retainer_run(_record(), month="2026-06")

    assert "run_local_seo" in run.planned_actions
    assert "run_monthly_report" in run.planned_actions
    assert "draft_google_ads" in run.planned_actions
    assert "client_site_deploy" in run.blocked_approvals
    assert "ad_campaign_go_live" in run.blocked_approvals
    assert "review_sms_activation" in run.blocked_approvals


def test_managed_booking_plans_action() -> None:
    client = {"billing_status": "active", "services": ["booking_native"]}
    run = plan_retainer_run({"id": "acme-site", "client": client}, month="2026-06")
    assert "manage_booking" in run.planned_actions


def test_booking_management_plans_action() -> None:
    client = {"billing_status": "active", "services": ["booking_connect", "booking_management"]}
    run = plan_retainer_run({"id": "acme-site", "client": client}, month="2026-06")
    assert "manage_booking" in run.planned_actions


def test_hosting_plans_lead_health_check() -> None:
    record = {"id": "acme-site", "client": {"billing_status": "active", "services": ["hosting"]}}
    run = plan_retainer_run(record, month="2026-06")
    assert "check_lead_health" in run.planned_actions


def test_inactive_client_gets_no_paid_work() -> None:
    for status in ("past_due", "cancelled", "disputed", "refunded", "trial"):
        record = {
            "id": "lapsed-site",
            "client": {"billing_status": status, "services": ["local_seo", "google_ads"]},
        }
        run = plan_retainer_run(record, month="2026-06")
        assert run.planned_actions == []
        assert run.blocked_approvals == []
        assert run.billing_status == status
        assert "not active" in run.skipped_reason


def test_missing_billing_status_is_treated_as_inactive() -> None:
    # Loudly-safe: an absent status must NOT entitle a client to paid work.
    record = {"id": "unknown-site", "client": {"services": ["local_seo"]}}
    run = plan_retainer_run(record, month="2026-06")
    assert run.planned_actions == []
    assert run.skipped_reason


def test_write_retainer_run(tmp_path) -> None:
    run = plan_retainer_run(_record(), month="2026-06")

    path = write_retainer_run(tmp_path, run)

    assert path == tmp_path / "clients" / "joes-plumbing-site" / "retainer-runs" / "2026-06.json"
    assert json.loads(path.read_text(encoding="utf-8"))["product_id"] == "joes-plumbing-site"


def test_mark_action_complete_tracks_outstanding(tmp_path) -> None:
    run = plan_retainer_run(_record(), month="2026-06")
    write_retainer_run(tmp_path, run)

    assert not run.is_complete()
    pid, month = "joes-plumbing-site", "2026-06"

    # Complete every planned action; the run should converge to done.
    for action in list(run.planned_actions):
        mark_action_complete(tmp_path, pid, month, action)

    assert outstanding_actions(tmp_path, pid, month) == []
    assert read_retainer_run(tmp_path, pid, month).is_complete()


def test_mark_action_complete_is_idempotent_and_validated(tmp_path) -> None:
    run = plan_retainer_run(_record(), month="2026-06")
    write_retainer_run(tmp_path, run)
    pid, month = "joes-plumbing-site", "2026-06"

    mark_action_complete(tmp_path, pid, month, "run_local_seo")
    again = mark_action_complete(tmp_path, pid, month, "run_local_seo")
    assert again.completed_actions.count("run_local_seo") == 1

    with pytest.raises(ValueError):
        mark_action_complete(tmp_path, pid, month, "not_a_planned_action")
