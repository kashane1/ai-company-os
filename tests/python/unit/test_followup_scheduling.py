"""F2: the first sends must get follow-ups, on BOTH logging paths, and a backfill
repairs rows that predate the sequencer. These are the contracts the 2026-06-12
desync (sent rows with empty next_touch_at) can never recur against.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from packages.agency import outreach_actions as actions
from packages.agency.outreach import bbw_ref_token
from packages.agency.outreach_lane import (
    OutreachClientRow,
    OutreachLaneStatus,
    log_manual_touch,
    refresh_client_status,
    write_client_status,
)
from packages.agency.outreach_store import OutreachStore

_spec = importlib.util.spec_from_file_location(
    "backfill_followups", Path("scripts/agency/backfill_followups.py")
)
backfill = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backfill)


def _record(place_id: str, name: str, **over: object) -> dict[str, object]:
    base = {
        "place_id": place_id,
        "display_name": name,
        "phone": "+15035550000",
        "city_id": "los_angeles",
        "genre_id": "auto_repair",
        "composite_cohort": "A_gold",
        "user_ratings_total": 40,
        "mockup_url": f"https://preview-{place_id}.example.test",
        "mockup_version": "v2-bespoke",
        "contact_email": f"{place_id}@example.com",
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
    return lane_root, OutreachStore(sqlite_path=tmp_path / "outreach.sqlite3")


def _row(lane_root: Path, place_id: str) -> OutreachClientRow:
    payload = json.loads((lane_root / "client-status.json").read_text())
    return next(
        OutreachClientRow.from_dict(r) for r in payload["rows"] if r["place_id"] == place_id
    )


# ---------------------------------------------------- both live logging paths
def test_dashboard_path_schedules_next_touch_and_records_token(tmp_path: Path) -> None:
    lane_root, store = _materialize(tmp_path, [_record("p1", "Joe Auto")])
    actions.record_touch("p1", "email", store=store, lane_root=lane_root)
    row = _row(lane_root, "p1")
    assert row.status is OutreachLaneStatus.SENT
    assert row.next_touch_at  # scheduled, not empty
    assert store.place_id_for_token(bbw_ref_token("p1")) == "p1"


def test_cli_path_schedules_next_touch_and_records_token(tmp_path: Path) -> None:
    lane_root, store = _materialize(tmp_path, [_record("p1", "Joe Auto")])
    log_manual_touch(
        "p1", channel="email", outcome="sent", lane_root=lane_root, store=store
    )
    row = _row(lane_root, "p1")
    assert row.status is OutreachLaneStatus.SENT
    assert row.next_touch_at
    assert store.place_id_for_token(bbw_ref_token("p1")) == "p1"


# ------------------------------------------------------------------ backfill
def _sent_row(place_id: str, *, status: str, next_touch_at: str = "") -> dict[str, object]:
    return {
        "place_id": place_id,
        "business_name": place_id,
        "status": status,
        "last_touch_at": "2026-06-12T05:00:00Z",
        "next_touch_at": next_touch_at,
        "recommended_channel": "email",
    }


def _write_ledger(lane_root: Path, rows: list[dict[str, object]]) -> None:
    lane_root.mkdir(parents=True, exist_ok=True)
    write_client_status([OutreachClientRow.from_dict(r) for r in rows], lane_root=lane_root)


def test_backfill_schedules_unscheduled_sent_rows_and_is_idempotent(tmp_path: Path) -> None:
    lane_root = tmp_path / "lane"
    store = OutreachStore(sqlite_path=tmp_path / "outreach.sqlite3")
    store.append_touch("p1", "email", sent_at="2026-06-12T05:00:00Z")
    _write_ledger(lane_root, [_sent_row("p1", status="sent")])

    found = backfill.run_backfill(lane_root=lane_root, store=store, apply=False)
    assert [r.place_id for r, _ in found] == ["p1"]
    assert found[0][1].startswith("2026-06-16")  # +4 days from the 06-12 send

    # dry-run wrote nothing
    assert _row(lane_root, "p1").next_touch_at == ""

    applied = backfill.run_backfill(lane_root=lane_root, store=store, apply=True)
    assert len(applied) == 1
    assert _row(lane_root, "p1").next_touch_at.startswith("2026-06-16")

    # idempotent: a second apply finds nothing to do
    assert backfill.run_backfill(lane_root=lane_root, store=store, apply=True) == []


def test_backfill_skips_terminal_and_already_scheduled(tmp_path: Path) -> None:
    lane_root = tmp_path / "lane"
    store = OutreachStore(sqlite_path=tmp_path / "outreach.sqlite3")
    for pid in ("dnc", "replied", "scheduled"):
        store.append_touch(pid, "email", sent_at="2026-06-12T05:00:00Z")
    _write_ledger(
        lane_root,
        [
            _sent_row("dnc", status="do_not_contact"),
            _sent_row("replied", status="replied"),
            _sent_row("scheduled", status="sent", next_touch_at="2026-06-20T00:00:00Z"),
        ],
    )
    assert backfill.run_backfill(lane_root=lane_root, store=store, apply=False) == []
