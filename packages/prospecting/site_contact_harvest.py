"""Owned-site contact harvester (fix F1) — the pure, testable core.

Owned-site *teaser* prospects (item 7) are drafts-to-nowhere: only ~9 of 582
teaser rows carry a digital contact, so the validated teaser + audit pitch has
nowhere to land. These businesses publish their own contact details on their own
websites; this module extracts them so the dashboard can write them as contact
*overrides* (never source-record mutations) and the teaser rows become launchable.

Everything here is **pure and network-free**. The extraction functions take HTML
or already-captured text; the orchestrator :func:`harvest_site` takes an injected
``fetcher`` callable so tests pass a fake and never touch the network. The live
fetcher (robots, timeouts, polite delay, same-domain) lives in the CLI
(``scripts/prospecting/harvest_site_contacts.py``), not here.

Guardrails baked in:
- **Junk filtering.** Vendor/analytics noise (sentry, wix, godaddy, cloudflare),
  ``example.com``/``test`` placeholders, and image-filename false hits are dropped.
- **Overrides only.** :meth:`HarvestResult.best_overrides` maps strictly onto the
  three *digital* :data:`ALLOWED_OVERRIDE_FIELDS` (email, instagram, facebook). A
  detected contact *form* is reported but is **not** an override — it is not a
  channel the dashboard can launch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

# --------------------------------------------------------------------- emails
# Pragmatic address matcher. Deliberately not RFC-complete: it should catch the
# addresses a small business actually puts on its site and nothing exotic.
_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
)
_MAILTO_RE = re.compile(r"mailto:([^\"'>?\s]+)", re.IGNORECASE)

# Domains/substrings that mean "not the business's real inbox": analytics,
# CMS/host vendors, CDN/error reporters, and obvious placeholders. Matched as a
# substring against the lowercased address.
_EMAIL_JUNK_SUBSTRINGS = (
    "example.com",
    "example.org",
    "example.net",
    "test.com",
    "yourdomain",
    "domain.com",
    "email.com",
    "sentry",
    "wixpress",
    "wix.com",
    "godaddy",
    "secureserver.net",
    "cloudflare",
    "squarespace",
    "shopify",
    "wordpress.com",
    "googlemail-noreply",
    "no-reply@",
    "noreply@",
    "sentry.io",
    "@2x",
    "@3x",
)
# Image-filename false hits: an address whose *local part* ends in an image
# extension is really something like ``logo.png@2x`` or ``hero.jpg@…``.
_IMAGE_EXT_RE = re.compile(r"\.(png|jpe?g|gif|svg|webp|ico|bmp)$", re.IGNORECASE)


def _is_junk_email(addr: str) -> bool:
    low = addr.lower()
    if any(token in low for token in _EMAIL_JUNK_SUBSTRINGS):
        return True
    local = low.split("@", 1)[0]
    if _IMAGE_EXT_RE.search(local):
        return True
    # A bare dotted token with no real TLD-ish tail we already required via the
    # regex, but guard against a trailing punctuation slip.
    return False


def extract_emails(html: str) -> list[str]:
    """All plausible business emails in ``html``: ``mailto:`` targets first, then
    plain-text addresses. Lowercased, deduped (order-preserving), junk filtered."""
    text = html or ""
    found: list[str] = []
    for match in _MAILTO_RE.findall(text):
        found.append(match.split("?", 1)[0])
    found.extend(_EMAIL_RE.findall(text))
    out: list[str] = []
    seen: set[str] = set()
    for raw in found:
        addr = raw.strip().strip(".").lower()
        if not addr or "@" not in addr:
            continue
        if _is_junk_email(addr):
            continue
        if addr in seen:
            continue
        seen.add(addr)
        out.append(addr)
    return out


# -------------------------------------------------------------------- socials
# Intent / share / tracking URLs that are NOT a profile we can DM.
_SOCIAL_SKIP_SEGMENTS = (
    "share",
    "sharer",
    "sharer.php",
    "plugins",
    "plugin",
    "intent",
    "dialog",
    "tr",
    "home",
    "login",
    "policy",
    "help",
    "about",
    "p",
    "reel",
    "reels",
    "stories",
    "explore",
    "hashtag",
    "tags",
    "tagged",
    "pages",
    "groups",
    "events",
    "watch",
    "marketplace",
    "permalink.php",
    "profile.php",
)
_INSTAGRAM_RE = re.compile(
    r"(?:https?:)?//(?:www\.)?instagram\.com/([A-Za-z0-9._]+)", re.IGNORECASE
)
_FACEBOOK_RE = re.compile(
    r"(?:https?:)?//(?:www\.)?(?:facebook\.com|fb\.com|m\.facebook\.com)/([A-Za-z0-9.\-]+)",
    re.IGNORECASE,
)


def _first_social_handle(pattern: re.Pattern[str], html: str) -> str:
    for raw in pattern.findall(html or ""):
        handle = raw.strip().strip("/").lower()
        if not handle or "?" in handle or "=" in handle:
            continue
        if handle in _SOCIAL_SKIP_SEGMENTS:
            continue
        # A profile handle is a single path segment; share/plugin URLs carry more.
        if "/" in handle:
            continue
        return handle
    return ""


def extract_socials(html: str) -> dict[str, str]:
    """``{"instagram": handle, "facebook": handle}`` (canonical bare handles).

    Skips share/sharer/plugin/intent/tracking URLs — only real profile links
    yield a handle. Missing channel => empty string.
    """
    return {
        "instagram": _first_social_handle(_INSTAGRAM_RE, html),
        "facebook": _first_social_handle(_FACEBOOK_RE, html),
    }


# ----------------------------------------------------------------- contact form
_FORM_RE = re.compile(r"<form\b[^>]*>(.*?)</form>", re.IGNORECASE | re.DOTALL)
_EMAIL_FIELD_RE = re.compile(
    r"""(?:type\s*=\s*["']?email["']?)"""
    r"""|(?:name\s*=\s*["']?[^"'>]*(?:email|e-mail|message|comment|enquir|inquir)[^"'>]*["']?)"""
    r"""|(?:<textarea\b)""",
    re.IGNORECASE,
)


def has_contact_form(html: str) -> bool:
    """True if ``html`` has a ``<form>`` carrying an email-or-message field
    (``type=email``, a name/id mentioning email/message/enquiry, or a textarea)."""
    for body in _FORM_RE.findall(html or ""):
        if _EMAIL_FIELD_RE.search(body):
            return True
    return False


# ---------------------------------------------------------------- link discovery
_CONTACT_HINTS = ("contact", "about", "reach", "get-in-touch", "connect")
_HREF_RE = re.compile(
    r"<a\b[^>]*?href\s*=\s*[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_www(host: str) -> str:
    # Prefix strip, NOT str.lstrip (which would strip any leading w/./ chars and
    # mangle hosts like "wow.com" -> "ow.com").
    return host[4:] if host.startswith("www.") else host


def _same_domain(base_url: str, candidate: str) -> bool:
    base = urlparse(base_url)
    cand = urlparse(candidate)
    if not cand.netloc:
        return True  # relative link -> same domain
    return _strip_www(base.netloc.lower()) == _strip_www(cand.netloc.lower())


def discover_contact_links(html: str, base_url: str) -> list[str]:
    """Up to 2 SAME-DOMAIN absolute URLs whose path or anchor text looks like a
    contact/about page. Order-preserving, deduped, homepage itself excluded."""
    out: list[str] = []
    seen: set[str] = set()
    base_norm = base_url.rstrip("/")
    for href, anchor in _HREF_RE.findall(html or ""):
        href = href.strip()
        if not href or href.lower().startswith(("mailto:", "tel:", "javascript:")):
            continue
        anchor_text = _TAG_RE.sub(" ", anchor).strip().lower()
        path_hint = href.lower()
        if not any(h in path_hint or h in anchor_text for h in _CONTACT_HINTS):
            continue
        absolute = urljoin(base_url if base_url.endswith("/") else base_url + "/", href)
        absolute = absolute.split("#", 1)[0].rstrip("/")
        if not _same_domain(base_url, absolute):
            continue
        if absolute == base_norm or not absolute:
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        out.append(absolute)
        if len(out) >= 2:
            break
    return out


# ---------------------------------------------------------------------- result
@dataclass
class HarvestResult:
    """Aggregated harvest for one site. ``emails`` is ordered best-first (the
    first is what :meth:`best_overrides` proposes)."""

    emails: list[str] = field(default_factory=list)
    instagram: str = ""
    facebook: str = ""
    has_form: bool = False
    pages_fetched: int = 0

    @property
    def best_email(self) -> str:
        return self.emails[0] if self.emails else ""

    def has_any(self) -> bool:
        return bool(self.emails or self.instagram or self.facebook or self.has_form)

    def best_overrides(self) -> dict[str, str]:
        """The harvested hits as dashboard contact overrides.

        Maps only onto the three *digital* override fields the dashboard launches:
        ``contact_email``, ``contact_instagram``, ``contact_facebook``. A contact
        *form* is intentionally absent — it is logged for triage, not a launchable
        channel, so it is never written as an override.
        """
        out: dict[str, str] = {}
        if self.best_email:
            out["contact_email"] = self.best_email
        if self.instagram:
            out["contact_instagram"] = self.instagram
        if self.facebook:
            out["contact_facebook"] = self.facebook
        return out


def harvest_from_html(htmls: list[str]) -> HarvestResult:
    """Aggregate extraction across one or more page HTMLs (homepage + contact
    pages). Order matters: earlier pages win the social/best-email slot."""
    result = HarvestResult()
    seen_emails: set[str] = set()
    for page in htmls:
        for addr in extract_emails(page):
            if addr not in seen_emails:
                seen_emails.add(addr)
                result.emails.append(addr)
        socials = extract_socials(page)
        if not result.instagram and socials["instagram"]:
            result.instagram = socials["instagram"]
        if not result.facebook and socials["facebook"]:
            result.facebook = socials["facebook"]
        if not result.has_form and has_contact_form(page):
            result.has_form = True
    return result


# ------------------------------------------------------------------ orchestrator
def harvest_site(
    prospect: object,
    *,
    fetcher,
    max_pages: int = 3,
    captured_home: str | None = None,
) -> HarvestResult:
    """Harvest one prospect's own site.

    ``prospect`` must expose ``site_url`` (a :class:`TeaserProspect` does). The
    homepage is the ``captured_home`` text when provided (no fetch — used for the
    580+ already-captured ``homepage.txt`` files, ZERO network), otherwise it is
    fetched via the injected ``fetcher`` callable ``(url) -> str | None``.

    When the homepage is captured (visible text, no markup) no contact-page links
    can be discovered, so no further fetches happen. When the homepage is fetched
    live, up to 2 discovered same-domain contact/about pages are fetched as well,
    capped at ``max_pages`` total.
    """
    base_url = str(getattr(prospect, "site_url", "") or "").strip()
    pages: list[str] = []
    pages_fetched = 0

    if captured_home is not None:
        pages.append(captured_home)
        # Captured homepage is rendered text — no <a href> markup to walk, so we
        # cannot (and do not) discover or fetch contact pages.
    else:
        if not base_url:
            return HarvestResult()
        home = fetcher(base_url)
        pages_fetched += 1
        if home:
            pages.append(home)
            for link in discover_contact_links(home, base_url):
                if pages_fetched >= max_pages:
                    break
                page = fetcher(link)
                pages_fetched += 1
                if page:
                    pages.append(page)

    result = harvest_from_html(pages)
    result.pages_fetched = pages_fetched if captured_home is None else 0
    return result


__all__ = [
    "HarvestResult",
    "extract_emails",
    "extract_socials",
    "has_contact_form",
    "discover_contact_links",
    "harvest_from_html",
    "harvest_site",
]
