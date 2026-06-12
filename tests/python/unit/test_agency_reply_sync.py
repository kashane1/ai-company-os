"""Reply-sync: matching, STOP detection, and the writes a matched reply makes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.agency import reply_sync as rs
from packages.agency import suppression
from packages.agency.outreach import bbw_ref_token
from packages.agency.outreach_lane import OutreachLaneStatus, set_row_status
from packages.agency.outreach_store import OutreachStore

PLACE_ID = "ChIJ_reply_test"


def _scaffold(tmp_path: Path) -> tuple[Path, OutreachStore, str]:
    """A lane root with one sent prospect + a recorded token. Returns
    (lane_root, store, token)."""
    lane = tmp_path
    (lane / "replies").mkdir(parents=True, exist_ok=True)
    status = {
        "rows": [
            {
                "place_id": PLACE_ID,
                "business_name": "Joe Auto",
                "city": "Austin",
                "genre_id": "auto_repair",
                "rating": 4.5,
                "review_count": 40,
                "mockup_url": "https://x.test/joe",
                "mockup_version": "v2",
                "recommended_channel": "email",
                "status": "sent",
                "contact_email": "joe@example.com",
            }
        ],
        "summary": {},
    }
    (lane / "client-status.json").write_text(json.dumps(status))
    store = OutreachStore(sqlite_path=lane / "outreach.sqlite3")
    token = bbw_ref_token(PLACE_ID)
    store.record_ref_token(token, PLACE_ID)
    return lane, store, token


def _reply(token: str, **overrides) -> rs.ParsedReply:
    base = dict(
        thread_id="t1",
        from_email="joe@example.com",
        subject="Re: preview",
        body=f"Looks great, let's talk. ref: {token}",
        received_at="2026-06-12T10:00:00Z",
    )
    base.update(overrides)
    return rs.ParsedReply(**base)


# ----------------------------------------------------------------- detection
def test_extract_ref_token_finds_token_in_subject_or_body() -> None:
    assert rs.extract_ref_token("hello", "footer ref: BBW-ABC234 bye") == "BBW-ABC234"
    assert rs.extract_ref_token("subj BBW-XY7Z45", "") == "BBW-XY7Z45"
    assert rs.extract_ref_token("no token here", "still none") is None


@pytest.mark.parametrize(
    "body",
    [
        "No thanks, not for us",  # the opt-out phrase the email advertises
        "Please UNSUBSCRIBE me",
        "remove me from this list",
        "do not contact us again",
        "not interested",
        "STOP",
    ],
)
def test_detect_stop_intent_true(body: str) -> None:
    assert rs.detect_stop_intent(body) is True


def test_detect_stop_intent_false_on_normal_reply() -> None:
    assert rs.detect_stop_intent("Yes this looks useful, can we chat?") is False


# ------------------------------------------------------------------- process
def test_process_reply_matches_by_token_and_advances_status(tmp_path: Path) -> None:
    lane, store, token = _scaffold(tmp_path)
    out = rs.process_reply(_reply(token), store=store, lane_root=lane)

    assert out.matched and out.matched_by == "token"
    assert out.status == "replied" and out.status_changed
    # Inbound touch logged, but it does not count as a send.
    assert "email" not in store.touch_summary().get(PLACE_ID, {})
    assert store.list_touches(PLACE_ID)[0]["direction"] == "inbound"
    # Operator snippet written, carrying the matched token.
    snippet = lane / "replies" / f"{PLACE_ID}.md"
    assert snippet.exists()
    assert token in snippet.read_text()


def test_process_reply_matches_by_sender_when_no_token(tmp_path: Path) -> None:
    lane, store, _token = _scaffold(tmp_path)
    reply = rs.ParsedReply(
        thread_id="t2",
        from_email="JOE@example.com",  # case-insensitive match
        subject="Re",
        body="sounds good",
    )
    out = rs.process_reply(reply, store=store, lane_root=lane)
    assert out.matched and out.matched_by == "sender" and out.place_id == PLACE_ID


def test_process_reply_stop_intent_suppresses(tmp_path: Path) -> None:
    lane, store, token = _scaffold(tmp_path)
    out = rs.process_reply(
        _reply(token, body=f"no thanks. ref: {token}"), store=store, lane_root=lane
    )
    assert out.suppressed
    assert suppression.is_suppressed(
        {"place_id": PLACE_ID, "contact_email": "joe@example.com"}, store=store
    )
    # The snippet flags it for operator confirmation rather than acting silently.
    snippet_text = (lane / "replies" / f"{PLACE_ID}.md").read_text().lower()
    assert "needs operator confirmation" in snippet_text


def test_process_reply_unmatched_mutates_nothing(tmp_path: Path) -> None:
    lane, store, _token = _scaffold(tmp_path)
    reply = rs.ParsedReply(
        thread_id="t3", from_email="stranger@nope.com", subject="hi", body="hello"
    )
    out = rs.process_reply(reply, store=store, lane_root=lane)

    assert not out.matched and out.place_id is None
    assert store.list_touches(PLACE_ID) == []
    assert not (lane / "replies" / f"{PLACE_ID}.md").exists()


def test_process_reply_never_downgrades_terminal_status(tmp_path: Path) -> None:
    lane, store, token = _scaffold(tmp_path)
    set_row_status(PLACE_ID, OutreachLaneStatus.WON, lane_root=lane)

    out = rs.process_reply(_reply(token, thread_id="t4"), store=store, lane_root=lane)
    assert out.matched
    assert out.status == "won" and not out.status_changed  # a won deal does not regress


def test_process_reply_is_safe_to_call_per_distinct_thread(tmp_path: Path) -> None:
    # The worker dedupes by thread id; distinct threads each log their own touch.
    lane, store, token = _scaffold(tmp_path)
    rs.process_reply(_reply(token, thread_id="t1"), store=store, lane_root=lane)
    rs.process_reply(_reply(token, thread_id="t5", received_at="2026-06-12T11:00:00Z"),
                     store=store, lane_root=lane)
    inbound = [t for t in store.list_touches(PLACE_ID) if t["direction"] == "inbound"]
    assert len(inbound) == 2
    # Both reply sections land in the snippet.
    assert (lane / "replies" / f"{PLACE_ID}.md").read_text().count("## ") == 2
