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

from packages.agency.outreach import (
    DEFAULT_SENDER_COMPANY,
    DEFAULT_SENDER_NAME,
    OutreachContext,
    context_for,
    sanitize_outreach_copy,
)

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


def build_messages_from_context(
    ctx: OutreachContext,
    *,
    step: int = 1,
    observation: str = "",
) -> ChannelMessages:
    """Per-channel draft copy for a prospect.

    ``step`` is the touch number this draft is for (1 = first touch, 2/3 =
    follow-ups). Step 1 is the original touch-1 copy, unchanged. For step >= 2 the
    bodies are shorter follow-ups that re-reference the demo URL and weave in
    ``observation`` (one verified fact or a re-pitch of the gap; see
    ``outreach_sequencer.observation_for_step``).
    """
    if step >= 2:
        return _build_follow_up_messages(ctx, observation=observation)
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
    # Quiet per-prospect reference token below the signature. Reply-sync (item 5)
    # matches inbound mail back to this prospect by it; email only, since IG/FB
    # replies are logged manually. Omitted when there is no place_id to derive it.
    if ctx.ref_token:
        email_body += f"\n\nref: {ctx.ref_token}"
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


def _build_follow_up_messages(ctx: OutreachContext, *, observation: str) -> ChannelMessages:
    """Touch-2/3 copy: shorter, re-references the preview URL, weaves in one new
    observation (email/DM), keeps the opt-out line + ref token on email."""
    business = ctx.business_name or "your business"
    url = ctx.mockup_url
    owner = ctx.owner_name or "there"
    observation = (observation or "").strip()

    email_subject = f"Following up: website preview for {business}"
    email_paras = [
        f"Hi {owner},",
        f"I wanted to follow up on the website preview I put together for {business}:",
        f"{url}",
    ]
    if observation:
        email_paras.append(observation)
    email_paras.append(
        "If it is useful, I can walk you through it or make it yours. If not, no worries."
    )
    email_paras.append('Reply "no thanks" and I won\'t email again.')
    email_paras.append(f"Best,\n{ctx.sender_name}\n{ctx.sender_company}")
    email_body = "\n\n".join(email_paras)
    # Keep the per-prospect reference token so reply-sync still matches the thread.
    if ctx.ref_token:
        email_body += f"\n\nref: {ctx.ref_token}"

    sms = (
        f"Hi, this is {ctx.sender_name} following up on the website preview for "
        f"{business}: {url}. Worth a quick look?"
    )

    dm_lines = [f"Hi again. Following up on the website preview I made for {business}: {url}"]
    if observation:
        dm_lines.append(observation)
    dm_lines.append("If you like it, I can make it yours. No worries if the timing is off.")
    dm = "\n\n".join(dm_lines)

    call_script = (
        f"- Hi, is this the owner of {business}?\n"
        f"- This is {ctx.sender_name}, following up. I sent over a website preview "
        f"for {business}: {url}\n"
        "- Did you get a chance to look at it?\n"
        "- If it is useful, I can walk you through it or make it yours."
    )

    return ChannelMessages(
        email_subject=sanitize_outreach_copy(email_subject),
        email_body=sanitize_outreach_copy(email_body),
        sms_body=sanitize_outreach_copy(sms),
        dm_body=sanitize_outreach_copy(dm),
        call_script=sanitize_outreach_copy(call_script),
    )


# ------------------------------------------------------------------- teaser
def build_teaser_messages(
    *,
    business_name: str,
    city: str,
    site_url: str,
    findings: list[dict],
    offer: dict,
    sender_name: str = DEFAULT_SENDER_NAME,
    sender_company: str = DEFAULT_SENDER_COMPANY,
    ref_token: str = "",
) -> ChannelMessages:
    """Teaser-variant copy: pitch the paid Conversion Audit of their *existing*
    site, not a rebuild.

    The opener leads with one concrete observation from the synthetic-panel
    findings (honest, specific), discloses the methodology in passing, and points
    to the paid audit. ``findings`` are the validated teaser findings (dicts with
    a ``title``); ``offer`` carries the audit/snapshot names+fees.
    """
    business = business_name or "your business"
    audit_name = str(offer.get("audit_name") or "Conversion Audit")
    audit_fee = offer.get("audit_fee")
    snapshot_name = str(offer.get("snapshot_name") or "Conversion Snapshot")
    snapshot_fee = offer.get("snapshot_fee")
    audit_price = f" (${audit_fee})" if audit_fee else ""
    snapshot_price = f" (${snapshot_fee})" if snapshot_fee else ""
    headline = str((findings[0] or {}).get("title") or "") if findings else ""
    count = len(findings)
    things = "thing" if count == 1 else "things"
    where = f" in {city}" if city else ""

    # One short, specific hook from the top finding — no revenue claims.
    hook = (
        f"the biggest one being {headline[0].lower() + headline[1:]}"
        if headline
        else "a few specific things worth a look"
    )

    email_subject = f"A quick read on the {business} website"
    email_body = (
        f"Hi there,\n\n"
        f"I run conversion audits for local businesses{where} and took an honest look "
        f"at {site_url}. I ran it past a panel of buyer personas and pulled {count} "
        f"things that might be costing you calls, {hook}.\n\n"
        f"I wrote it up as a one-page teaser, happy to send it over. If it's useful, "
        f"the full {audit_name}{audit_price} is a persona-by-persona teardown of the "
        f"whole site with prioritized copy fixes (the {snapshot_name}{snapshot_price} "
        f"is a faster single-page version). No rebuild, just advice on the site you have.\n\n"
        f"Worth a look?\n\n"
        f"Best,\n{sender_name}\n{sender_company}"
    )
    if ref_token:
        email_body += f"\n\nref: {ref_token}"

    sms = (
        f"Hi, this is {sender_name}. I did a quick conversion read on the {business} "
        f"website ({site_url}) with a buyer-persona panel and found {count} {things} "
        f"worth a look. Want the one-page teaser?"
    )
    dm = (
        f"Hi there. I took an honest look at the {business} website ({site_url}) and "
        f"ran it past a panel of buyer personas, {count} {things} stood out that might "
        f"be costing you calls.\n\n"
        f"I can send a one-page teaser. If it's useful, I do a full {audit_name}"
        f"{audit_price} of the site you already have, no rebuild."
    )
    call_script = (
        f"- Hi, is this the owner of {business}?\n"
        f"- My name is {sender_name}. I run conversion audits for local businesses{where}.\n"
        f"- I took a look at your website and ran it past a panel of buyer personas.\n"
        f"- {count} specific {things} stood out that might be costing you calls.\n"
        f"- I can send a free one-page teaser. Would that be useful?"
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
    "build_teaser_messages",
    "normalize_phone",
    "gmail_compose_url",
    "sms_url",
    "tel_url",
    "facebook_url",
    "instagram_url",
]
