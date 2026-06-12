"""Follow-up sequencer (item 6): per-step cadence, max-3 stop, honest observation."""

from __future__ import annotations

import json
from pathlib import Path

from packages.agency import outreach_actions as actions
from packages.agency import outreach_sequencer as seq
from packages.agency.outreach import context_for
from packages.agency.outreach_lane import refresh_client_status
from packages.agency.outreach_store import OutreachStore


# --------------------------------------------------------------- cadence math
def test_schedule_next_touch_is_per_step() -> None:
    # count = sends so far (this one included): touch 1 -> +4d, touch 2 -> +8d.
    assert seq.schedule_next_touch(1, "2026-06-10T00:00:00Z") == "2026-06-14T00:00:00Z"
    assert seq.schedule_next_touch(2, "2026-06-10T00:00:00Z") == "2026-06-18T00:00:00Z"


def test_schedule_stops_after_three_touches() -> None:
    assert seq.schedule_next_touch(3, "2026-06-10T00:00:00Z") == ""
    assert seq.schedule_next_touch(4, "2026-06-10T00:00:00Z") == ""


def test_next_step_for_caps_at_max() -> None:
    assert seq.next_step_for(0) == 1
    assert seq.next_step_for(1) == 2
    assert seq.next_step_for(2) == 3
    assert seq.next_step_for(5) == 3  # finished sequence still resolves to step-3 copy


# --------------------------------------------------------- observation sourcing
def _write_brief(sites_root: Path, place_id: str, facts: list[str]) -> None:
    body = ["# Content Brief", "", "## What's true about the work"]
    body += [f"- {fact}" for fact in facts]
    body += ["", "## Guardrails", "- do not claim cheapest"]
    path = sites_root / place_id / "02-content-brief.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def _ctx(place_id: str = "p1"):
    return context_for(
        {
            "place_id": place_id,
            "display_name": "Joe Auto",
            "genre_id": "auto_repair",
            "user_ratings_total": 40,
            "mockup_url": "https://preview.example.test",
        },
        {},
    )


def test_brief_observations_strips_citation_and_placeholders(tmp_path: Path) -> None:
    _write_brief(
        tmp_path,
        "p1",
        [
            "same-day brake repairs — *source: review*",
            "<service/specialty> — *source: photo*",  # template placeholder, skipped
            "free loaner cars (source: website)",
        ],
    )
    facts = seq.brief_observations("p1", sites_root=tmp_path)
    assert facts == ["same-day brake repairs", "free loaner cars"]


def test_observation_rotates_brief_facts_per_step(tmp_path: Path) -> None:
    _write_brief(tmp_path, "p1", ["same-day brake repairs", "ASE certified techs"])
    ctx = _ctx()
    touch2 = seq.observation_for_step("p1", 2, ctx, sites_root=tmp_path)
    touch3 = seq.observation_for_step("p1", 3, ctx, sites_root=tmp_path)
    assert "same-day brake repairs" in touch2
    assert "ASE certified techs" in touch3
    assert touch2 != touch3
    assert "—" not in touch2  # copy rule: no em dash


def test_observation_falls_back_to_gap_when_brief_thin(tmp_path: Path) -> None:
    # No brief written: must still produce a (non-fabricated) gap re-pitch.
    ctx = _ctx()
    obs = seq.observation_for_step("p1", 2, ctx, sites_root=tmp_path)
    assert obs  # non-empty
    assert "—" not in obs


def test_first_touch_has_no_extra_observation(tmp_path: Path) -> None:
    assert seq.observation_for_step("p1", 1, _ctx(), sites_root=tmp_path) == ""


# ------------------------------------------------------- end-to-end via the lane
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
        "contact_email": "joe@example.com",
    }
    base.update(over)
    return base


def _materialize(tmp_path: Path) -> tuple[Path, OutreachStore]:
    records_root = tmp_path / "records"
    lane_root = tmp_path / "prospects" / "outreach-lane"
    records_root.mkdir()
    (records_root / "p1.json").write_text(json.dumps(_record("p1", "Joe Auto")))
    refresh_client_status(records_root=records_root, lane_root=lane_root)
    return lane_root, OutreachStore(sqlite_path=tmp_path / "outreach.sqlite3")


def _next_touch_at(lane_root: Path, place_id: str) -> str:
    payload = json.loads((lane_root / "client-status.json").read_text())
    row = next(r for r in payload["rows"] if r["place_id"] == place_id)
    return row["next_touch_at"]


def test_record_touch_schedules_per_step_then_stops(tmp_path: Path) -> None:
    lane_root, store = _materialize(tmp_path)

    actions.record_touch("p1", "email", store=store, lane_root=lane_root)
    after1 = _next_touch_at(lane_root, "p1")
    assert after1  # touch 2 is scheduled

    actions.record_touch("p1", "email", store=store, lane_root=lane_root)
    after2 = _next_touch_at(lane_root, "p1")
    assert after2 > after1  # touch 3 pushed further out (+8 vs +4)

    actions.record_touch("p1", "email", store=store, lane_root=lane_root)
    assert _next_touch_at(lane_root, "p1") == ""  # max 3 enforced: no touch 4


def test_due_followup_surfaces_step_two_copy(tmp_path: Path) -> None:
    lane_root, store = _materialize(tmp_path)
    sites_root = tmp_path / "prospects" / "sites"
    _write_brief(sites_root, "p1", ["same-day brake repairs"])

    # Touch-1 copy (before any send): the original preview pitch.
    view0 = actions.build_outreach_panel(store=store, lane_root=lane_root)
    email0 = next(b for b in view0.rows[0].buttons if b.channel == "email").copy

    actions.record_touch("p1", "email", store=store, lane_root=lane_root)

    view1 = actions.build_outreach_panel(store=store, lane_root=lane_root)
    email1 = next(b for b in view1.rows[0].buttons if b.channel == "email").copy
    assert email1 != email0
    assert "follow up" in email1.lower()
    assert "same-day brake repairs" in email1  # honest observation from the brief
    assert 'no thanks' in email1.lower()  # opt-out line preserved


def test_reply_cancels_pending_followup(tmp_path: Path) -> None:
    lane_root, store = _materialize(tmp_path)
    actions.record_touch("p1", "email", store=store, lane_root=lane_root)
    assert _next_touch_at(lane_root, "p1")  # scheduled

    actions.set_status("p1", "replied", lane_root=lane_root)
    assert _next_touch_at(lane_root, "p1") == ""  # reply clears the follow-up
