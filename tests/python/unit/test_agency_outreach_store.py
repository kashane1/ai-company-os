from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from packages.agency.outreach_store import (
    DEFAULT_VARIANT,
    SUPPRESSIONS_TABLE,
    TOUCHES_TABLE,
    OutreachStore,
)


def _store(tmp_path: Path) -> OutreachStore:
    return OutreachStore(sqlite_path=tmp_path / "outreach.sqlite3")


def test_append_and_summarize_touches(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.append_touch("p1", "email", sent_at="2026-06-01T00:00:00Z")
    store.append_touch("p1", "email", sent_at="2026-06-03T00:00:00Z")
    store.append_touch("p1", "sms", sent_at="2026-06-02T00:00:00Z")

    touches = store.list_touches("p1")
    assert [t["channel"] for t in touches] == ["email", "sms", "email"]

    summary = store.touch_summary()
    assert summary["p1"]["email"] == {"count": 2, "last_sent_at": "2026-06-03T00:00:00Z"}
    assert summary["p1"]["sms"]["count"] == 1


def test_append_touch_rejects_unknown_channel(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.append_touch("p1", "carrier_pigeon")


def test_override_upserts_and_reads(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.set_override("p1", "contact_email", "a@example.com")
    store.set_override("p1", "contact_email", "b@example.com")  # overwrite
    store.set_override("p1", "phone", "+15035551234")

    assert store.get_overrides("p1") == {
        "contact_email": "b@example.com",
        "phone": "+15035551234",
    }
    assert store.all_overrides()["p1"]["contact_email"] == "b@example.com"


def test_override_rejects_unknown_field(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.set_override("p1", "ssn", "nope")


def test_import_legacy_jsonl_normalizes_channels(tmp_path: Path) -> None:
    legacy = tmp_path / "touches.jsonl"
    legacy.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {"place_id": "p1", "channel": "instagram", "occurred_at": "2026-05-01T00:00:00Z"},
                {"place_id": "p1", "channel": "phone", "occurred_at": "2026-05-02T00:00:00Z"},
                {"place_id": "", "channel": "email"},  # skipped: no place_id
                {"channel": "email"},  # skipped: no place_id
            ]
        )
        + "\n"
    )
    store = _store(tmp_path)
    imported = store.import_legacy_jsonl(legacy)
    assert imported == 2
    summary = store.touch_summary()
    assert "instagram_dm" in summary["p1"]
    assert "call" in summary["p1"]


def test_import_legacy_jsonl_missing_file_is_noop(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.import_legacy_jsonl(tmp_path / "absent.jsonl") == 0


def test_touch_records_variant_and_defaults(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.append_touch("p1", "email", variant="social-proof")
    store.append_touch("p1", "email")  # default
    store.append_touch("p1", "sms", variant="   ")  # blank -> default

    variants = [t["variant"] for t in store.list_touches("p1")]
    assert variants == ["social-proof", DEFAULT_VARIANT, DEFAULT_VARIANT]


def test_variant_column_added_to_legacy_db(tmp_path: Path) -> None:
    # A DB created before the variant column existed: build the old shape by hand,
    # then let ensure_schema migrate it additively.
    db_path = tmp_path / "outreach.sqlite3"
    conn = sqlite3.connect(db_path)
    conn.execute(
        f"CREATE TABLE {TOUCHES_TABLE} (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "place_id TEXT NOT NULL, channel TEXT NOT NULL, sent_at TEXT NOT NULL, "
        "via TEXT NOT NULL, note TEXT NOT NULL DEFAULT '')"
    )
    conn.execute(
        f"INSERT INTO {TOUCHES_TABLE} (place_id, channel, sent_at, via, note) "
        "VALUES ('p1', 'email', '2026-06-01T00:00:00Z', 'legacy', '')"
    )
    conn.commit()
    conn.close()

    store = OutreachStore(sqlite_path=db_path)
    rows = store.list_touches("p1")
    assert rows[0]["variant"] == DEFAULT_VARIANT  # backfilled by the migration
    store.append_touch("p1", "sms", variant="short")
    assert store.list_touches("p1")[1]["variant"] == "short"


def test_suppression_upsert_lookup_and_keys(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.suppress_key("place:p1", "place_id", "bounced", "operator")
    # Re-suppressing the same key keeps the original reason/source (DO NOTHING).
    store.suppress_key("place:p1", "place_id", "changed mind", "disqualified")
    store.suppress_key("email:a@x.com", "email", "unsubscribed", "reply_stop")

    assert store.is_key_suppressed("place:p1") is True
    assert store.is_key_suppressed("place:absent") is False
    assert store.suppressed_keys() == {"place:p1", "email:a@x.com"}

    entries = {e["key"]: e for e in store.list_suppressions()}
    assert entries["place:p1"]["reason"] == "bounced"  # first write wins
    assert entries["email:a@x.com"]["source"] == "reply_stop"


def test_inbound_touch_excluded_from_sent_counts(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.append_touch("p1", "email", variant="demo-link")  # outbound send
    store.append_touch("p1", "email", via="reply_sync", direction="inbound")  # a reply

    # touch_summary is the "sent" view — the inbound reply must not show up.
    summary = store.touch_summary()
    assert summary["p1"]["email"]["count"] == 1
    # variant_counts feeds the A/B arm tally — outbound only.
    assert store.variant_counts() == {"demo-link": 1}
    # But the full per-prospect history shows both directions.
    directions = [t["direction"] for t in store.list_touches("p1")]
    assert directions == ["outbound", "inbound"]


def test_append_touch_rejects_unknown_direction(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.append_touch("p1", "email", direction="sideways")


def test_direction_column_added_to_legacy_db(tmp_path: Path) -> None:
    # A DB predating the direction column: build the old shape (with variant but
    # no direction), then let ensure_schema migrate it additively.
    db_path = tmp_path / "outreach.sqlite3"
    conn = sqlite3.connect(db_path)
    conn.execute(
        f"CREATE TABLE {TOUCHES_TABLE} (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "place_id TEXT NOT NULL, channel TEXT NOT NULL, sent_at TEXT NOT NULL, "
        "via TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', "
        f"variant TEXT NOT NULL DEFAULT '{DEFAULT_VARIANT}')"
    )
    conn.execute(
        f"INSERT INTO {TOUCHES_TABLE} (place_id, channel, sent_at, via, note, variant) "
        "VALUES ('p1', 'email', '2026-06-01T00:00:00Z', 'legacy', '', 'demo-link')"
    )
    conn.commit()
    conn.close()

    store = OutreachStore(sqlite_path=db_path)
    # Pre-existing rows backfill to outbound, so the legacy send still counts.
    assert store.list_touches("p1")[0]["direction"] == "outbound"
    assert store.touch_summary()["p1"]["email"]["count"] == 1


def test_ref_token_record_and_lookup(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.place_id_for_token("BBW-ABC234") is None
    store.record_ref_token("BBW-ABC234", "p1")
    assert store.place_id_for_token("BBW-ABC234") == "p1"
    # Idempotent: re-recording the deterministic token keeps the first mapping.
    store.record_ref_token("BBW-ABC234", "p1")
    assert store.place_id_for_token("BBW-ABC234") == "p1"
