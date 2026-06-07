"""Client-site lead-pipeline monitoring (hosting SLA)."""

from __future__ import annotations

from datetime import date

from packages.agency.lead_health import (
    LeadHealthStatus,
    assess_lead_health,
    load_leads_from_dir,
)


def _lead(received_at: str, *, delivered: bool = True) -> dict[str, object]:
    return {
        "submission_id": received_at,  # unique enough for tests
        "contact": "jane@example.com",
        "received_at": received_at,
        "notified_at": "2026-06-01T00:00:00Z" if delivered else None,
    }


def test_healthy_pipeline_is_ok() -> None:
    leads = [_lead("2026-06-01T10:00:00Z"), _lead("2026-06-04T09:00:00Z")]
    health = assess_lead_health(leads, product_id="joe", as_of=date(2026, 6, 7))
    assert health.status is LeadHealthStatus.OK
    assert health.leads_in_window == 2
    assert health.undelivered_in_window == 0
    assert health.days_since_last_lead == 3
    assert health.alerts == []


def test_undelivered_lead_is_alert() -> None:
    # The silent-failure case: lead captured, owner never emailed.
    leads = [_lead("2026-06-05T10:00:00Z", delivered=False)]
    health = assess_lead_health(leads, product_id="joe", as_of=date(2026, 6, 7))
    assert health.status is LeadHealthStatus.ALERT
    assert health.undelivered_in_window == 1
    assert any("never emailed" in a for a in health.alerts)


def test_unreachable_store_is_alert() -> None:
    health = assess_lead_health([], product_id="joe", as_of=date(2026, 6, 7), store_reachable=False)
    assert health.status is LeadHealthStatus.ALERT
    assert any("unreachable" in a for a in health.alerts)


def test_long_dry_spell_warns() -> None:
    leads = [_lead("2026-03-01T10:00:00Z")]  # > 45 days before as_of
    health = assess_lead_health(leads, product_id="joe", as_of=date(2026, 6, 7))
    assert health.status is LeadHealthStatus.WARN
    assert any("no leads in" in a for a in health.alerts)


def test_no_leads_yet_warns() -> None:
    health = assess_lead_health([], product_id="joe", as_of=date(2026, 6, 7))
    assert health.status is LeadHealthStatus.WARN
    assert any("no leads on record" in a for a in health.alerts)


def test_form_less_site_does_not_warn_on_no_leads() -> None:
    # Most SMBs don't depend on a lead form: a quiet store is fine, not a problem.
    health = assess_lead_health(
        [], product_id="joe", as_of=date(2026, 6, 7), lead_capture_expected=False
    )
    assert health.status is LeadHealthStatus.OK
    assert health.alerts == []


def test_form_less_site_still_alerts_on_undelivered() -> None:
    # The undelivered ALERT is universal: a captured-but-undelivered lead is always bad.
    leads = [_lead("2026-06-05T10:00:00Z", delivered=False)]
    health = assess_lead_health(
        leads, product_id="joe", as_of=date(2026, 6, 7), lead_capture_expected=False
    )
    assert health.status is LeadHealthStatus.ALERT
    assert any("never emailed" in a for a in health.alerts)


def test_funnel_record_delivered_via_status_field() -> None:
    # The agency's own review funnel marks delivery with status="notified".
    leads = [{"submission_id": "r1", "received_at": "2026-06-05T10:00:00Z", "status": "notified"}]
    health = assess_lead_health(leads, product_id="better-business-web", as_of=date(2026, 6, 7))
    assert health.undelivered_in_window == 0
    assert health.status is LeadHealthStatus.OK


def test_garbage_received_at_does_not_crash() -> None:
    leads = [{"submission_id": "x", "received_at": "not-a-date", "notified_at": "x"}]
    health = assess_lead_health(leads, product_id="joe", as_of=date(2026, 6, 7))
    # Unparseable date -> not counted in window, treated as "no dated leads".
    assert health.leads_in_window == 0
    assert health.status is LeadHealthStatus.WARN


def test_load_leads_from_dir(tmp_path) -> None:
    (tmp_path / "a.json").write_text('{"submission_id":"a","received_at":"2026-06-01T00:00:00Z"}')
    (tmp_path / "bad.json").write_text("{not json")
    leads = load_leads_from_dir(tmp_path)
    assert len(leads) == 1
    assert load_leads_from_dir(tmp_path / "missing") == []
