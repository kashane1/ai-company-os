"""Promotional landing page (Agency layer, G4 — Package C service).

A single-purpose campaign page (e.g. ``summer.joesplumbing.com``) built by reusing
the existing web scaffold rather than forking a template: a :class:`PromoCampaign`
becomes a token context fed to ``render_landing_html``, so the page inherits the
design system and the contact form, with the hero/CTA reframed around one offer.

Offline + no Node (peer of :mod:`packages.agency.local_seo`): render to a string
with a token guard, or emit a ``dist/index.html`` ready to deploy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.web.scaffold import default_context, render_landing_html, unfilled_tokens


@dataclass(frozen=True)
class PromoCampaign:
    business_name: str
    offer_headline: str  # the one thing the page sells, e.g. "20% off your first service"
    offer_detail: str = ""
    cta_label: str = "Claim this offer"
    city: str = ""
    service_category: str = ""
    expiry: str = ""  # e.g. "Offer ends June 30" — becomes the urgency note
    site_url: str = "https://example.com"

    def validate(self) -> None:
        if not self.business_name.strip():
            raise ValueError("promo: business_name is required")
        if not self.offer_headline.strip():
            raise ValueError("promo: offer_headline is required")


def promo_context(campaign: PromoCampaign) -> dict[str, str]:
    """Build the scaffold token context for a single-offer campaign page."""
    campaign.validate()
    context = default_context(campaign.business_name, site_url=campaign.site_url)

    where = f" in {campaign.city}" if campaign.city else ""
    detail = campaign.offer_detail or (
        f"A limited-time offer from {campaign.business_name}{where}. "
        "Reserve your spot before it's gone."
    )
    note = campaign.expiry or "Limited-time offer"
    eyebrow = "Limited-time offer" + (f" · {campaign.city}" if campaign.city else "")

    context.update(
        {
            "META_DESCRIPTION": f"{campaign.offer_headline} — {campaign.business_name}.",
            "EYEBROW": eyebrow,
            "HERO_HEADLINE": campaign.offer_headline,
            "HERO_SUBHEAD": detail,
            "PRIMARY_CTA": campaign.cta_label,
            "SECONDARY_CTA": "Learn more",
            "HERO_NOTE": note,
            "FEATURES_HEADLINE": f"Why {campaign.business_name}",
            "CTA_HEADLINE": campaign.offer_headline,
            "CTA_SUBHEAD": f"{campaign.cta_label} — {note.lower()}.",
        }
    )
    return context


def render_promo_html(campaign: PromoCampaign) -> str:
    """Render the campaign page to a self-contained HTML string (render-guarded)."""
    html = render_landing_html(promo_context(campaign))
    leftover = unfilled_tokens(html)
    if leftover:  # never ship a page with visible {{TOKENS}}
        raise ValueError(f"unfilled promo tokens: {leftover}")
    return html


def emit_promo_page(campaign: PromoCampaign, out_dir: Path) -> Path:
    """Write the campaign page to ``out_dir/dist/index.html`` and return its path."""
    dist = out_dir / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    index = dist / "index.html"
    index.write_text(render_promo_html(campaign), encoding="utf-8")
    return index
