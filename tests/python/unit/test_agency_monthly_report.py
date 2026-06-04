import json

from packages.agency.monthly_report import MonthlyMetrics, render_monthly_report, write_monthly_report


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
