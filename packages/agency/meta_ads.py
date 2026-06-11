"""Meta (Facebook/Instagram) Ads campaign draft (Agency layer — `meta_ads` service).

The Meta twin of :mod:`packages.agency.google_ads`. Turns a
:class:`~packages.agency.intake.ClientIntake` into a ``META_ADS.md`` the operator
reviews and builds in the client's Meta Ads Manager: a campaign objective,
audiences (geo + interest + lookalike + retargeting), creative variants (primary
text / headlines / descriptions within Meta's recommended limits), and placements.

Boundaries (identical to Google Ads):
* **Spend stays client-owned** — we draft and manage; the client owns the ad account.
* The draft is advisory. **Going live is gated** by the SAME
  ``packages.policies.agency_gates.assert_ad_campaign_go_live`` (mandatory daily +
  monthly budget cap, [D7], + the ``ad_campaign_go_live`` approval) — this module
  only drafts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.agency.intake import ClientIntake

# Meta recommended display limits (text truncates beyond these in most placements).
_PRIMARY_MAX = 125
_HEADLINE_MAX = 40
_DESCRIPTION_MAX = 30


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


@dataclass(frozen=True)
class Audience:
    name: str
    targeting: str


@dataclass(frozen=True)
class MetaAdsDraft:
    business_name: str
    service_category: str
    campaign_name: str
    objective: str
    geo_targets: tuple[str, ...]
    audiences: tuple[Audience, ...]
    placements: tuple[str, ...]
    primary_texts: tuple[str, ...]
    headlines: tuple[str, ...]
    descriptions: tuple[str, ...]
    landing_url: str
    daily_budget: float | None = None
    monthly_budget: float | None = None
    preflight_summary: str = ""
    conversion_lab_report_path: str = ""

    def to_markdown(self) -> str:
        budget = (
            f"${self.daily_budget:,.0f}/day · ${self.monthly_budget:,.0f}/mo"
            if self.daily_budget and self.monthly_budget
            else "_TBD — required before go-live (daily + monthly cap)_"
        )
        geo_lines = [f"- {g}" for g in self.geo_targets] or ["- _primary city_"]
        lines = [
            f"# Meta Ads Draft — {self.business_name}",
            "",
            "> **Draft for the operator.** The client owns the Meta ad account and the",
            "> ad spend; we build + manage. **Go-live is gated** and requires a daily +",
            "> monthly budget cap ([D7]).",
            "",
            f"**Campaign:** {self.campaign_name}",
            f"**Objective:** {self.objective}",
            f"**Budget cap:** {budget}",
            f"**Destination URL:** {self.landing_url}",
            "",
        ]
        if self.preflight_summary or self.conversion_lab_report_path:
            lines += [
                "## Conversion Lab Preflight",
                "",
                f"- Report: {self.conversion_lab_report_path or '_not linked_'}",
                f"- Recommended angle: {self.preflight_summary or '_none supplied_'}",
                "",
            ]
        lines += ["## Geo targeting", "", *geo_lines, "", "## Audiences", ""]
        for aud in self.audiences:
            lines.append(f"- **{aud.name}:** {aud.targeting}")
        lines += ["", "## Placements", ""]
        lines += [f"- {p}" for p in self.placements]
        lines += ["", "## Creative", "", f"**Primary text (≤{_PRIMARY_MAX} chars):**", ""]
        lines += [f"- {p}" for p in self.primary_texts]
        lines += ["", f"**Headlines (≤{_HEADLINE_MAX} chars):**", ""]
        lines += [f"- {h}" for h in self.headlines]
        lines += ["", f"**Descriptions (≤{_DESCRIPTION_MAX} chars):**", ""]
        lines += [f"- {d}" for d in self.descriptions]
        lines += [
            "",
            "## Go-live checklist",
            "",
            "- [ ] Client owns the Meta ad account + Page; we have Business Manager access",
            "- [ ] Daily + monthly budget cap set (gate refuses go-live without it)",
            "- [ ] Meta Pixel / Conversions API on the landing page",
            "- [ ] Lead form or destination URL tested",
            "- [ ] `ad_campaign_go_live` approval granted",
            "",
        ]
        return "\n".join(lines) + "\n"


def _audiences_for(category: str, geo: tuple[str, ...]) -> tuple[Audience, ...]:
    where = ", ".join(geo) if geo else "your service area"
    return (
        Audience(
            "Local prospecting",
            f"People in {where} (radius), age 25–65, interested in {category} / local services",
        ),
        Audience(
            "Lookalike",
            "1% lookalike of your past customers / leads (upload a customer list)",
        ),
        Audience(
            "Retargeting",
            "Website visitors + Page/Instagram engagers, last 30 days",
        ),
    )


def draft_meta_ads(
    intake: ClientIntake,
    *,
    daily_budget: float | None = None,
    monthly_budget: float | None = None,
    preflight_summary: str = "",
    conversion_lab_report_path: str = "",
) -> MetaAdsDraft:
    intake.validate()
    city = intake.city
    cat = intake.service_category
    geo = tuple(intake.service_area_cities or ([city] if city else []))

    primary_texts = tuple(
        _clip(t, _PRIMARY_MAX)
        for t in (
            f"Looking for {cat} in {city}? {intake.business_name} has you covered — "
            "free estimates, upfront pricing, licensed & insured.",
            f"{intake.business_name}: trusted local {cat}. Book online or call today for "
            "fast, friendly service.",
        )
    )
    headlines = tuple(
        _clip(h, _HEADLINE_MAX)
        for h in (
            f"{cat.title()} in {city}",
            "Free Estimates Today",
            "Licensed & Insured Local Pros",
            f"Top-Rated in {city}",
        )
    )
    descriptions = tuple(
        _clip(d, _DESCRIPTION_MAX)
        for d in ("Book online or call now", "Fast, upfront, reliable")
    )

    return MetaAdsDraft(
        business_name=intake.business_name,
        service_category=cat,
        campaign_name=f"{intake.business_name} — {city} Leads",
        objective="Leads",
        geo_targets=geo,
        audiences=_audiences_for(cat, geo),
        placements=("Facebook Feed", "Instagram Feed", "Stories", "Reels"),
        primary_texts=primary_texts,
        headlines=headlines,
        descriptions=descriptions,
        landing_url=intake.site_url,
        daily_budget=daily_budget,
        monthly_budget=monthly_budget,
        preflight_summary=preflight_summary,
        conversion_lab_report_path=conversion_lab_report_path,
    )


def emit_meta_ads_draft(
    intake: ClientIntake,
    docs_root: Path,
    *,
    daily_budget: float | None = None,
    monthly_budget: float | None = None,
    preflight_summary: str = "",
    conversion_lab_report_path: str = "",
) -> Path:
    """Write ``META_ADS.md`` into a client workspace and return its path."""
    docs_root.mkdir(parents=True, exist_ok=True)
    path = docs_root / "META_ADS.md"
    draft = draft_meta_ads(
        intake,
        daily_budget=daily_budget,
        monthly_budget=monthly_budget,
        preflight_summary=preflight_summary,
        conversion_lab_report_path=conversion_lab_report_path,
    )
    path.write_text(draft.to_markdown(), encoding="utf-8")
    return path
