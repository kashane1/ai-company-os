"""Reading eBay's "your item has sold" notification into a sale we can act on.

This is the cross-delisting trigger. A card live on both marketplaces sells on
one of them, and the other listing has to come down before someone else buys a
card that is already in an envelope. Until the Platform Notifications webhook
is wired, the sale email is the fastest signal available — it arrives within a
minute or two of checkout.

Three things shape this parser:

  It reads the plain-text rendering, not the HTML. eBay's template changes its
  markup often and its labels rarely, so matching on "Order:" survives a
  redesign that would break a CSS selector.

  It deliberately drops the buyer's name and shipping address. The email leads
  with both, nothing downstream needs them, and inventory data tends to outlive
  the reason it was collected. eBay already has the address, and the shipping
  label comes from eBay. Parsing it out would mean storing someone's home
  address in a hobby database forever.

  It refuses rather than guesses. A half-parsed sale that silently fails to
  match a listing is worse than one that raises, because the failure shows up
  later as an oversell rather than now as an error.

The order number is the idempotency key. eBay re-sends these, mail clients
re-deliver them, and a replayed sale must not become a second sale — which is
what `events.idempotency_key` is for.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime

# "Order:" and "Sold:" sit on their own line in the text rendering, with the
# value on the next one. \s*\n\s* spans that break without also swallowing a
# following label, which a bare \s+ would do on an empty field.
_FIELD = r"^\s*{label}\s*:?\s*\n\s*(?P<value>.+?)\s*$"

_ORDER_RE = re.compile(_FIELD.format(label="Order"), re.MULTILINE)
_PRICE_RE = re.compile(_FIELD.format(label="Sold"), re.MULTILINE)
_DATE_RE = re.compile(_FIELD.format(label="Date sold"), re.MULTILINE)
_QTY_RE = re.compile(_FIELD.format(label="Quantity sold"), re.MULTILINE)

# "You made the sale for <title>" — eBay truncates long titles with an ellipsis,
# so what comes back is a prefix of the listing title, never the whole thing.
_SUBJECT_RE = re.compile(
    r"You (?:made|have made) the sale for\s+(?P<title>.+?)\s*$", re.IGNORECASE
)

_MONEY_RE = re.compile(r"\$?\s*([\d,]+(?:\.\d{1,2})?)")

# The most postage that could plausibly sit between a list price and the total
# eBay reports. A rigid mailer runs about $4.50, so this leaves room without
# making every listing on the shelf a candidate.
MAX_IMPLIED_SHIPPING_CENTS = 800


class NotASaleEmail(ValueError):
    """The message is not an eBay sale notification, or is missing its fields."""


@dataclass(frozen=True)
class EbaySale:
    """One sold item, carrying only what delisting and reconciliation need."""

    order_id: str
    title: str
    price_cents: int
    quantity: int
    sold_on: date | None

    @property
    def idempotency_key(self) -> str:
        """Stable across every redelivery of this notification."""
        return f"ebay:order:{self.order_id}"

    @property
    def is_truncated_title(self) -> bool:
        """eBay cut the title short, so only a prefix match is possible."""
        return self.title.endswith("...") or self.title.endswith("…")


def _money_to_cents(text: str) -> int:
    match = _MONEY_RE.search(text)
    if match is None:
        raise NotASaleEmail(f"Could not read a price from {text!r}")
    return round(float(match.group(1).replace(",", "")) * 100)


def _parse_date(text: str) -> date | None:
    """eBay writes 'Oct 04, 2026'. A date we cannot read is not worth raising on."""
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _field(pattern: re.Pattern[str], body: str, label: str) -> str:
    match = pattern.search(body)
    if match is None:
        raise NotASaleEmail(f"No {label} in this message")
    return match.group("value").strip()


def parse_sale(subject: str, body: str) -> EbaySale:
    """Read one sale out of an eBay notification. Raises if it is not one.

    The title comes from the subject rather than the body: the body repeats it
    twice as link text, which collapses unpredictably depending on how the mail
    client rendered the HTML, while the subject is a single clean line.
    """
    subject_match = _SUBJECT_RE.search(subject.strip())
    if subject_match is None:
        raise NotASaleEmail(f"Subject is not an eBay sale notification: {subject!r}")

    quantity_text = _QTY_RE.search(body)
    return EbaySale(
        order_id=_field(_ORDER_RE, body, "order number"),
        title=subject_match.group("title").strip(),
        price_cents=_money_to_cents(_field(_PRICE_RE, body, "sale price")),
        quantity=int(quantity_text.group("value").strip()) if quantity_text else 1,
        sold_on=_parse_date(_field(_DATE_RE, body, "sale date")) if _DATE_RE.search(body) else None,
    )


def match_listing(conn: sqlite3.Connection, sale: EbaySale) -> sqlite3.Row | None:
    """Find the live eBay listing this sale belongs to, or None if it is unclear.

    Matching is on the listing title, because the sale email carries no item
    number — and on a truncated title it can only be a prefix. That is sound
    only while the prefix is unique among live listings, so an ambiguous match
    returns None rather than picking one. Two Charizards listed at different
    conditions share a title prefix, and delisting the wrong one puts a card
    you still own out of reach while leaving the sold one live.

    The price is only a tie-breaker. eBay reports the total paid including
    postage, so it can narrow several candidates down to one but can never
    confirm a match on its own.
    """
    prefix = sale.title.rstrip(" .…")
    rows = conn.execute(
        """
        SELECT l.*, c.condition_code
          FROM listings l
          JOIN copies c ON c.copy_id = l.copy_id
         WHERE l.channel = 'ebay'
           AND l.ended_at IS NULL
           AND l.listing_title IS NOT NULL
           AND l.listing_title LIKE ? || '%'
        """,
        (prefix,),
    ).fetchall()

    if len(rows) == 1:
        return rows[0]
    if not rows:
        return None

    # Several listings share the prefix, so fall back to the price. eBay reports
    # the total paid, which includes postage, so a candidate is plausible when
    # the gap between the sale and its list price looks like shipping: at or
    # above zero, and no larger than a rigid mailer costs.
    #
    # An exact price match is deliberately not treated as decisive. Listings at
    # $50.00 and $49.00 against a $50.00 sale are both consistent — the second
    # one with a dollar of postage — and picking the exact one would delist a
    # card still sitting in the binder while the sold one stayed live.
    plausible = [
        row
        for row in rows
        if 0 <= sale.price_cents - row["list_price_cents"] <= MAX_IMPLIED_SHIPPING_CENTS
    ]
    return plausible[0] if len(plausible) == 1 else None
