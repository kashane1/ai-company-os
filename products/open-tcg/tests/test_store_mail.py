from __future__ import annotations

import datetime as dt
from email.message import EmailMessage
from email.utils import format_datetime

import pytest

from radar.catalog import classify as catalog_classify
from radar.stores import collect, mail, registry

from .conftest import NOW

MOONBLAST = registry.Store(
    store_id="tcg_moonblast", name="TCG Moonblast", domain="tcgmoonblast.com", tier="backup",
    platform="wix", email_signup="drop", email_status="subscribed",
)
WULF = registry.Store(
    store_id="wulf_gaming", name="Wulf Gaming", domain="wulfgaming.com", tier="first_pass",
    email_signup="drop", email_status="subscribed",
)
INDY = registry.Store(
    store_id="indy_card_shop", name="Indy Card Shop", domain="indycardshop.myshopify.com", tier="first_pass",
    email_signup="drop", email_status="needs_founder",
)
STORES = [MOONBLAST, WULF, INDY]


def raw_email(*, sender: str, subject: str, html: str = "<p>hello</p>", sent: dt.datetime = NOW, message_id: str | None = None) -> bytes:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = "jimsimons01102000@gmail.com"
    message["Subject"] = subject
    message["Date"] = format_datetime(sent)
    message["Message-ID"] = message_id or f"<{abs(hash((sender, subject, sent)))}@test>"
    message.set_content("plain")
    message.add_alternative(html, subtype="html")
    return bytes(message)


@pytest.mark.parametrize(
    ("subject", "body", "expected"),
    [
        ("Delta Reign Pokémon preorders are LIVE!", "", ("drop", True)),
        ("RESTOCK: Prismatic Evolutions back in stock", "pokemon tcg", ("drop", True)),
        ("Welcome to TCG Slayer — you're on the list", "Pokémon drops", ("subscription", True)),
        ("Please confirm your subscription", "", ("subscription", False)),
        ("20% off everything this weekend", "Pokemon too", ("promo", True)),
        ("Thursday Price Drops", "Pokemon singles", ("promo", True)),
        ("Store hours this week", "Magic prerelease events", ("other", False)),
        ("This week at the shop", "New arrivals: Pokémon Chaos Rising ETBs", ("drop", True)),
    ],
)
def test_classify(subject, body, expected):
    assert mail.classify(subject, body) == expected


def test_attribution_paths():
    known = {"news@shopmail.example": "wulf_gaming"}
    def who(sender, display="", links=()):
        alert = mail.inbox_message.EmailAlert("<x>", sender, sender.rpartition("@")[2], "s", None, "", tuple(links))
        return mail.attribute(alert, display, STORES, known)

    assert who("matthew@tcgmoonblast.com") == ("tcg_moonblast", "sender_domain")
    assert who("hello@mail.tcgmoonblast.com") == ("tcg_moonblast", "sender_domain")
    assert who("wulfgamingmi@gmail.com", "Wulf Gaming") == ("wulf_gaming", "display_name")
    assert who("news@shopmail.example", "Anything") == ("wulf_gaming", "known_sender")
    indy_links = ["https://indycardshop.myshopify.com/products/a", "https://indycardshop.myshopify.com/collections/b"]
    assert who("store@shopifyemail.com", "VAULT", indy_links) == ("indy_card_shop", "links")
    assert who("someone@gmail.com", "Random Person", ["https://example.com/x"]) == (None, None)


class FakeMailbox:
    def __init__(self, messages: dict[int, bytes], uidvalidity: int = 7):
        self.messages = messages
        self.uidvalidity = uidvalidity

    def search(self, *, after_uid, since):
        return sorted(uid for uid in self.messages if after_uid is None or uid > after_uid)

    def fetch(self, uid):
        return self.messages[uid]


def _seed_wulf_drop(connection, now):
    """What an immediate store check would have recorded: a matched ETB back in stock."""
    connection.execute("INSERT INTO ref_groups (group_id, name) VALUES (1, 'ME04: Chaos Rising')")
    connection.execute(
        "INSERT INTO ref_products (product_id, group_id, name, product_type, updated_at) VALUES (11, 1, ?, ?, '')",
        ("Chaos Rising Elite Trainer Box", catalog_classify.product_type("Chaos Rising Elite Trainer Box")),
    )
    connection.execute("INSERT INTO ref_price_points (product_id, day, market_price) VALUES (11, '2026-09-25', 66.41)")
    collect.sync_registry(connection, [WULF])
    connection.execute(
        """
        INSERT INTO store_listings (store_id, variant_id, shop_product_id, handle, title, url, first_seen_at,
            last_seen_at, is_baseline, price_cents, is_available, language, match_status, catalog_product_id)
        VALUES ('wulf_gaming', 1, 1, 'cr-etb', 'Chaos Rising ETB', 'https://wulfgaming.com/products/cr-etb',
            ?, ?, 0, 4999, 1, 'en', 'exact', 11)
        """,
        (now.isoformat(), now.isoformat()),
    )
    connection.execute(
        "INSERT INTO listing_snapshots (store_id, variant_id, observed_at, change, price_cents, is_available) "
        "VALUES ('wulf_gaming', 1, ?, 'first_seen', 4999, 1)",
        (now.isoformat(),),
    )


