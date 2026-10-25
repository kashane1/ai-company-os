"""Alert-email reader: parsing, the generic Pokémon filter, cursor, and episodes."""

from __future__ import annotations

import datetime as dt
import json

from radar import episodes, watchlist
from radar.inbox import message, reader

from .conftest import FIXTURES, NOW

WATCH = watchlist.load()
SET_KEYS = ["30th celebration", "prismatic evolutions", "ascended heroes"]


def raw(name: str) -> bytes:
    return (FIXTURES / "email" / name).read_bytes()


def test_parses_headers_and_html_body_as_plain_text():
    alert = message.parse_email(raw("synthetic_nowinstock.eml"))
    assert alert.sender_domain == "nowinstock.net"
    assert alert.subject.startswith("In Stock Alert: 30th Celebration")
    assert alert.message_id == "<synthetic-nis-1@nowinstock.net>"
    assert alert.sent_at == "2026-09-25T08:51:40+00:00"
    assert "is now In Stock" in alert.body
    assert "alert('ignored')" not in alert.body  # scripts are dropped, never run
    assert alert.links[0] == "https://nowinstock.net/getw99999/"


def test_generic_filter_keeps_pokemon_mail_and_known_alert_senders():
    assert message.is_relevant(message.parse_email(raw("synthetic_nowinstock.eml")))
    assert message.is_relevant(message.parse_email(raw("synthetic_keepa.eml")))
    assert not message.is_relevant(message.parse_email(raw("unrelated.eml")))


def test_classifies_an_email_into_an_observation_shape():
    parsed = message.classify(message.parse_email(raw("synthetic_nowinstock.eml")), set_keys=SET_KEYS)
    assert (parsed.signal, parsed.retailer, parsed.is_tcg) == ("in_stock", "Target", True)
    assert parsed.url == "https://nowinstock.net/getw99999/"

    keepa = message.classify(message.parse_email(raw("synthetic_keepa.eml")), set_keys=SET_KEYS)
    assert (keepa.retailer, keepa.price) == ("Amazon", 34.99)


class FakeMailbox:
    def __init__(self, messages: dict[int, bytes], uidvalidity: int = 7) -> None:
        self.messages = messages
        self.uidvalidity = uidvalidity
        self.searches: list[tuple[int | None, dt.date | None]] = []

    def search(self, *, after_uid: int | None, since: dt.date | None) -> list[int]:
        self.searches.append((after_uid, since))
        return sorted(uid for uid in self.messages if after_uid is None or uid > after_uid)

    def fetch(self, uid: int) -> bytes:
        return self.messages[uid]


def observations(connection) -> list:
    return connection.execute("SELECT * FROM observations WHERE source_id = 'email' ORDER BY id").fetchall()


def test_poll_stores_relevant_mail_and_advances_the_uid_cursor(connection):
    mailbox = FakeMailbox({10: raw("synthetic_nowinstock.eml"), 11: raw("unrelated.eml"), 12: raw("synthetic_keepa.eml")})
    new_ids = reader.poll(connection, mailbox, watch=WATCH, now=NOW, set_keys=SET_KEYS)

    rows = observations(connection)
    assert len(new_ids) == 2 and len(rows) == 2
    assert rows[0]["author"] == "nowinstock.net"
    assert json.loads(rows[0]["watch_matches"]) == ["30th Celebration Elite Trainer Box"]
    assert json.loads(rows[1]["watch_matches"]) == ["Prismatic Evolutions Booster Bundle"]
    assert reader.load_cursor(connection) == (7, 12)
    # The first poll looks back a fixed window; later polls ask only for newer UIDs.
    assert mailbox.searches[0][0] is None and mailbox.searches[0][1] == NOW.date() - reader.FIRST_POLL_LOOKBACK

    reader.poll(connection, mailbox, watch=WATCH, now=NOW + dt.timedelta(minutes=1), set_keys=SET_KEYS)
    assert mailbox.searches[1] == (12, None)
    assert len(observations(connection)) == 2


def test_a_changed_uidvalidity_resets_the_cursor(connection):
    reader.poll(connection, FakeMailbox({5: raw("synthetic_keepa.eml")}), watch=WATCH, now=NOW, set_keys=SET_KEYS)
    reset = FakeMailbox({1: raw("synthetic_nowinstock.eml")}, uidvalidity=8)
    reader.poll(connection, reset, watch=WATCH, now=NOW, set_keys=SET_KEYS)
    assert reset.searches[0][0] is None
    assert reader.load_cursor(connection) == (8, 1)


def test_the_same_message_is_stored_once_even_after_a_reset(connection):
    reader.poll(connection, FakeMailbox({5: raw("synthetic_keepa.eml")}), watch=WATCH, now=NOW, set_keys=SET_KEYS)
    reader.poll(connection, FakeMailbox({1: raw("synthetic_keepa.eml")}, uidvalidity=9), watch=WATCH, now=NOW, set_keys=SET_KEYS)
    assert len(observations(connection)) == 1


def test_emails_are_scored_per_sender(connection):
    [observation_id] = reader.poll(
        connection, FakeMailbox({10: raw("synthetic_nowinstock.eml")}), watch=WATCH, now=NOW, set_keys=SET_KEYS
    )
    episodes.assign(connection, observation_id)
    card = {row.source_id for row in episodes.scorecard(connection)}
    assert card == {"email:nowinstock.net"}


def test_imap_connection_verifies_gmails_certificate(monkeypatch):
    """imaplib's default SSL context does not verify certificates; ours must."""
    import ssl

    captured = {}

    class FakeIMAP:
        def __init__(self, host, **kwargs):
            captured.update(host=host, **kwargs)
            raise ConnectionAbortedError("stop before any network use")

    monkeypatch.setattr(reader.imaplib, "IMAP4_SSL", FakeIMAP)
    try:
        reader.ImapMailbox("radar@example.test", "not-a-real-password")
    except ConnectionAbortedError:
        pass
    context = captured["ssl_context"]
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_fixtures_do_not_contain_the_real_inbox_address():
    for path in (FIXTURES / "email").glob("*.eml"):
        assert "@gmail.com" not in path.read_text(), path.name
