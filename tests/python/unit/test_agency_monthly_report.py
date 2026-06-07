import json

from packages.agency.monthly_report import (
    MonthlyMetrics,
    metrics_from_plausible,
    render_monthly_report,
    write_monthly_report,
)
from packages.agency.plausible import FORM_LEAD_GOAL


def _row(metrics, dimensions=None):
    return {"results": [{"dimensions": dimensions or [], "metrics": metrics}]}


class _FakeStats:
    """Routes the adapter's three query shapes to canned responses."""

    def __init__(self, *, traffic, goals, leads):
        self.traffic, self.goals, self.leads = traffic, goals, leads

    def query(self, body):
        if "dimensions" in body:
            return self.goals
        if "filters" in body:
            return self.leads
        return self.traffic


def test_monthly_report_uses_owner_friendly_metrics() -> None:
    report = render_monthly_report(
        MonthlyMetrics(
            product_id="joes-plumbing-site",
            month="2026-06",
            visits=120,
            form_leads=9,
            completed_work=["Published two service pages"],
            recommended_action="Add one coupon page.",
            billing_status="active",
        ),
        client_name="Joe's Plumbing",
    )

    assert "Website visits" in report
    assert "Form leads" in report
    assert "Not tracked yet" in report
    assert "Published two service pages" in report
    assert "Add one coupon page" in report


def test_write_monthly_report(tmp_path) -> None:
    path = write_monthly_report(
        tmp_path,
        MonthlyMetrics(product_id="joes-plumbing-site", month="2026-06"),
        client_name="Joe's Plumbing",
    )

    assert path == tmp_path / "reports" / "2026-06.md"
    assert "Joe's Plumbing" in path.read_text(encoding="utf-8")


def test_monthly_metrics_loads_from_dict() -> None:
    payload = json.loads(
        '{"product_id":"p","month":"2026-06","visits":3,"form_leads":2,"calls":1,"calls_tracked":true}'
    )
    metrics = MonthlyMetrics.from_dict(payload)
    assert metrics.calls == 1
    assert metrics.calls_tracked is True
    assert metrics.leads_tracked is True  # defaulted for legacy records


def test_metrics_from_plausible_pulls_real_numbers() -> None:
    client = _FakeStats(
        traffic=_row([342, 1187]),
        goals=_row([7], dimensions=[FORM_LEAD_GOAL]),
        leads=_row([7, 9]),
    )
    metrics = metrics_from_plausible(
        client,
        product_id="joes-plumbing-site",
        month="2026-05",
        site_id="joesplumbing.com",
        completed_work=["Published two service pages"],
    )
    assert metrics.visits == 342
    assert metrics.form_leads == 7
    assert metrics.leads_tracked is True
    assert metrics.completed_work == ["Published two service pages"]


def test_metrics_from_plausible_missing_goal_keeps_traffic_and_flags_leads() -> None:
    # No FORM_LEAD_GOAL present -> traffic still real, leads untracked, action set.
    client = _FakeStats(
        traffic=_row([342, 1187]),
        goals=_row([5], dimensions=["Some Other Goal"]),
        leads=_row([0]),
    )
    metrics = metrics_from_plausible(
        client,
        product_id="joes-plumbing-site",
        month="2026-05",
        site_id="joesplumbing.com",
    )
    assert metrics.visits == 342  # traffic survives a missing goal
    assert metrics.leads_tracked is False
    assert FORM_LEAD_GOAL in metrics.recommended_action

    report = render_monthly_report(metrics, client_name="Joe's Plumbing")
    # Leads render as "Not tracked yet", never a fake 0.
    assert "**Form leads:** Not tracked yet" in report
