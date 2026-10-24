"""Store drop emails: attribute, classify, and act on them right away.

Reads the project inbox read-only with its own cursor and Gmail query (the
radar's alert-email reader is untouched). Store mail reaches that inbox
through the founder's Gmail forwarding filter (`radar store-mail-filter`
prints it). A fresh Pokémon drop email from a known store triggers an
immediate read of that store's newest page, then one Mac notification with
what the store lists in stock right now.

Email content is untrusted: nothing here follows a link or acts on what an
email says beyond reading its text.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from email import message_from_bytes, policy
from email.utils import parseaddr
from typing import Callable, Iterable
from urllib.parse import urlsplit

from .. import sources
from ..db import iso
from ..inbox import message as inbox_message
from ..inbox import reader as inbox_reader
from . import collect, match, registry

SOURCE_ID = "store_email"
# Everything except the alert services the radar's own reader handles.
GMAIL_QUERY = "-from:nowinstock.net -from:keepa.com"
FIRST_POLL_LOOKBACK = dt.timedelta(days=3)
POLL_INTERVAL_S = 30
MAX_BACKOFF_S = 300
# Older drop emails are recorded but don't notify (a backlog after downtime).
FRESH_FOR = dt.timedelta(minutes=60)
NOTIFY_COOLDOWN = dt.timedelta(minutes=30)
# Listings that appeared or came back in stock this recently count as the drop.
DROP_WINDOW = dt.timedelta(hours=2)

_SUBSCRIPTION = re.compile(
    r"\b(confirm (your )?(subscription|email)|welcome to|thanks? (you )?for (signing up|subscribing)|you'?re (subscribed|in|on the list)|verify your email)\b"
)
_DROP = re.compile(
    r"\b(drops?|dropping|live now|is live|are live|now live|restock(ed|s)?|back in stock|in stock now|just landed|new arrivals?"
    r"|pre-?orders? (are )?(open|live)|pre-?orders?|release(s|d)?|launch(es|ed)?|available now|allocation)\b"
)
_PROMO = re.compile(r"\b(\d+% off|sale|discount|coupon|promo code|black friday|cyber monday|deals?)\b")
# "Thursday Price Drops" is a sale, not a product drop.
_PRICE_DROP = re.compile(r"\bprice drops?\b")
_POKEMON = re.compile(r"pok[eé]mon|\bptcg\b")


@dataclass(frozen=True)
class StoreEmail:
    message_id: str
    store_id: str | None
    attribution: str | None
    sender: str
    display_name: str
    subject: str
    sent_at: str | None
    kind: str
    is_pokemon: bool
    first_link: str | None


def _root(domain: str) -> str:
    domain = domain.lower().removeprefix("www.")
    if domain.endswith(".myshopify.com"):
        return domain
    parts = domain.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def attribute(
    alert: inbox_message.EmailAlert,
    display_name: str,
    stores: Iterable[registry.Store],
    known_senders: dict[str, str],
) -> tuple[str | None, str | None]:
    """(store_id, how) for an email, or (None, None)."""
    stores = list(stores)
    if alert.sender in known_senders:
        return known_senders[alert.sender], "known_sender"
    sender_root = _root(alert.sender_domain)
    for store in stores:
        if _root(store.domain) == sender_root and not store.domain.endswith(".myshopify.com"):
            return store.store_id, "sender_domain"
    name = match.fold(display_name)
    if name:
        for store in sorted(stores, key=lambda s: -len(s.name)):
            store_name = match.fold(store.name)
            if len(store_name) >= 5 and (store_name in name or (len(name) >= 5 and name in store_name)):
                return store.store_id, "display_name"
    counts: dict[str, int] = {}
    for link in alert.links:
        host = (urlsplit(link).hostname or "").lower()
        for store in stores:
            if host and _root(host) == _root(store.domain):
                counts[store.store_id] = counts.get(store.store_id, 0) + 1
    if counts:
        best = max(counts.items(), key=lambda item: item[1])
        if best[1] >= 2 and list(counts.values()).count(best[1]) == 1:
            return best[0], "links"
    return None, None


def classify(subject: str, body: str) -> tuple[str, bool]:
    """(kind, is_pokemon). The subject decides first; the body only breaks ties."""
    subject_text = match.fold(subject)
    text = f"{subject_text}\n{match.fold(body)}"
    is_pokemon = bool(_POKEMON.search(text))
    if _SUBSCRIPTION.search(subject_text):
        return "subscription", is_pokemon
    if _PRICE_DROP.search(subject_text):
        return "promo", is_pokemon
    if _DROP.search(subject_text):
        return "drop", is_pokemon
    if _PROMO.search(subject_text):
        return "promo", is_pokemon
    if _DROP.search(text):
        return "drop", is_pokemon
    return ("promo" if _PROMO.search(text) else "other"), is_pokemon


def read_email(
    raw: bytes, stores: Iterable[registry.Store], known_senders: dict[str, str]
) -> StoreEmail:
    alert = inbox_message.parse_email(raw)
    display_name = parseaddr(str(message_from_bytes(raw, policy=policy.default).get("From", "")))[0]
    store_id, how = attribute(alert, display_name, stores, known_senders)
    kind, is_pokemon = classify(alert.subject, alert.body)
    return StoreEmail(
        message_id=alert.message_id or f"<no-id:{alert.sender}:{alert.sent_at}:{alert.subject[:40]}>",
        store_id=store_id,
        attribution=how,
        sender=alert.sender,
        display_name=display_name,
        subject=alert.subject,
        sent_at=alert.sent_at,
        kind=kind,
        is_pokemon=is_pokemon,
        first_link=alert.links[0] if alert.links else None,
    )


def record(connection: sqlite3.Connection, email: StoreEmail, *, now: dt.datetime) -> bool:
    """Store an email once and learn its sender; True when it is new."""
    inserted = connection.execute(
        """
        INSERT OR IGNORE INTO store_emails
            (message_id, store_id, attribution, sender, display_name, subject, sent_at, received_at,
             kind, is_pokemon, first_link)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            email.message_id, email.store_id, email.attribution, email.sender, email.display_name,
            email.subject, email.sent_at, iso(now), email.kind, int(email.is_pokemon), email.first_link,
        ),
    )
    if email.store_id and email.attribution != "known_sender":
        connection.execute(
            "INSERT OR IGNORE INTO store_mail_senders (sender, store_id, learned_at) VALUES (?, ?, ?)",
            (email.sender, email.store_id, iso(now)),
        )
    return inserted.rowcount == 1


