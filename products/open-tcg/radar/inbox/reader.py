"""Read the project inbox over IMAP, strictly read-only, and store alert emails.

The mailbox is opened with EXAMINE, so messages are never marked read,
moved, or deleted. A UID cursor (with the mailbox's UIDVALIDITY) makes each
poll ask only for newer mail; the first poll looks back a fixed window.
Messages are keyed by Message-ID, so a UIDVALIDITY reset cannot duplicate
them.
"""

from __future__ import annotations

import datetime as dt
import imaplib
import json
import re
import sqlite3
import time
import tomllib
from pathlib import Path
from typing import Callable, Iterable, Protocol

from .. import matching, sources
from ..config import DATA_DIR
from ..db import iso
from ..http import tls_context
from ..social.bluesky import catalog_set_keys
from ..watchlist import WatchItem
from . import message

SOURCE_ID = "email"
IMAP_HOST = "imap.gmail.com"
PASSWORD_PATH = DATA_DIR / "secrets" / "gmail-app-password"
CONFIG_PATH = DATA_DIR / "config.toml"
FIRST_POLL_LOOKBACK = dt.timedelta(days=14)
POLL_INTERVAL_S = 30
MAX_BACKOFF_S = 300
# Gmail's own search narrows the candidates; message.is_relevant re-checks locally.
GMAIL_QUERY = '"pokemon OR from:nowinstock.net OR from:keepa.com"'


class Mailbox(Protocol):
    uidvalidity: int

    def search(self, *, after_uid: int | None, since: dt.date | None) -> list[int]: ...
    def fetch(self, uid: int) -> bytes: ...


class ImapMailbox:
    """Gmail INBOX opened read-only (EXAMINE)."""

    def __init__(self, address: str, password: str) -> None:
        # imaplib's default context skips certificate checks; always pass a verifying one.
        self._imap = imaplib.IMAP4_SSL(IMAP_HOST, timeout=30, ssl_context=tls_context())
        self._imap.login(address, password)
        status, _ = self._imap.select("INBOX", readonly=True)
        if status != "OK":
            raise RuntimeError("could not open INBOX read-only")
        response = self._imap.response("UIDVALIDITY")[1]
        self.uidvalidity = int(response[0]) if response and response[0] else 0

    def search(self, *, after_uid: int | None, since: dt.date | None) -> list[int]:
        criteria = []
        if after_uid is not None:
            criteria += ["UID", f"{after_uid + 1}:*"]
        if since is not None:
            criteria += ["SINCE", since.strftime("%d-%b-%Y")]
        criteria += ["X-GM-RAW", GMAIL_QUERY]
        status, data = self._imap.uid("SEARCH", *criteria)
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {status}")
        uids = [int(uid) for uid in (data[0] or b"").split()]
        # "UID n:*" always includes the newest message, even when it is older than n.
        return sorted(uid for uid in uids if after_uid is None or uid > after_uid)

    def fetch(self, uid: int) -> bytes:
        # BODY.PEEK leaves the \Seen flag untouched.
        status, data = self._imap.uid("FETCH", str(uid), "(BODY.PEEK[])")
        if status != "OK" or not data or not isinstance(data[0], tuple):
            raise RuntimeError(f"IMAP fetch failed for UID {uid}")
        return data[0][1]

    def noop(self) -> None:
        self._imap.noop()

    def close(self) -> None:
        try:
            self._imap.logout()
        except (imaplib.IMAP4.error, OSError):
            pass


def credentials(config_path: Path = CONFIG_PATH, password_path: Path = PASSWORD_PATH) -> tuple[str, str]:
    address = tomllib.loads(config_path.read_text())["inbox"]["address"]
    password = re.sub(r"\s+", "", password_path.read_text())
    return address, password


def load_cursor(connection: sqlite3.Connection) -> tuple[int, int] | None:
    row = connection.execute("SELECT cursor FROM stream_cursors WHERE source_id = ?", (SOURCE_ID,)).fetchone()
    if not row:
        return None
    packed = int(row["cursor"])
    return packed >> 32, packed & 0xFFFFFFFF


def _save_cursor(connection: sqlite3.Connection, uidvalidity: int, uid: int, now: dt.datetime) -> None:
    # One integer column holds both: UIDVALIDITY in the high 32 bits, UID in the low.
    connection.execute(
        """
        INSERT INTO stream_cursors (source_id, cursor, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET cursor = excluded.cursor, updated_at = excluded.updated_at
        """,
        (SOURCE_ID, (uidvalidity << 32) | uid, iso(now)),
    )


def poll(
    connection: sqlite3.Connection,
    mailbox: Mailbox,
    *,
    watch: Iterable[WatchItem],
    now: dt.datetime,
    set_keys: Iterable[str] | None = None,
) -> list[int]:
    """Fetch mail newer than the cursor; returns new observation ids."""
    watch = list(watch)
    keys = catalog_set_keys(connection) if set_keys is None else list(set_keys)
    cursor = load_cursor(connection)
    if cursor and cursor[0] == mailbox.uidvalidity:
        uids = mailbox.search(after_uid=cursor[1], since=None)
    else:
        uids = mailbox.search(after_uid=None, since=now.date() - FIRST_POLL_LOOKBACK)

    new_ids = []
    last_uid = cursor[1] if cursor and cursor[0] == mailbox.uidvalidity else 0
    for uid in uids:
        alert = message.parse_email(mailbox.fetch(uid))
        last_uid = max(last_uid, uid)
        if not message.is_relevant(alert):
            continue
        parsed = message.classify(alert, set_keys=keys)
        matches = matching.watch_matches(parsed.text, watch, keys) if parsed.is_tcg else []
        external_id = alert.message_id or f"uid:{mailbox.uidvalidity}:{uid}"
        inserted = connection.execute(
            """
            INSERT OR IGNORE INTO observations
                (source_id, external_id, author, text, signal, retailer, product_text, price, url,
                 is_tcg, watch_matches, source_time, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SOURCE_ID, external_id, alert.sender_domain, parsed.text, parsed.signal, parsed.retailer,
                parsed.product_text, parsed.price, parsed.url, int(parsed.is_tcg), json.dumps(matches),
                parsed.created_at, iso(now),
            ),
        )
        if inserted.rowcount:
            new_ids.append(inserted.lastrowid)
    _save_cursor(connection, mailbox.uidvalidity, last_uid, now)
    connection.commit()
    return new_ids


def run_inbox(
    connection: sqlite3.Connection,
    *,
    watch: Iterable[WatchItem],
    on_observation: Callable[[int], None] | None = None,
    clock: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.timezone.utc),
    open_mailbox: Callable[[], ImapMailbox] | None = None,
) -> None:
    """Poll forever on one connection, reconnecting with capped backoff."""
    watch = list(watch)
    open_mailbox = open_mailbox or (lambda: ImapMailbox(*credentials()))
    backoff = 5
    while True:
        mailbox = None
        try:
            mailbox = open_mailbox()
            backoff = 5
            while True:
                for observation_id in poll(connection, mailbox, watch=watch, now=clock()):
                    if on_observation:
                        on_observation(observation_id)
                sources.record_run(connection, SOURCE_ID, ok=True, now=clock())
                time.sleep(POLL_INTERVAL_S)
                mailbox.noop()
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # network and auth errors: record, back off, reconnect
            # Never log credentials; exception text from imaplib does not include them.
            sources.record_run(connection, SOURCE_ID, ok=False, error=f"{type(exc).__name__}: {exc}"[:300], now=clock())
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_S)
        finally:
            if mailbox is not None:
                mailbox.close()
