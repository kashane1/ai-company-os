"""social-post-safety — pure-Python validator skill.

Fails closed: any exception inside ``run`` becomes
``{"verdict": "fail", "reasons": ["exception: ..."]}``.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

FTC_MARKERS = ("#ad", "#sponsored", "#paidpartnership", "paid partnership")

PROFANITY = {"fuck", "shit", "bitch", "asshole"}  # conservative; tune later

TLD_ALLOWLIST = {
    "com",
    "org",
    "net",
    "io",
    "app",
    "co",
    "us",
}

# Platform character limits (soft warnings, not hard fails — Premium tiers may differ).
PLATFORM_CHAR_LIMITS: dict[str, int] = {
    "x": 280,
    "threads": 500,
    "instagram": 2200,
    "tiktok": 4000,
    "facebook": 63206,
}

# Allowed @mentions — add product handles here.
MENTION_ALLOWLIST = {"catchbookapp"}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
MENTION_RE = re.compile(r"@([A-Za-z0-9_]+)")
CASHTAG_RE = re.compile(r"\$([A-Za-z][A-Za-z0-9]+)")


def _check_ftc(draft: str, campaign: dict) -> list[str]:
    if not campaign.get("paid"):
        return []
    lower = draft.lower()
    if any(marker in lower for marker in FTC_MARKERS):
        return []
    return ["ftc_disclosure_missing"]


def _check_platform_tos(draft: str, platform: str, campaign: dict) -> list[str]:
    reasons: list[str] = []
    if platform == "instagram" and campaign.get("paid"):
        if "#paidpartnership" not in draft.lower():
            reasons.append("instagram_paid_partnership_tag_missing")
    if platform == "tiktok" and campaign.get("affiliate"):
        if "#ad" not in draft.lower():
            reasons.append("tiktok_affiliate_disclosure_missing")
    return reasons


def _check_links(links: list[str]) -> list[str]:
    reasons: list[str] = []
    for url in links:
        try:
            parsed = urlparse(url)
        except Exception:
            reasons.append(f"malformed_url:{url}")
            continue
        if parsed.scheme not in ("http", "https"):
            reasons.append(f"bad_scheme:{url}")
            continue
        host = parsed.hostname or ""
        if "." not in host:
            reasons.append(f"no_tld:{url}")
            continue
        tld = host.rsplit(".", 1)[-1]
        if tld not in TLD_ALLOWLIST:
            reasons.append(f"disallowed_tld:{url}")
    return reasons


def _check_profanity(draft: str) -> list[str]:
    lower = draft.lower()
    for word in PROFANITY:
        if re.search(rf"\b{re.escape(word)}\b", lower):
            return [f"profanity:{word}"]
    return []


def _check_pii(draft: str) -> list[str]:
    reasons: list[str] = []
    if EMAIL_RE.search(draft):
        reasons.append("pii_email")
    if PHONE_RE.search(draft):
        reasons.append("pii_phone")
    return reasons


def _check_mentions(draft: str) -> list[str]:
    """Flag @mentions and $cashtags that aren't in the allowlist."""
    reasons: list[str] = []
    for match in MENTION_RE.finditer(draft):
        handle = match.group(1).lower()
        if handle not in MENTION_ALLOWLIST:
            reasons.append(f"unvetted_mention:@{handle}")
    for match in CASHTAG_RE.finditer(draft):
        reasons.append(f"unvetted_cashtag:${match.group(1)}")
    return reasons


def _check_char_limit(draft: str, platform: str) -> list[str]:
    """Warn if draft exceeds platform character limit (soft warning)."""
    limit = PLATFORM_CHAR_LIMITS.get(platform)
    if limit and len(draft) > limit:
        return [f"char_limit_warning:{platform}:{len(draft)}/{limit}"]
    return []


def _normalize_unicode(text: str) -> str:
    """NFKC-normalize to defeat homoglyph evasion of profanity/PII checks."""
    return unicodedata.normalize("NFKC", text)


def run(payload: dict) -> dict:
    try:
        raw_draft = str(payload.get("draft", ""))
        platform = str(payload.get("platform", "")).lower()
        campaign = payload.get("campaign") or {}
        links = list(payload.get("links") or [])

        # Normalize Unicode before running text checks (defeats homoglyph evasion).
        draft = _normalize_unicode(raw_draft)

        reasons: list[str] = []
        reasons.extend(_check_ftc(draft, campaign))
        reasons.extend(_check_platform_tos(draft, platform, campaign))
        reasons.extend(_check_links(links))
        reasons.extend(_check_profanity(draft))
        reasons.extend(_check_pii(draft))
        reasons.extend(_check_mentions(draft))
        reasons.extend(_check_char_limit(draft, platform))

        return {"verdict": "fail" if reasons else "pass", "reasons": reasons}
    except Exception as exc:  # pragma: no cover - defensive fail-closed
        return {"verdict": "fail", "reasons": [f"exception:{type(exc).__name__}:{exc}"]}