def drop_listings(connection: sqlite3.Connection, store_id: str, *, now: dt.datetime, limit: int = 4) -> list[str]:
    """Matched listings in stock that appeared or came back in the drop window, cheapest first."""
    since = iso(now - DROP_WINDOW)
    rows = connection.execute(
        """
        SELECT p.name, l.price_cents,
               (SELECT market_price FROM ref_price_points pp WHERE pp.product_id = l.catalog_product_id
                  ORDER BY pp.day DESC LIMIT 1) AS market
        FROM store_listings l JOIN ref_products p ON p.product_id = l.catalog_product_id
        WHERE l.store_id = ? AND l.is_available = 1 AND l.match_status IN ('exact', 'confirmed')
          AND EXISTS (SELECT 1 FROM listing_snapshots n WHERE n.store_id = l.store_id
                        AND n.variant_id = l.variant_id AND n.observed_at >= ? AND n.is_available = 1)
        ORDER BY l.price_cents
        LIMIT ?
        """,
        (store_id, since, limit),
    ).fetchall()
    lines = []
    for row in rows:
        market = f", market ${row['market']:,.2f}" if row["market"] else ""
        lines.append(f"{row['name']} ${row['price_cents'] / 100:,.2f}{market}")
    return lines


def act(
    connection: sqlite3.Connection,
    email: StoreEmail,
    stores_by_id: dict[str, registry.Store],
    *,
    now: dt.datetime,
    check_store: Callable[[sqlite3.Connection, registry.Store, dt.datetime], bool],
    notifier: Callable[[str, str], None],
) -> bool:
    """Notify for a fresh Pokémon drop email from a known store; True if it notified."""
    if email.kind != "drop" or not email.is_pokemon or email.store_id is None:
        return False
    store = stores_by_id.get(email.store_id)
    if store is None:
        return False
    if email.sent_at and now - dt.datetime.fromisoformat(email.sent_at) > FRESH_FOR:
        return False
    last = connection.execute(
        "SELECT MAX(notified_at) AS last FROM store_emails WHERE store_id = ? AND notified_at IS NOT NULL",
        (store.store_id,),
    ).fetchone()["last"]
    if last and now - dt.datetime.fromisoformat(last) < NOTIFY_COOLDOWN:
        return False
    lines: list[str] = []
    if store.is_polled and check_store(connection, store, now):
        lines = drop_listings(connection, store.store_id, now=now)
    body = email.subject
    if lines:
        body += "\nIn stock now: " + "; ".join(lines)
    elif email.first_link:
        body += f"\n{email.first_link}"
    notifier(f"{store.name}: drop email", body)
    connection.execute(
        "UPDATE store_emails SET notified_at = ? WHERE message_id = ?", (iso(now), email.message_id)
    )
    connection.commit()
    return True


class StoreMailbox(inbox_reader.ImapMailbox):
    """The project inbox, read-only, searched with the store-mail query."""

    def search(self, *, after_uid: int | None, since: dt.date | None) -> list[int]:
        criteria = []
        if after_uid is not None:
            criteria += ["UID", f"{after_uid + 1}:*"]
        if since is not None:
            criteria += ["SINCE", since.strftime("%d-%b-%Y")]
        criteria += ["X-GM-RAW", f'"{GMAIL_QUERY}"']
        status, data = self._imap.uid("SEARCH", *criteria)
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {status}")
        uids = [int(uid) for uid in (data[0] or b"").split()]
        return sorted(uid for uid in uids if after_uid is None or uid > after_uid)


def _load_cursor(connection: sqlite3.Connection) -> tuple[int, int] | None:
    row = connection.execute("SELECT cursor FROM stream_cursors WHERE source_id = ?", (SOURCE_ID,)).fetchone()
    if not row:
        return None
    packed = int(row["cursor"])
    return packed >> 32, packed & 0xFFFFFFFF


