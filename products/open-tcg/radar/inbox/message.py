"""Parse alert emails into plain data. Email content is untrusted input.

HTML is reduced to text and links; scripts and styles are dropped. Nothing
here follows a link, loads a remote image, or acts on what an email says.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from email import message_from_bytes, policy
from email.utils import parseaddr, parsedate_to_datetime
from html.parser import HTMLParser
from typing import Iterable

from ..social import parse

# Generic filter: any mail mentioning Pokémon, plus the alert services we
# subscribed to (their subject lines may name only the product).
KNOWN_ALERT_SENDERS = frozenset({"nowinstock.net", "keepa.com"})
_POKEMON = re.compile(r"pok[eé]mon", re.IGNORECASE)
_PRICE_ALERT = re.compile(r"\bprice (alert|drop|dropped)\b|\bback in stock\b", re.IGNORECASE)
BODY_LIMIT = 4000


class _TextAndLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.links: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "a":
            href = dict(attrs).get("href") or ""
            if href.startswith(("http://", "https://")):
                self.links.append(href)
        elif tag in ("br", "p", "div", "tr", "li"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


@dataclass(frozen=True)
class EmailAlert:
    message_id: str
    sender: str
    sender_domain: str
    subject: str
    sent_at: str | None
    body: str
    links: tuple[str, ...]


def _body_and_links(mail) -> tuple[str, list[str]]:
    part = mail.get_body(preferencelist=("html", "plain"))
    if part is None:
        return "", []
    content = part.get_content()
    if part.get_content_type() == "text/html":
        extractor = _TextAndLinks()
        extractor.feed(content)
        text, links = "".join(extractor.parts), extractor.links
    else:
        text, links = content, re.findall(r"https?://\S+", content)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)[:BODY_LIMIT], links


def parse_email(raw: bytes) -> EmailAlert:
    mail = message_from_bytes(raw, policy=policy.default)
    sender = parseaddr(str(mail.get("From", "")))[1].lower()
    try:
        sent_at = parsedate_to_datetime(str(mail["Date"])).astimezone(dt.timezone.utc).isoformat()
    except (TypeError, ValueError):
        sent_at = None
    body, links = _body_and_links(mail)
    return EmailAlert(
        message_id=str(mail.get("Message-ID", "")).strip(),
        sender=sender,
        sender_domain=sender.rpartition("@")[2],
        subject=" ".join(str(mail.get("Subject", "")).split()),
        sent_at=sent_at,
        body=body,
        links=tuple(links),
    )


def is_relevant(alert: EmailAlert) -> bool:
    if any(alert.sender_domain == domain or alert.sender_domain.endswith("." + domain) for domain in KNOWN_ALERT_SENDERS):
        return True
    return bool(_POKEMON.search(alert.subject) or _POKEMON.search(alert.body))


def classify(alert: EmailAlert, *, set_keys: Iterable[str]) -> parse.ParsedPost:
    """Reuse the post classifier on subject + body; emails add a few rules."""
    text = f"{alert.subject}\n{alert.body}"
    parsed = parse.parse_post({"text": text}, set_keys=set_keys)
    signal = parsed.signal
    # A price alert or back-in-stock mail means the item can be bought now.
    if signal == "other" and _PRICE_ALERT.search(text):
        signal = "in_stock"
    retailer = parse.parse_post({"text": alert.subject}).retailer or parsed.retailer
    return parse.ParsedPost(
        text=text,
        signal=signal,
        retailer=retailer,
        product_text=alert.subject,
        price=parsed.price,
        url=alert.links[0] if alert.links else parsed.url,
        is_tcg=parsed.is_tcg or bool(_POKEMON.search(text)),
        created_at=alert.sent_at,
    )
