"""Per-prospect outreach copy generation (Agency layer).

Turns a verified prospect record that already has a built preview site
(``mockup_url``) into ready-to-send, channel-appropriate, genre-specific
outreach drafts. Composes the editable template library under
``state/prospects/outreach/``. Nothing here sends, and outputs never contain
first-person send claims (the GTM lane forbids them).

The pipeline:

    record (+ mockup_url)
      → gap_ref (by verdict + genre)            this module
      → {observed_gap, hook} from genre-snippets.md
      → fill SMS / call / email-with-mockup / DM templates with real data
      → one outreach.md per prospect + a consolidated index row
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from packages.agency.prospect_site import GENRE_PROFILES, city_label

# genre_id → snippet section key in genre-snippets.md (used for none_found leads).
_GENRE_GAP_REF = {
    "auto_repair": "auto_repair",
    "barber_shop": "salon_nails",
    "beauty_salon": "salon_nails",
    "nail_salon": "salon_nails",
    "massage_therapy": "appointment_service",
    "bakery": "cafe",
    "coffee_shop": "cafe",
}

_SEARCH_PHRASES = {
    "accountant": "tax and accounting help",
    "auto_repair": "auto shops",
    "bakery": "bakeries",
    "barber_shop": "barbershops",
    "beauty_salon": "hair salons",
    "coffee_shop": "coffee shops",
    "electrician": "electricians",
    "garage_door": "garage door companies",
    "landscaper": "landscapers",
    "massage_therapy": "massage studios",
    "nail_salon": "nail salons",
    "notary": "notaries",
    "roofer": "roofers",
}

# Short, SMS-friendly gap phrasing keyed by gap_ref (the long observed_gap is too
# verbose for a text). Kept here (not in markdown) so it's testable.
_SHORT_GAP = {
    "auto_repair": "there's no website where someone can see your hours/services and just tap to call",
    "salon_nails": "there's no website showing your work and an easy way to book or call",
    "appointment_service": "there's no simple site that makes it easy for new clients to find and book you",
    "cafe": "there's no website with your menu, hours, and location",
    "marketplace_only": "your main web presence looks like a booking or listing page, not a simple site you own",
    "generic": "there's no website where a new customer can see what you offer and how to reach you",
}

FORBIDDEN_OUTREACH_MARKS = ("—",)


def gap_ref_for(record: dict) -> str:
    """Pick the snippet section for a record.

    A ``marketplace_only`` lead's pain is "only a listing/booking page"; a
    ``none_found`` lead's pain is genre-specific ("no website at all").
    """
    if record.get("web_verify_verdict") == "marketplace_only":
        return "marketplace_only"
    return _GENRE_GAP_REF.get(str(record.get("genre_id", "")), "generic")


def genre_noun(record: dict) -> str:
    profile = GENRE_PROFILES.get(str(record.get("genre_id", "")))
    return profile.category if profile else "local business"


def search_phrase(record: dict) -> str:
    return _SEARCH_PHRASES.get(str(record.get("genre_id", "")), "local businesses")


def parse_snippets(text: str) -> dict[str, dict[str, str]]:
    """Parse genre-snippets.md into ``{section_key: {observed_gap, hook}}``.

    Section keys are taken from the leading token of each ``## heading`` (e.g.
    ``## salon_nails  (nail / beauty / barber)`` → ``salon_nails``). Values may
    span multiple wrapped lines (indented continuations). These are joined into
    one string. Surrounding quotes and markdown ``*emphasis*`` are stripped so
    the text drops cleanly into a plain-text email/SMS.
    """
    out: dict[str, dict[str, str]] = {}
    current: str | None = None
    key: str | None = None
    buf: list[str] = []

    def flush() -> None:
        if current and key:
            value = " ".join(s.strip() for s in buf).strip().strip('"').replace("*", "")
            out[current][key] = re.sub(r"\s+", " ", value)

    for line in text.splitlines():
        h = re.match(r"^##\s+(\S+)", line)
        if h:
            flush()
            key, buf[:] = None, []
            current = h.group(1)
            out[current] = {}
            continue
        if current is None:
            continue
        m = re.match(r"^\s*-\s*\*\*(observed_gap|hook):\*\*\s*(.*)$", line)
        if m:
            flush()
            key = m.group(1)
            buf = [m.group(2)]
        elif key and line.strip() and not line.lstrip().startswith("-"):
            buf.append(line)  # wrapped continuation of the current value
        elif not line.strip():
            flush()
            key, buf = None, []
    flush()
    return out


@dataclass(frozen=True)
class OutreachContext:
    business_name: str
    owner_name: str
    neighborhood: str
    city: str
    genre_noun: str
    search_phrase: str
    observed_gap: str
    observed_gap_short: str
    hook: str
    review_count: str
    review_phrase: str
    mockup_url: str
    email: str = ""
    instagram: str = ""
    facebook: str = ""
    booking_url: str = ""
    owned_website: str = ""
    sender_name: str = "[your name]"
    sender_company: str = "[your company]"

    def as_placeholders(self) -> dict[str, str]:
        return {
            "{business_name}": self.business_name,
            "{owner_name}": self.owner_name,
            "{neighborhood}": self.neighborhood,
            "{city}": self.city,
            "{genre_noun}": self.genre_noun,
            "{search_phrase}": self.search_phrase,
            "{observed_gap}": self.observed_gap,
            "{observed_gap_short}": self.observed_gap_short,
            "{hook}": self.hook,
            "{review_count}": self.review_count,
            "{review_phrase}": self.review_phrase,
            "{mockup_url}": self.mockup_url,
            "{sender_name}": self.sender_name,
            "{sender_company}": self.sender_company,
        }


def context_for(record: dict, snippets: dict[str, dict[str, str]]) -> OutreachContext:
    ref = gap_ref_for(record)
    snip = snippets.get(ref, snippets.get("generic", {}))
    city = city_label(str(record.get("city_id", "")))
    reviews = record.get("user_ratings_total")
    review_count = int(reviews or 0)
    ctx = OutreachContext(
        business_name=str(record.get("display_name", "")),
        owner_name="there",
        neighborhood=city,
        city=city,
        genre_noun=genre_noun(record),
        search_phrase=search_phrase(record),
        observed_gap=snip.get("observed_gap", _SHORT_GAP["generic"]),
        observed_gap_short=_SHORT_GAP.get(ref, _SHORT_GAP["generic"]),
        hook=snip.get("hook", ""),
        review_count=f"{reviews}" if reviews else "your",
        review_phrase=review_phrase(review_count),
        mockup_url=str(record.get("mockup_url", "")),
        email=str(record.get("contact_email", "")),
        instagram=str(record.get("contact_instagram", "")),
        facebook=str(record.get("contact_facebook", "")),
        booking_url=str(record.get("contact_booking_url", "")),
        owned_website=str(record.get("contact_owned_website", "")),
    )
    # Resolve placeholder-in-snippet (snippets themselves contain {business_name} etc.)
    repl = ctx.as_placeholders()
    return OutreachContext(
        **{
            **ctx.__dict__,
            "observed_gap": _fill(ctx.observed_gap, repl),
            "hook": _fill(ctx.hook, repl),
        }
    )


def _fill(text: str, repl: dict[str, str]) -> str:
    for k, v in repl.items():
        text = text.replace(k, v)
    return sanitize_outreach_copy(text)


def review_phrase(review_count: int) -> str:
    if review_count >= 300:
        return "a lot of strong reviews"
    if review_count >= 75:
        return "a strong review profile"
    if review_count > 0:
        return "good reviews"
    return "a good local reputation"


def sanitize_outreach_copy(text: str) -> str:
    """Remove punctuation that makes outreach read machine-written."""
    return re.sub(r"\s*—\s*", ", ", text)


def recommended_channel(record: dict) -> str:
    """Best first-touch channel given what contact info we now have.

    Order: a confirmed owned site means recheck (don't pitch "no website"); else
    prefer email, then Instagram, then Facebook DM, then SMS/call on the phone,
    else we still need a contact.
    """
    if str(record.get("contact_owned_website", "")).strip():
        return "recheck_has_site"
    if str(record.get("contact_email", "")).strip():
        return "email"
    if str(record.get("contact_instagram", "")).strip():
        return "instagram_dm"
    if str(record.get("contact_facebook", "")).strip():
        return "facebook_dm"
    if record.get("phone"):
        return "sms_or_call"
    return "needs_contact"


def render_template(template_body: str, ctx: OutreachContext) -> str:
    return _fill(template_body, ctx.as_placeholders())


def unfilled_placeholders(text: str) -> list[str]:
    """Known business placeholders still present (sender_* are intentionally left)."""
    keep = {"{sender_name}", "{sender_company}"}
    return sorted({m.group(0) for m in re.finditer(r"\{[a-z_]+\}", text)} - keep)


@dataclass
class OutreachBundle:
    record: dict
    context: OutreachContext
    channel: str
    sections: dict[str, str] = field(default_factory=dict)  # channel -> filled copy
