"""F3: every outbound email touch must carry a reply-sync ref token, enforced at
the store layer so no logging path (dashboard, CLI, legacy import, future) can
skip it. Without a token, item 5's token-first reply matching can't resolve a
reply to its prospect.
"""

from __future__ import annotations

from pathlib import Path

from packages.agency.outreach import bbw_ref_token
from packages.agency.outreach_store import OutreachStore


def _store(tmp_path: Path) -> OutreachStore:
    return OutreachStore(sqlite_path=tmp_path / "outreach.sqlite3")


def _emails_without_token(store: OutreachStore) -> list[str]:
    """The invariant probe: outbound email touches with no ref_tokens row."""
    with store.connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT t.place_id FROM outreach_touches t "
            "LEFT JOIN outreach_ref_tokens r ON r.place_id = t.place_id "
            "WHERE t.channel = 'email' AND t.direction = 'outbound' AND r.place_id IS NULL"
        )
        return [str(OutreachStore._row_to_dict(row)["place_id"]) for row in cur.fetchall()]


def test_email_touch_records_token_in_same_transaction(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.append_touch("p1", "email")
    assert store.place_id_for_token(bbw_ref_token("p1")) == "p1"
    assert _emails_without_token(store) == []


def test_non_email_touch_records_no_token(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.append_touch("p1", "sms")
    assert store.place_id_for_token(bbw_ref_token("p1")) is None


def test_inbound_email_does_not_record_token(tmp_path: Path) -> None:
    # An inbound reply is not a send; it must not mint a send-token.
    store = _store(tmp_path)
    store.append_touch("p1", "email", direction="inbound")
    assert store.place_id_for_token(bbw_ref_token("p1")) is None


def test_invariant_holds_across_every_email_path(tmp_path: Path) -> None:
    store = _store(tmp_path)
    # legacy import path also goes through append_touch
    store.append_touch("a", "email", via="legacy_jsonl")
    store.append_touch("b", "email", via="cli")
    store.append_touch("c", "email", via="dashboard")
    store.append_touch("d", "sms")  # not email -> no token, not a violation
    assert _emails_without_token(store) == []
