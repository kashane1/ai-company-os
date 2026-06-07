"""Ad-platform vertical eligibility (Agency layer).

Some verticals can't advertise on Google/Meta at all (firearms, tobacco, adult)
or only under certification/targeting limits (alcohol, gambling, high-risk
finance). Drafting a campaign for a banned vertical sells an un-runnable service —
your own gun-store demo is the live reminder. This module is the single source of
truth for "can this business run ads here?", checked before a draft is produced.

Levels:
* ``"banned"``     — not runnable on this platform (hard block → ``AdPolicyError``).
* ``"restricted"`` — runnable only with certification / targeting limits (warn;
  the operator must confirm eligibility before go-live).

Matching is keyword-substring against the client's ``service_category``. Keywords
are chosen to avoid false positives (e.g. never bare ``"bar"`` — it hits
``"barber"``).
"""

from __future__ import annotations

from dataclasses import dataclass

AD_PLATFORMS = ("google", "meta")


@dataclass(frozen=True)
class _VerticalRule:
    keywords: tuple[str, ...]
    google: str  # "banned" | "restricted" | ""
    meta: str
    reason: str


# Order matters only for which reason is reported first on overlap; keep specific
# (banned) verticals ahead of broader (restricted) ones.
_RULES: tuple[_VerticalRule, ...] = (
    _VerticalRule(
        ("firearm", "firearms", "gun store", "gun shop", "gun range", "shooting range",
         "ammo", "ammunition", "rifle", "pistol", "weapon"),
        google="banned", meta="banned",
        reason="firearms/ammunition ads are prohibited on Google and Meta",
    ),
    _VerticalRule(
        ("tobacco", "cigarette", "cigar shop", "vape", "vaping", "e-cigarette",
         "smoke shop", "hookah"),
        google="banned", meta="banned",
        reason="tobacco/vaping ads are prohibited on Google and Meta",
    ),
    _VerticalRule(
        ("cannabis", "marijuana", "dispensary", "cbd", "thc", "kratom"),
        google="banned", meta="banned",
        reason="cannabis/CBD ads are prohibited (recreational) on Google and Meta",
    ),
    _VerticalRule(
        ("adult", "escort", "strip club", "gentlemen's club"),
        google="banned", meta="banned",
        reason="adult-content ads are prohibited on Google and Meta",
    ),
    _VerticalRule(
        ("liquor store", "winery", "brewery", "distillery", "wine bar", "cocktail bar",
         "nightclub", "alcohol"),
        google="restricted", meta="restricted",
        reason="alcohol ads require targeting limits + platform certification",
    ),
    _VerticalRule(
        ("casino", "gambling", "sportsbook", "betting", "lottery", "poker room"),
        google="restricted", meta="restricted",
        reason="gambling ads require prior licensing/certification",
    ),
    _VerticalRule(
        ("payday", "crypto", "cryptocurrency", "forex", "binary options"),
        google="restricted", meta="restricted",
        reason="high-risk financial ads require certification",
    ),
    _VerticalRule(
        ("supplement", "nutraceutical", "pharmacy", "cbd oil"),
        google="restricted", meta="restricted",
        reason="healthcare/supplement ads are restricted and reviewed",
    ),
)


class AdPolicyError(ValueError):
    """A vertical that cannot advertise on the target platform."""


def check_ad_vertical(service_category: str, platform: str) -> tuple[str | None, str]:
    """Return ``(level, reason)`` for a vertical on a platform.

    ``level`` is ``"banned"``, ``"restricted"``, or ``None`` (no restriction).
    """
    cat = service_category.lower()
    plat = platform.lower()
    if plat not in AD_PLATFORMS:
        raise ValueError(f"unknown ad platform {platform!r}; expected one of {AD_PLATFORMS}")
    for rule in _RULES:
        if any(kw in cat for kw in rule.keywords):
            level = rule.google if plat == "google" else rule.meta
            if level:
                return level, rule.reason
    return None, ""


def assert_ad_vertical_allowed(service_category: str, platform: str) -> None:
    """Raise :class:`AdPolicyError` if the vertical is banned on the platform.

    A ``"restricted"`` vertical does NOT raise — it's runnable with certification;
    callers should surface :func:`check_ad_vertical`'s reason as a warning instead.
    """
    level, reason = check_ad_vertical(service_category, platform)
    if level == "banned":
        raise AdPolicyError(
            f"{service_category!r} cannot advertise on {platform}: {reason}"
        )