def _save_cursor(connection: sqlite3.Connection, uidvalidity: int, uid: int, now: dt.datetime) -> None:
    connection.execute(
        """
        INSERT INTO stream_cursors (source_id, cursor, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET cursor = excluded.cursor, updated_at = excluded.updated_at
        """,
        (SOURCE_ID, (uidvalidity << 32) | uid, iso(now)),
    )


def poll(
    connection: sqlite3.Connection,
    mailbox: inbox_reader.Mailbox,
    *,
    stores: list[registry.Store],
    now: dt.datetime,
    check_store: Callable[[sqlite3.Connection, registry.Store, dt.datetime], bool],
    notifier: Callable[[str, str], None],
) -> list[StoreEmail]:
    """Read mail newer than the cursor; returns new store emails (attributed or not)."""
    collect.sync_registry(connection, stores)
    cursor = _load_cursor(connection)
    if cursor and cursor[0] == mailbox.uidvalidity:
        uids = mailbox.search(after_uid=cursor[1], since=None)
        last_uid = cursor[1]
    else:
        uids = mailbox.search(after_uid=None, since=now.date() - FIRST_POLL_LOOKBACK)
        last_uid = 0
    known = {row["sender"]: row["store_id"] for row in connection.execute("SELECT sender, store_id FROM store_mail_senders")}
    by_id = {store.store_id: store for store in stores}
    new = []
    for uid in uids:
        email = read_email(mailbox.fetch(uid), stores, known)
        last_uid = max(last_uid, uid)
        if email.store_id is None and email.kind == "other" and not email.is_pokemon:
            continue  # unrelated mail: not stored
        if record(connection, email, now=now):
            new.append(email)
            if email.store_id:
                known[email.sender] = email.store_id
            act(connection, email, by_id, now=now, check_store=check_store, notifier=notifier)
    _save_cursor(connection, mailbox.uidvalidity, last_uid, now)
    connection.commit()
    return new


def run(
    connection: sqlite3.Connection,
    *,
    on_email: Callable[[StoreEmail], None] | None = None,
    clock: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.timezone.utc),
    notifier: Callable[[str, str], None] | None = None,
) -> None:
    """Poll forever, reconnecting with capped backoff (as the alert-email reader does)."""
    from ..notify import macos_notify

    notifier = notifier or macos_notify

    def check_and_alert(c: sqlite3.Connection, store: registry.Store, at: dt.datetime) -> bool:
        """Read the store now, then alert on any MSRP hit the read found (P4)."""
        from . import alerts  # imported here: alerts -> report -> mail

        ok = collect.check_store_now(c, store, now=at)
        if ok:
            alerts.evaluate(c, now=at, send=notifier)
        return ok

    backoff = 5
    while True:
        mailbox = None
        try:
            mailbox = StoreMailbox(*inbox_reader.credentials())
            backoff = 5
            while True:
                stores = registry.load()
                for email in poll(
                    connection,
                    mailbox,
                    stores=stores,
                    now=clock(),
                    check_store=check_and_alert,
                    notifier=notifier,
                ):
                    if on_email:
                        on_email(email)
                sources.record_run(connection, SOURCE_ID, ok=True, now=clock())
                time.sleep(POLL_INTERVAL_S)
                mailbox.noop()
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # network and auth errors: record, back off, reconnect
            sources.record_run(connection, SOURCE_ID, ok=False, error=f"{type(exc).__name__}: {exc}"[:300], now=clock())
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_S)
        finally:
            if mailbox is not None:
                mailbox.close()


def forwarding_filter(connection: sqlite3.Connection, stores: Iterable[registry.Store]) -> str:
    """A Gmail search for the founder's forwarding filter: subscribed stores' domains plus learned senders."""
    terms = []
    for store in stores:
        if store.email_status == "subscribed" and not store.domain.endswith(".myshopify.com"):
            terms.append(_root(store.domain))
    for row in connection.execute("SELECT DISTINCT sender FROM store_mail_senders ORDER BY sender"):
        if _root(row["sender"].rpartition("@")[2]) not in terms:
            terms.append(row["sender"])
    return "from:(" + " OR ".join(dict.fromkeys(terms)) + ")"


def summary(connection: sqlite3.Connection, *, since: dt.datetime) -> list[str]:
    lines = []
    for row in connection.execute(
        """
        SELECT COALESCE(s.name, '(unattributed) ' || e.sender) AS who, e.kind, e.is_pokemon,
               COUNT(*) AS n, MAX(e.received_at) AS last
        FROM store_emails e LEFT JOIN stores s USING (store_id)
        WHERE e.received_at >= ? GROUP BY 1, 2, 3 ORDER BY last DESC
        """,
        (iso(since),),
    ):
        pokemon = " pokemon" if row["is_pokemon"] else ""
        lines.append(f"  {row['last'][:16]}  {row['n']:>3} {row['kind']:<12}{pokemon:<8} {row['who']}")
    return lines


def to_json(email: StoreEmail) -> str:
    return json.dumps(email.__dict__, sort_keys=True)
