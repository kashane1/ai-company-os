from __future__ import annotations

import json
from pathlib import Path

from packages.agency import outreach_actions as actions
from packages.agency.outreach_lane import refresh_client_status
from packages.agency.outreach_store import OutreachStore


def _record(place_id: str, name: str, **over: object) -> dict[str, object]:
    base = {
        "place_id": place_id,
        "display_name": name,
        "phone": "",
        "city_id": "los_angeles",
        "genre_id": "auto_repair",
        "composite_cohort": "A_gold",
        "user_ratings_total": 40,
        "mockup_url": f"https://preview-{place_id}.example.test",
        "mockup_version": "v2-bespoke",
    }
    base.update(over)
    return base


def _materialize(tmp_path: Path, records: list[dict[str, object]]) -> tuple[Path, OutreachStore]:
    records_root = tmp_path / "records"
    lane_root = tmp_path / "lane"
    records_root.mkdir()
    for record in records:
        (records_root / f"{record['place_id']}.json").write_text(json.dumps(record))
    refresh_client_status(records_root=records_root, lane_root=lane_root)
    store = OutreachStore(sqlite_path=tmp_path / "outreach.sqlite3")
    return lane_root, store


def _buttons(view, place_id: str) -> dict[str, object]:
    row = next(r for r in view.rows if r.place_id == place_id)
    return {b.channel: b for b in row.buttons}


def test_panel_enables_buttons_only_when_contact_present(tmp_path: Path) -> None:
    lane_root, store = _materialize(
        tmp_path,
        [_record("p1", "Joe Auto", phone="+15035550000", contact_email="")],
    )
    view = actions.build_outreach_panel(store=store, lane_root=lane_root)
    buttons = _buttons(view, "p1")

    assert buttons["email"].enabled is False  # no email
    assert buttons["sms"].enabled is True  # phone present
    assert buttons["call"].enabled is True
    assert buttons["facebook_dm"].enabled is False
    assert buttons["sms"].url.startswith("sms:+15035550000")


def test_set_contact_enables_email_button(tmp_path: Path) -> None:
    lane_root, store = _materialize(tmp_path, [_record("p1", "Joe Auto")])
    assert _buttons(actions.build_outreach_panel(store=store, lane_root=lane_root), "p1")[
        "email"
    ].enabled is False

    actions.set_contact("p1", "contact_email", "joe@example.com", store=store)

    email = _buttons(actions.build_outreach_panel(store=store, lane_root=lane_root), "p1")["email"]
    assert email.enabled is True
    assert "joe%40example.com" in email.url


def test_record_touch_logs_and_bumps_status(tmp_path: Path) -> None:
    lane_root, store = _materialize(tmp_path, [_record("p1", "Joe Auto")])

    result = actions.record_touch("p1", "email", store=store, lane_root=lane_root)
    assert result["status"] == "sent"  # READY_TO_SEND -> SENT on first touch

    actions.record_touch("p1", "email", store=store, lane_root=lane_root)
    view = actions.build_outreach_panel(store=store, lane_root=lane_root)
    assert [row.place_id for row in view.rows] == ["p1"]
    assert _buttons(view, "p1")["email"].sent_count == 2


def test_panel_rows_include_filter_facts_and_facet_counts(tmp_path: Path) -> None:
    lane_root, store = _materialize(
        tmp_path,
        [
            _record("p1", "Joe Auto", contact_email="joe@example.com"),
            _record("p2", "Mia Mobile", phone="+15035550000", contact_email=""),
        ],
    )
    actions.record_touch("p1", "email", store=store, lane_root=lane_root)

    view = actions.build_outreach_panel(store=store, lane_root=lane_root)
    p1 = next(row for row in view.rows if row.place_id == "p1")
    p2 = next(row for row in view.rows if row.place_id == "p2")

    assert "preview" in p1.facts.tags
    assert "email-present" in p1.facts.tags
    assert "email-sent-once" in p1.facts.tags
    assert "preview-email-sent-once" in p1.facts.tags
    assert p1.facts.total_sent_count == 1

    assert "phone-present" in p2.facts.tags
    assert "no-sends" in p2.facts.tags
    assert "email-not-sent" in p2.facts.tags
    assert "preview-email-unsent" in p2.facts.tags

    counts = {facet.key: facet.count for facet in view.facets}
    assert counts["preview"] == 2
    assert counts["email-present"] == 1
    assert counts["no-sends"] == 1
    assert counts["preview-email-sent-once"] == 1


def test_set_status_persists_manual_choice(tmp_path: Path) -> None:
    lane_root, store = _materialize(tmp_path, [_record("p1", "Joe Auto")])
    actions.set_status("p1", "replied", lane_root=lane_root)
    view = actions.build_outreach_panel(store=store, lane_root=lane_root)
    row = next(r for r in view.rows if r.place_id == "p1")
    assert row.status == "replied"


def test_touch_does_not_downgrade_manual_status(tmp_path: Path) -> None:
    lane_root, store = _materialize(tmp_path, [_record("p1", "Joe Auto")])
    actions.set_status("p1", "won", lane_root=lane_root)
    result = actions.record_touch("p1", "email", store=store, lane_root=lane_root)
    assert result["status"] == "won"  # past-SENT status preserved
