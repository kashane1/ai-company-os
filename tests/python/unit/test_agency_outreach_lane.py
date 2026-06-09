from __future__ import annotations

import json
from pathlib import Path

from packages.agency.outreach_lane import (
    OutreachLaneStatus,
    build_client_rows,
    default_outreach_lane_root,
    log_manual_touch,
    refresh_client_status,
)


def _record(
    place_id: str,
    name: str,
    *,
    mockup_version: str = "",
    engagement_status: str = "none",
) -> dict[str, object]:
    return {
        "place_id": place_id,
        "display_name": name,
        "formatted_address": "123 Main St",
        "phone": "+1 555-0100",
        "types": ["bakery"],
        "city_id": "los_angeles",
        "genre_id": "bakery",
        "grid_cell_id": "los_angeles:bakery",
        "composite_cohort": "A_gold",
        "rating": 4.9,
        "user_ratings_total": 651,
        "mockup_url": f"https://preview-{place_id}.netlify.app",
        "mockup_version": mockup_version,
        "engagement_status": engagement_status,
    }


def test_build_client_rows_seeds_finished_as_ready_and_template_as_needs_bespoke() -> None:
    rows = build_client_rows(
        [
            _record("p1", "Finished Bakery", mockup_version="v2-bespoke"),
            _record("p2", "Template Bakery"),
            {**_record("p3", "Not A Gold"), "composite_cohort": "B"},
            {**_record("p4", "No URL"), "mockup_url": ""},
        ],
    )

    assert [row.place_id for row in rows] == ["p1", "p2"]
    assert rows[0].status == OutreachLaneStatus.READY_TO_SEND
    assert rows[0].next_action.startswith("Review draft")
    assert rows[1].status == OutreachLaneStatus.NEEDS_BESPOKE
    assert rows[1].next_action == "Rebuild bespoke demo before outreach"


def test_build_client_rows_blocks_owned_site_recheck_before_outreach() -> None:
    rows = build_client_rows(
        [
            {
                **_record("p1", "Finished Bakery", mockup_version="v2-bespoke"),
                "contact_owned_website": "https://example.com",
            }
        ],
    )

    assert rows[0].status == OutreachLaneStatus.BLOCKED
    assert rows[0].next_action == "Recheck owned-site signal before outreach"


def test_build_client_rows_preserves_operator_fields_on_refresh() -> None:
    existing = {
        "p1": {
            "place_id": "p1",
            "status": "sent",
            "manual_channel": "email",
            "next_follow_up_at": "2026-06-12",
            "last_touch_at": "2026-06-09T10:00:00",
            "notes": "Owner's daughter helps with site.",
        }
    }

    rows = build_client_rows(
        [_record("p1", "Finished Bakery", mockup_version="v2-bespoke")],
        existing_rows=existing,
    )

    assert rows[0].status == OutreachLaneStatus.SENT
    assert rows[0].manual_channel == "email"
    assert rows[0].next_follow_up_at == "2026-06-12"
    assert rows[0].notes == "Owner's daughter helps with site."


def test_refresh_writes_json_and_markdown_status_files(tmp_path: Path) -> None:
    records_root = tmp_path / "records"
    records_root.mkdir()
    (records_root / "p1.json").write_text(
        json.dumps(_record("p1", "Finished Bakery", mockup_version="v2-bespoke"))
    )
    (records_root / "p2.json").write_text(json.dumps(_record("p2", "Template Bakery")))
    lane_root = tmp_path / "outreach-lane"

    rows = refresh_client_status(records_root=records_root, lane_root=lane_root)

    assert len(rows) == 2
    status_json = json.loads((lane_root / "client-status.json").read_text())
    assert status_json["summary"]["total"] == 2
    assert status_json["summary"]["ready_to_send"] == 1
    markdown = (lane_root / "client-status.md").read_text()
    assert "Finished Bakery" in markdown
    assert "Template Bakery" in markdown
    assert "Human-gated" in markdown


def test_log_manual_touch_appends_jsonl_and_updates_status(tmp_path: Path) -> None:
    records_root = tmp_path / "records"
    records_root.mkdir()
    (records_root / "p1.json").write_text(
        json.dumps(_record("p1", "Finished Bakery", mockup_version="v2-bespoke"))
    )
    lane_root = tmp_path / "outreach-lane"
    refresh_client_status(records_root=records_root, lane_root=lane_root)

    updated = log_manual_touch(
        "p1",
        channel="email",
        outcome="sent",
        lane_root=lane_root,
        occurred_at="2026-06-09T12:00:00",
        next_follow_up_at="2026-06-12",
        notes="Sent manually from Gmail.",
    )

    assert updated.status == OutreachLaneStatus.SENT
    assert updated.manual_channel == "email"
    assert updated.next_follow_up_at == "2026-06-12"
    assert updated.last_touch_at == "2026-06-09T12:00:00"
    touches = (lane_root / "touches.jsonl").read_text().splitlines()
    assert len(touches) == 1
    assert json.loads(touches[0])["outcome"] == "sent"


def test_default_outreach_lane_root_lives_under_runtime_state() -> None:
    assert str(default_outreach_lane_root()).endswith("state/prospects/outreach-lane")
