"""Per-channel draft copy and native deep-links for the action dashboard.

Each prospect row needs, per channel, (a) a short prefilled message and (b) a
URL/scheme that opens the native composer with that message already in it. The
operator reviews and hits send themselves; nothing here sends.

Copy reuses ``outreach.context_for`` (passing empty snippets) so genre nouns,
the short observed gap, city, and mockup URL all come from the one place that
already computes them. Output is run through ``sanitize_outreach_copy`` to keep
the no-em-dash, machine-written-tell rules the GTM lane enforces.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote, urlencode

from packages.agency.outreach import OutreachContext, context_for, sanitize_outreach_copy

GMAIL_COMPOSE_BASE = "https://mail.google.com/mail/"


@dataclass(frozen=True)
class ChannelMessages:
    email_subject: str
    email_body: str
    sms_body: str
    dm_body: str
    call_script: str

    def to_dict(self) -> dict[str, str]:
        return {
            "email_subject": self.email_subject,
            "email_body": self.email_body,
            "sms_body": self.sms_body,
            "dm_body": self.dm_body,
            "call_script": self.call_script,
        }


def build_messages(record: dict) -> ChannelMessages:
    ctx = context_for(record, {})
    return build_messages_from_context(ctx)


def build_messages_from_context(ctx: OutreachContext) -> ChannelMessages:
    business = ctx.business_name or "your business"
    search_phrase = ctx.search_phrase or "local businesses"
    city = ctx.city or "town"
    url = ctx.mockup_url
    owner = ctx.owner_name or "there"

    sms = (
        f"Hi, this is {ctx.sender_name}. I found {business} while looking up "
        f"{search_phrase} in {city} and made a website preview: {url}. "
        "It shows services, hours, and a clear way to book or call. Useful?"
    )
    dm = (
        f"Hi there. I found {business} while looking up {search_phrase} in "
        f"{city} and made a website preview: {url}\n\n"
        "The idea is to show your work, services, hours, and a clear way "
        "for people to book or call. If you like it, I can make it yours."
    )
    email_subject = f"I made a website preview for {business}"
    email_body = (
        f"Hi {owner},\n\n"
        f"I found {business} while looking up {search_phrase} in {city} and wanted to "
        "show you something practical.\n\n"
        "I put together a one-page preview with space for your work, services, "
        "hours, and a clear way for customers to book or call:\n\n"
        f"{url}\n\n"
        "If you like it, I can make it yours. If it is not a fit, all good.\n\n"
        'Reply "no thanks" and I won\'t email again.\n\n'
        f"Best,\n{ctx.sender_name}\n{ctx.sender_company}"
    )
    call_script = (
        f"- Hi, is this the owner of {business}?\n"
        f"- My name is {ctx.sender_name}. I found you while looking up {search_phrase} in {city}.\n"
        f"- I made a website preview for {business}: {url}\n"
        "- It shows services, hours, and a clear way to book or call.\n"
        "- Would it be useful if I texted you the link?"
    )
    return ChannelMessages(
        email_subject=sanitize_outreach_copy(email_subject),
        email_body=sanitize_outreach_copy(email_body),
        sms_body=sanitize_outreach_copy(sms),
        dm_body=sanitize_outreach_copy(dm),
        call_script=sanitize_outreach_copy(call_script),
    )


# --------------------------------------------------------------------- links
def normalize_phone(phone: str) -> str:
    """Strip formatting to a ``tel:``/``sms:``-safe number, preserving a ``+``."""
    cleaned = re.sub(r"[^\d+]", "", phone or "")
    if "+" in cleaned:
        cleaned = "+" + cleaned.replace("+", "")
    return cleaned


def gmail_compose_url(*, to: str, subject: str, body: str) -> str:
    params = urlencode(
        {"view": "cm", "fs": "1", "to": to, "su": subject, "body": body},
        quote_via=quote,
    )
    return f"{GMAIL_COMPOSE_BASE}?{params}"


def sms_url(phone: str, body: str) -> str:
    # macOS Messages accepts `sms:<number>&body=<text>`.
    return f"sms:{normalize_phone(phone)}&body={quote(body)}"


def tel_url(phone: str) -> str:
    return f"tel:{normalize_phone(phone)}"


def facebook_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return f"https://www.facebook.com/{value.lstrip('@/')}"


def instagram_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return f"https://instagram.com/{value.lstrip('@/')}"


__all__ = [
    "ChannelMessages",
    "build_messages",
    "build_messages_from_context",
    "normalize_phone",
    "gmail_compose_url",
    "sms_url",
    "tel_url",
    "facebook_url",
    "instagram_url",
]