def test_poll_notifies_once_with_what_is_in_stock(connection):
    notes, checks = [], []

    def check_store(conn, store, now):
        checks.append(store.store_id)
        _seed_wulf_drop(conn, now)
        return True

    mailbox = FakeMailbox({
        1: raw_email(sender="Wulf Gaming <wulfgamingmi@gmail.com>", subject="Pokémon Chaos Rising restock is live now"),
        2: raw_email(sender="Wulf Gaming <wulfgamingmi@gmail.com>", subject="More Pokemon drops tonight", sent=NOW + dt.timedelta(minutes=5)),
        3: raw_email(sender="Aunt May <may@example.com>", subject="Dinner Sunday?"),
    })
    new = mail.poll(connection, mailbox, stores=STORES, now=NOW + dt.timedelta(minutes=6),
                    check_store=check_store, notifier=lambda t, b: notes.append((t, b)))
    assert [(e.store_id, e.kind) for e in new] == [("wulf_gaming", "drop"), ("wulf_gaming", "drop")]
    assert checks == ["wulf_gaming"]  # the second drop email is inside the cooldown
    assert notes == [(
        "Wulf Gaming: drop email",
        "Pokémon Chaos Rising restock is live now\nIn stock now: Chaos Rising Elite Trainer Box $49.99, market $66.41",
    )]
    # Unrelated personal mail is not stored, and the sender was learned.
    assert connection.execute("SELECT COUNT(*) FROM store_emails").fetchone()[0] == 2
    assert connection.execute("SELECT store_id FROM store_mail_senders").fetchone()[0] == "wulf_gaming"
    # The cursor moved past everything read.
    assert mail.poll(connection, mailbox, stores=STORES, now=NOW, check_store=check_store, notifier=notes.append) == []


def test_unpolled_store_notifies_with_link_and_stale_mail_is_quiet(connection):
    notes = []
    html = '<a href="https://www.tcgmoonblast.com/category/pokemon">Shop the drop</a>'
    mailbox = FakeMailbox({
        1: raw_email(sender="TCG Moonblast <matthew@tcgmoonblast.com>", subject="Old: Pokemon preorders live",
                     sent=NOW - dt.timedelta(hours=3), message_id="<old@x>"),
        2: raw_email(sender="TCG Moonblast <matthew@tcgmoonblast.com>", subject="Delta Reign Pokemon preorders are live",
                     html=html, message_id="<new@x>"),
        3: raw_email(sender="TCG Moonblast <matthew@tcgmoonblast.com>", subject="Heck yeah, welcome to the drops list",
                     message_id="<welcome@x>"),
    })
    mail.poll(connection, mailbox, stores=STORES, now=NOW, check_store=lambda *a: pytest.fail("not polled"),
              notifier=lambda t, b: notes.append((t, b)))
    assert notes == [("TCG Moonblast: drop email", "Delta Reign Pokemon preorders are live\nhttps://www.tcgmoonblast.com/category/pokemon")]
    kinds = dict(connection.execute("SELECT message_id, kind FROM store_emails").fetchall())
    assert kinds == {"<old@x>": "drop", "<new@x>": "drop", "<welcome@x>": "subscription"}


def test_forwarding_filter_lists_subscribed_domains_and_learned_senders(connection):
    collect.sync_registry(connection, STORES)
    connection.execute(
        "INSERT INTO store_mail_senders (sender, store_id, learned_at) VALUES ('wulfgamingmi@gmail.com', 'wulf_gaming', 'x')"
    )
    assert mail.forwarding_filter(connection, STORES) == "from:(tcgmoonblast.com OR wulfgaming.com OR wulfgamingmi@gmail.com)"


def test_shipped_registry_email_fields():
    stores = registry.load()
    moonblast = next(s for s in stores if s.store_id == "tcg_moonblast")
    assert (moonblast.email_signup, moonblast.email_status) == ("drop", "subscribed")
    assert sum(s.email_status == "subscribed" for s in stores) >= 14
