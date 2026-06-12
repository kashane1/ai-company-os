"""Funnel telemetry — counts measured from primary sources, stable output."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from packages.agency.funnel import (
    FunnelCooldownError,
    compute_funnel,
    cooldown_remaining_seconds,
    load_funnel_report_payload,
    refresh_funnel_report,
    render_funnel_markdown,
    write_funnel_report,
)
from packages.agency.outreach_store import OutreachStore
from packages.schemas.offer import (
    BillType,
    Bundle,
    Service,
    ServiceCatalog,
    ServiceTier,
)


def _catalog() -> ServiceCatalog:
    svc = Service(
        service_id="svc",
        name="Monthly Care",
        tier=ServiceTier.TIER_2,
        bill_type=BillType.RECURRING,
        monthly_fee=100.0,
    )
    catalog = ServiceCatalog(
        services={"svc": svc},
        bundles={"pkg": Bundle(bundle_id="pkg", name="Package", service_ids=["svc"])},
    )
    catalog.validate()
    return catalog


def _scaffold(root: Path) -> OutreachStore:
    """Build a synthetic state tree and return a store wired to its sqlite."""
    prospects = root / "state" / "prospects"
    records = prospects / "records"
    audited = prospects / "audited"
    sites = prospects / "sites"
    lane = prospects / "outreach-lane"
    billing = root / "state" / "agency" / "billing"
    for path in (records, audited, sites, lane, billing):
        path.mkdir(parents=True, exist_ok=True)

    # 4 collected; 2 carry a mockup_url (deployed).
    for i in range(4):
        rec = {
            "place_id": f"p{i}",
            "display_name": f"Biz {i}",
            "genre_id": "plumber",
            "city_id": "dallas",
        }
        if i < 2:
            rec["mockup_url"] = f"https://demo{i}.netlify.app"
        (records / f"p{i}.json").write_text(json.dumps(rec))

    # 3 audited verdicts; 2 are build targets (none_found, marketplace_only).
    (audited / "a.csv").write_text(
        "place_id,web_verify_verdict\n"
        "p0,none_found\n"
        "p1,marketplace_only\n"
        "p2,owned_site\n"
    )

    # 3 built sites (dist-v2/index.html present).
    for i in range(3):
        d = sites / f"p{i}" / "dist-v2"
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text("<html></html>")

    # Lane ledger summary: 1 replied, 1 won, 1 lost.
    (lane / "client-status.json").write_text(
        json.dumps(
            {
                "updated_at": "2026-06-12T00:00:00Z",
                "summary": {"total": 4, "replied": 1, "won": 1, "lost": 1},
                "rows": [
                    {"place_id": "p0", "status": "replied", "genre_id": "plumber", "city": "Dallas"}
                ],
            }
        )
    )

    # One ACTIVE billing ledger on the "pkg" bundle → $100 MRR.
    (billing / "client-a.json").write_text(
        json.dumps({"product_id": "client-a", "bundle": "pkg", "billing_status": "active"})
    )

    store = OutreachStore(sqlite_path=lane / "outreach.sqlite3")
    store.append_touch("p0", "email", variant="demo-link")
    store.append_touch("p1", "sms", variant="short")
    return store


def test_stage_counts_from_primary_sources(tmp_path: Path) -> None:
    store = _scaffold(tmp_path)
    report = compute_funnel(repo_root=tmp_path, store=store, catalog=_catalog())
    counts = report.stage_counts
    assert counts["collected"] == 4
    assert counts["audited"] == 3
    assert counts["built"] == 3
    assert counts["deployed"] == 2
    assert counts["sent"] == 2  # distinct place_ids touched
    assert counts["replied"] == 1
    assert counts["won"] == 1
    assert counts["active_clients"] == 1


def test_verdicts_and_targets(tmp_path: Path) -> None:
    store = _scaffold(tmp_path)
    report = compute_funnel(repo_root=tmp_path, store=store, catalog=_catalog())
    assert report.verdicts == {"marketplace_only": 1, "none_found": 1, "owned_site": 1}
    assert report.target_verdicts == 2  # none_found + marketplace_only


def test_mrr_priced_at_catalog(tmp_path: Path) -> None:
    store = _scaffold(tmp_path)
    report = compute_funnel(repo_root=tmp_path, store=store, catalog=_catalog())
    assert report.active_clients == 1
    assert report.mrr_cents == 10_000  # one $100/mo bundle


def test_sent_breakdown(tmp_path: Path) -> None:
    store = _scaffold(tmp_path)
    report = compute_funnel(repo_root=tmp_path, store=store, catalog=_catalog())
    assert report.sent_by_channel == {"email": 1, "sms": 1}
    assert report.sent_by_variant == {"demo-link": 1, "short": 1}


def test_conversion_rates(tmp_path: Path) -> None:
    store = _scaffold(tmp_path)
    report = compute_funnel(repo_root=tmp_path, store=store, catalog=_catalog())
    by_key = {stage.key: stage for stage in report.stages}
    assert by_key["collected"].conversion_pct is None  # first stage
    assert by_key["audited"].conversion_pct == 75.0  # 3 / 4
    assert by_key["deployed"].conversion_pct == round(2 / 3 * 100, 1)


def test_zero_data_callout_for_missing_sources(tmp_path: Path) -> None:
    # Empty state: every directory absent → all stages flagged.
    store = OutreachStore(sqlite_path=tmp_path / "outreach.sqlite3")
    report = compute_funnel(repo_root=tmp_path, store=store, catalog=_catalog())
    assert any("Active clients" in z for z in report.zero_data)
    assert any("Collected" in z for z in report.zero_data)
    active_stage = next(s for s in report.stages if s.key == "active_clients")
    assert active_stage.available is False


def test_deltas_vs_previous_run(tmp_path: Path) -> None:
    store = _scaffold(tmp_path)
    first = compute_funnel(repo_root=tmp_path, store=store, catalog=_catalog())
    # Add a new collected + deployed record, then recompute with the prior payload.
    rec = {"place_id": "p9", "display_name": "Biz 9", "mockup_url": "https://demo9.netlify.app"}
    (tmp_path / "state" / "prospects" / "records" / "p9.json").write_text(json.dumps(rec))
    second = compute_funnel(
        repo_root=tmp_path, store=store, catalog=_catalog(), previous=first.to_dict()
    )
    by_key = {stage.key: stage for stage in second.stages}
    assert by_key["collected"].delta == 1
    assert by_key["deployed"].delta == 1
    assert by_key["audited"].delta == 0


def test_breakdown_by_vertical(tmp_path: Path) -> None:
    store = _scaffold(tmp_path)
    report = compute_funnel(repo_root=tmp_path, store=store, catalog=_catalog(), by="vertical")
    assert report.by == "vertical"
    # Both touched prospects are plumbers.
    assert report.breakdown["sent"] == {"plumber": 2}
    assert report.breakdown["replied"] == {"plumber": 1}


def test_write_and_reload_is_stable(tmp_path: Path) -> None:
    store = _scaffold(tmp_path)
    report = compute_funnel(repo_root=tmp_path, store=store, catalog=_catalog())
    report_root = tmp_path / "state" / "prospects"
    json_path, md_path = write_funnel_report(report, report_root=report_root)
    assert json_path.exists() and md_path.exists()

    # Same report renders byte-identical markdown (committed-format-stable).
    assert render_funnel_markdown(report) == md_path.read_text()
    # The snapshot the dashboard reads round-trips.
    payload = load_funnel_report_payload(tmp_path)
    assert payload is not None
    assert payload["stage_counts"]["built"] == 3
    assert payload["mrr"]["mrr_usd"] == 100.0


def test_missing_report_returns_none(tmp_path: Path) -> None:
    assert load_funnel_report_payload(tmp_path) is None


def test_cooldown_remaining_seconds() -> None:
    now = datetime(2026, 6, 12, 12, 0, 0, tzinfo=UTC)
    assert cooldown_remaining_seconds(None, now=now) == 0  # never run → allowed
    fresh = {"updated_at": "2026-06-12T11:59:00Z"}  # 60s ago
    assert cooldown_remaining_seconds(fresh, cooldown_seconds=120, now=now) == 60
    stale = {"updated_at": "2026-06-12T11:00:00Z"}  # an hour ago
    assert cooldown_remaining_seconds(stale, cooldown_seconds=120, now=now) == 0
    garbage = {"updated_at": "not-a-date"}
    assert cooldown_remaining_seconds(garbage, now=now) == 0


def test_refresh_enforces_cooldown(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    first = refresh_funnel_report(repo_root=tmp_path)  # no prior report → allowed
    assert first["stage_counts"]["built"] == 3

    with pytest.raises(FunnelCooldownError) as excinfo:
        refresh_funnel_report(repo_root=tmp_path)  # back-to-back → blocked
    assert excinfo.value.remaining_seconds > 0

    # A zero cooldown (e.g. the scheduled job's effective behavior) bypasses it.
    again = refresh_funnel_report(repo_root=tmp_path, cooldown_seconds=0)
    assert again["stage_counts"]["collected"] == 4


def test_inbound_reply_touch_does_not_inflate_sent(tmp_path: Path) -> None:
    store = _scaffold(tmp_path)
    # A reply-sync inbound touch on a brand-new place_id must not count as a send.
    store.append_touch("p9", "email", via="reply_sync", direction="inbound")

    report = compute_funnel(repo_root=tmp_path, store=store, catalog=_catalog())
    assert report.stage_counts["sent"] == 2  # still the two outbound sends
    # by_channel counts distinct outbound prospects per channel — the inbound
    # email reply does not bump it.
    assert report.sent_by_channel.get("email") == 1
