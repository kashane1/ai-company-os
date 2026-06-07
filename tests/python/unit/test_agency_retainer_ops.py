import json

from packages.agency.retainer_ops import plan_retainer_run, write_retainer_run


def _record() -> dict[str, object]:
    return {
        "id": "joes-plumbing-site",
        "client": {
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
    record = {"id": "acme-site", "client": {"services": ["booking_native"]}}
    run = plan_retainer_run(record, month="2026-06")
    assert "manage_booking" in run.planned_actions


def test_booking_management_plans_action() -> None:
    record = {"id": "acme-site", "client": {"services": ["booking_connect", "booking_management"]}}
    run = plan_retainer_run(record, month="2026-06")
    assert "manage_booking" in run.planned_actions


def test_write_retainer_run(tmp_path) -> None:
    run = plan_retainer_run(_record(), month="2026-06")

    path = write_retainer_run(tmp_path, run)

    assert path == tmp_path / "clients" / "joes-plumbing-site" / "retainer-runs" / "2026-06.json"
    assert json.loads(path.read_text(encoding="utf-8"))["product_id"] == "joes-plumbing-site"
