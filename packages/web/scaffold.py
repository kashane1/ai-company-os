"""Web scaffold — materialize an Astro static-first landing site (F3).

The WEB lane seeds a new web product from a template under
``packages/web/scaffold/<template>/`` and fills in product-specific copy. Codex
then edits the result; the web gate (``packages/web/validation.py``) checks the
build output.

**Scope:** paid **client sites** (``products/<slug>-site/``, agency Phase 4) and
product validation experiments — **not** customer-facing prospect mockups. Those
use ``docs/demo-site-build-playbook.md`` (``dist-v2/``). The offline
:func:`render_landing_html` path is legacy token-fill for ``--legacy-build`` /
tests only.

Two entry points:

* :func:`scaffold_site` writes the full project into a target directory, with
  every ``{{TOKEN}}`` replaced from a context dict — a ready-to-build Astro
  project.
* :func:`render_landing_html` produces the landing page as a single
  self-contained HTML string (CSS inlined), so the platform can preview and
  validate the design **offline, without Node** — the same markup Astro emits
  for the static page.

Defaults are intentionally professional and conversion-oriented so a scaffold is
presentable on day one; the scaffold is the floor, not the ceiling.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parent / "scaffold"
DEFAULT_TEMPLATE = "astro-landing"

# Files we token-substitute (text). Anything else is copied verbatim.
_TEXT_SUFFIXES = {
    ".astro", ".css", ".js", ".mjs", ".ts", ".json", ".md", ".html", ".txt", ".gitignore",
}

_TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "web-product"


def default_context(
    site_name: str,
    *,
    tagline: str = "The faster way to get it done",
    audience: str = "teams",
    site_url: str = "https://example.com",
) -> dict[str, str]:
    """A complete, presentable default context. Every token the template uses
    has a sensible value, so a scaffold renders cleanly before any editing."""
    return {
        "SITE_NAME": site_name,
        "PACKAGE_NAME": _slug(site_name),
        "SITE_URL": site_url,
        "TAGLINE": tagline,
        "META_DESCRIPTION": f"{site_name} helps {audience} {tagline.lower()}.",
        "EYEBROW": "Now in early access",
        "HERO_HEADLINE": tagline,
        "HERO_SUBHEAD": f"{site_name} gives {audience} a simpler, faster way to work — "
        "set up in minutes, no busywork.",
        "PRIMARY_CTA": "Get early access",
        "SECONDARY_CTA": "See how it works",
        "HERO_NOTE": "No credit card required · Cancel anytime",
        "TRUST_LABEL": "Trusted by teams who ship",
        "TRUST_1": "Northwind", "TRUST_2": "Lumen", "TRUST_3": "Cedar", "TRUST_4": "Halcyon",
        "FEATURES_HEADLINE": "Everything you need, nothing you don't",
        "FEATURES_SUBHEAD": "Thoughtfully designed to remove friction so you can focus "
        "on the work that matters.",
        "FEATURE_1_TITLE": "Fast by default",
        "FEATURE_1_BODY": "Up and running in minutes with sensible defaults — no setup marathon.",
        "FEATURE_2_TITLE": "Built for focus",
        "FEATURE_2_BODY": "A clean, intuitive interface that stays out of your way.",
        "FEATURE_3_TITLE": "Private and secure",
        "FEATURE_3_BODY": "Your data stays yours, with security built in from the start.",
        "HOW_HEADLINE": "Three steps to value",
        "STEP_1_TITLE": "Sign up", "STEP_1_BODY": "Create your account in under a minute.",
        "STEP_2_TITLE": "Connect", "STEP_2_BODY": "Bring in your work and we handle the rest.",
        "STEP_3_TITLE": "Ship", "STEP_3_BODY": "See results the same day you start.",
        "TESTIMONIAL": "It paid for itself in the first week.",
        "TESTIMONIAL_AUTHOR": "— An early customer",
        "CTA_HEADLINE": "Be first to try it",
        "CTA_SUBHEAD": "Join the early-access list and we'll reach out as soon as your spot opens.",
        "FAQ_HEADLINE": "Frequently asked questions",
        "FAQ_1_Q": f"What is {site_name}?",
        "FAQ_1_A": f"{site_name} is the simplest way for {audience} to {tagline.lower()}.",
        "FAQ_2_Q": "How much does it cost?",
        "FAQ_2_A": "Early access is free. Paid plans arrive at launch — early users "
        "get the best price.",
        "FAQ_3_Q": "When can I start?",
        "FAQ_3_A": "Join the list above and we'll send your invite as soon as a spot opens.",
        "YEAR": str(datetime.now(timezone.utc).year),
        "FOOTER_NOTE": "Made with care.",
        # Stripe monetization (F8) — replace with the real Price ID at launch.
        "STRIPE_PRICE_ID": "price_replace_me",
    }


def local_business_context(
    business_name: str,
    *,
    service_category: str,
    city: str,
    services: list[str] | None = None,
    phone: str = "",
    tagline: str | None = None,
    site_url: str = "https://example.com",
) -> dict[str, str]:
    """A scaffold context tuned for a local-SMB client site (Agency layer).

    Starts from :func:`default_context` and overrides the SaaS-flavored copy with
    local-business framing keyed off ``service_category`` and ``city`` (e.g. a
    plumber in Seattle). The result is the same token dict ``scaffold_site``
    consumes, so the existing template renders without forking.
    """
    services = services or []
    tagline = tagline or f"Trusted {service_category} in {city}"
    audience = f"{city} homeowners and businesses"
    context = default_context(business_name, tagline=tagline, audience=audience, site_url=site_url)

    primary = f"Call {phone}" if phone else "Get a free quote"
    service_line = ", ".join(services[:3]) if services else service_category
    context.update(
        {
            "EYEBROW": f"{service_category.title()} · {city}",
            "HERO_HEADLINE": tagline,
            "HERO_SUBHEAD": (
                f"{business_name} provides reliable {service_category} for {city}. "
                f"{service_line.capitalize()} — done right, on time."
            ),
            "PRIMARY_CTA": primary,
            "SECONDARY_CTA": "See our services",
            "HERO_NOTE": "Licensed & insured · Free estimates",
            "TRUST_LABEL": f"Proudly serving {city}",
            "FEATURES_HEADLINE": "Why choose us",
            "FEATURES_SUBHEAD": f"Local, dependable {service_category} you can count on.",
            "FEATURE_1_TITLE": "Local & reliable",
            "FEATURE_1_BODY": f"Based in {city} — we show up on time and do the job right.",
            "FEATURE_2_TITLE": "Upfront pricing",
            "FEATURE_2_BODY": "Clear estimates, no surprises.",
            "FEATURE_3_TITLE": "Satisfaction first",
            "FEATURE_3_BODY": "We're not done until you're happy with the work.",
            "CTA_HEADLINE": f"Need {service_category} in {city}?",
            "CTA_SUBHEAD": "Reach out today for a fast, free estimate.",
            "FAQ_1_Q": "What areas do you serve?",
            "FAQ_1_A": f"{business_name} serves {city} and the surrounding area.",
            "FAQ_2_Q": "How do I get a quote?",
            "FAQ_2_A": primary + " or use the contact form on this page.",
        }
    )
    return context


def _substitute(text: str, context: dict[str, str]) -> str:
    return _TOKEN_RE.sub(lambda m: str(context.get(m.group(1), m.group(0))), text)


def unfilled_tokens(text: str) -> list[str]:
    """Token names still present in ``text`` (useful as a render guard)."""
    return sorted(set(_TOKEN_RE.findall(text)))


def scaffold_site(
    target_dir: Path,
    context: dict[str, str],
    *,
    template: str = DEFAULT_TEMPLATE,
) -> list[Path]:
    """Copy ``template`` into ``target_dir``, substituting tokens in text files.

    Returns the list of files written. Raises if the template is unknown.
    """
    template_root = TEMPLATES_ROOT / template
    if not template_root.is_dir():
        raise FileNotFoundError(f"unknown web template: {template}")

    written: list[Path] = []
    for src in sorted(template_root.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(template_root)
        dest = target_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in _TEXT_SUFFIXES or src.name == ".gitignore":
            content = _substitute(src.read_text(encoding="utf-8"), context)
            dest.write_text(content, encoding="utf-8")
        else:
            dest.write_bytes(src.read_bytes())
        written.append(dest)
    return written


def render_landing_html(
    context: dict[str, str],
    *,
    template: str = DEFAULT_TEMPLATE,
) -> str:
    """Render the landing page to a single self-contained HTML string.

    Strips the Astro frontmatter and inlines ``global.css`` so the result is a
    faithful, offline-renderable preview that the web gate can validate — no
    Node required.
    """
    template_root = TEMPLATES_ROOT / template
    page = (template_root / "src" / "pages" / "index.astro").read_text(encoding="utf-8")
    css = (template_root / "src" / "styles" / "global.css").read_text(encoding="utf-8")

    page = _FRONTMATTER_RE.sub("", page, count=1)
    style_block = f"<style>\n{css}\n</style>"
    if "</head>" in page:
        page = page.replace("</head>", f"  {style_block}\n</head>", 1)
    else:  # pragma: no cover - template always has a head
        page = style_block + page
    return _substitute(page, context)
