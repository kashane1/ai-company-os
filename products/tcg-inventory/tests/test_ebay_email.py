"""Tests for reading eBay sale notifications.

The fixture below is a real notification with the buyer's name and address
removed — which is also what the parser does, so the removal costs the tests
no coverage.
"""

from __future__ import annotations

import pytest

from inventory import ebay_email, intake
from inventory.ebay_email import NotASaleEmail

SUBJECT = "You made the sale for Pokémon TCG 30th Celebration ETB Elite Trainer Box ..."

BODY = """\
Shop eBay

Great news-your item has sold!
Get a shipping label or QR code

Your buyer's shipping details:

Ship by:
Oct 06, 2026

Hi April,

Your buyer has paid and now it's time to get a shipping label.

Pokémon TCG 30th Celebration ETB Elite Trainer Box ...
Pokémon TCG 30th Celebration ETB Elite Trainer Box ...
Sold:

$140.00

Order:

25-15223-93243

Date sold:

Oct 04, 2026

Buyer:

bestdeal1981

Quantity sold:

1

Package icon
The right way to package
"""


# ─── Parsing ─────────────────────────────────────────────────────────────────

def test_reads_the_fields_delisting_needs():
    sale = ebay_email.parse_sale(SUBJECT, BODY)

    assert sale.order_id == "25-15223-93243"
    assert sale.price_cents == 14000
    assert sale.quantity == 1
    assert sale.sold_on.isoformat() == "2026-10-04"
    assert sale.title.startswith("Pokémon TCG 30th Celebration ETB")


def test_the_order_number_is_the_idempotency_key():
    """eBay redelivers these, and a replay must not become a second sale."""
    first = ebay_email.parse_sale(SUBJECT, BODY)
    again = ebay_email.parse_sale(SUBJECT, BODY)

    assert first.idempotency_key == again.idempotency_key == "ebay:order:25-15223-93243"


def test_a_truncated_title_is_flagged_as_a_prefix():
    sale = ebay_email.parse_sale(SUBJECT, BODY)

    assert sale.is_truncated_title


def test_an_untruncated_title_is_not_flagged():
    sale = ebay_email.parse_sale("You made the sale for Iono 269/193", BODY)

    assert not sale.is_truncated_title


def test_the_buyer_address_is_not_extracted():
    """Nothing downstream needs it, and eBay prints the label."""
    sale = ebay_email.parse_sale(SUBJECT, BODY)

    assert not hasattr(sale, "buyer")
    assert "alameda" not in repr(sale).lower()


def test_a_marketing_email_is_refused_not_guessed():
    with pytest.raises(NotASaleEmail):
        ebay_email.parse_sale("Your weekly seller digest", BODY)


def test_a_sale_email_missing_its_order_number_raises():
    with pytest.raises(NotASaleEmail):
        ebay_email.parse_sale(SUBJECT, "Sold:\n\n$140.00\n")


# ─── Matching a sale to a listing ────────────────────────────────────────────

def listed(conn, title, price, variant=1, condition="NM"):
    copy_id = intake.add_copy(conn, variant, condition).copy_id
    return intake.list_copy(conn, copy_id, "ebay", price, listing_title=title)


def sale(title="Charizard ex 199/165 ...", price_cents=5000):
    return ebay_email.EbaySale(
        order_id="25-00000-00001", title=title,
        price_cents=price_cents, quantity=1, sold_on=None,
    )


def test_a_truncated_title_matches_on_its_prefix(conn):
    listing_id = listed(conn, "Charizard ex 199/165 Scarlet & Violet 151 SIR", 5000)

    match = ebay_email.match_listing(conn, sale())

    assert match["listing_id"] == listing_id


def test_an_ambiguous_prefix_matches_nothing(conn):
    """Delisting the wrong one strands a card you still own."""
    listed(conn, "Charizard ex 199/165 Scarlet & Violet 151 SIR", 5000)
    listed(conn, "Charizard ex 199/165 Scarlet & Violet 151 SIR LP", 4900, condition="LP")

    assert ebay_email.match_listing(conn, sale()) is None


def test_price_breaks_a_tie_when_one_listing_is_clearly_closer(conn):
    cheap = listed(conn, "Charizard ex 199/165 Scarlet & Violet 151", 500)
    listed(conn, "Charizard ex 199/165 Scarlet & Violet 151 SIR", 9000, condition="LP")

    match = ebay_email.match_listing(conn, sale(price_cents=520))

    assert match["listing_id"] == cheap


def test_an_ended_listing_is_never_matched(conn):
    listing_id = listed(conn, "Charizard ex 199/165 Scarlet & Violet 151 SIR", 5000)
    intake.end_listing(conn, listing_id, "sold")

    assert ebay_email.match_listing(conn, sale()) is None


def test_no_match_returns_none_rather_than_raising(conn):
    listed(conn, "Umbreon VMAX 215/203 Evolving Skies", 5000)

    assert ebay_email.match_listing(conn, sale()) is None
