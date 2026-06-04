"""Google Ads campaign draft (Agency layer, G8 — Package C service).

Turns a :class:`~packages.agency.intake.ClientIntake` into an ``ADS.md`` the
operator reviews and builds in the client's Google Ads account: campaign +
ad-group structure, keyword themes (service × geo), a standard negative list, a
Responsive Search Ad (headlines/descriptions within Google's character limits),
and geo targeting from the service area.

Boundaries:
* **Spend stays client-owned** — we draft and manage; the client owns the account.
* The draft is advisory. **Going live is gated** by
  ``packages.policies.agency_gates.assert_ad_campaign_go_live`` with a mandatory
  daily + monthly budget cap ([D7]) — this module only drafts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.agency.intake import ClientIntake

# Google Ads Responsive Search Ad limits.
_HEADLINE_MAX = 30
_DESCRIPTION_MAX = 90

# Intent-poisoning terms a local service almost never wants to pay for.
_DEFAULT_NEGATIVES = (
    "free", "diy", "how to", "jobs", "salary", "training", "course",
    "wholesale", "used", "cheap", "near me jobs",
)


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


@dataclass(frozen=True)
class AdGroup:
    name: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class AdsDraft:
    business_name: str
    service_category: str
    campaign_name: str
    geo_targets: tuple[str, ...]
    ad_groups: tuple[AdGroup, ...]
    negative_keywords: tuple[str, ...]
    headlines: tuple[str, ...]
    descriptions: tuple[str, ...]
    landing_url: str
    daily_budget: float | None = None
    monthly_budget: float | None = None

    def to_markdown(self) -> str:
        budget = (
            f"${self.daily_budget:,.0f}/day · ${self.monthly_budget:,.0f}/mo"
            if self.daily_budget and self.monthly_budget
            else "_TBD — required before go-live (daily + monthly cap)_"
        )
        geo_lines = [f"- {g}" for g in self.geo_targets] or ["- _primary city_"]
        lines = [
            f"# Google Ads Draft — {self.business_name}",
            "",
            "> **Draft for the operator.** The client owns the Google Ads account and",
            "> the ad spend; we build + manage. **Go-live is gated** and requires a",
            "> daily + monthly budget cap ([D7]).",
            "",
            f"**Campaign:** {self.campaign_name}",
            f"**Budget cap:** {budget}",
            f"**Final URL:** {self.landing_url}",
            "",
            "## Geo targeting",
            "",
            *geo_lines,
            "",
            "## Ad groups & keywords",
            "",
        ]
        for group in self.ad_groups:
            lines.append(f"### {group.name}")
            lines.append("")
            lines += [f'- "{kw}"' for kw in group.keywords]  # phrase match
            lines.append("")
        lines += ["## Negative keywords", ""]
        lines += [f"- {n}" for n in self.negative_keywords]
        lines += ["", "## Responsive Search Ad", "", "**Headlines (≤30 chars):**", ""]
        lines += [f"- {h}" for h in self.headlines]
        lines += ["", "**Descriptions (≤90 chars):**", ""]
        lines += [f"- {d}" for d in self.descriptions]
        lines += [
            "",
            "## Go-live checklist",
            "",
            "- [ ] Client owns the Ads account; we have manager access",
            "- [ ] Daily + monthly budget cap set (gate refuses go-live without it)",
            "- [ ] Conversion tracking on the landing page",
            "- [ ] `ad_campaign_go_live` approval granted",
            "",
        ]
        return "\n".join(lines) + "\n"


def _keywords_for(service: str, city: str) -> tuple[str, ...]:
    s = service.lower()
    base = [f"{s} {city}", f"{s} near me", f"best {s} {city}", f"{s} cost", f"emergency {s} {city}"]
    return tuple(dict.fromkeys(k.strip() for k in base if k.strip()))  # dedupe, keep order


def draft_google_ads(
    intake: ClientIntake,
    *,
    daily_budget: float | None = None,
    monthly_budget: float | None = None,
) -> AdsDraft:
    intake.validate()
    city = intake.city
    services = intake.services or [intake.service_category]
    geo = tuple(intake.service_area_cities or ([city] if city else []))

    ad_groups = tuple(
        AdGroup(name=service.title(), keywords=_keywords_for(service, city)) for service in services
    )

    cat = intake.service_category
    headlines = tuple(
        _clip(h, _HEADLINE_MAX)
        for h in (
            intake.business_name,
            f"{cat.title()} in {city}",
            "Free Estimates",
            "Licensed & Insured",
            "Call Today",
            "Fast, Reliable Service",
            "Upfront Pricing",
            f"Top-Rated in {city}",
        )
    )
    descriptions = tuple(
        _clip(d, _DESCRIPTION_MAX)
        for d in (
            f"{intake.business_name} — reliable {cat} for {city}. Free estimates, upfront pricing.",
            "Licensed & insured local pros. Call now for fast, friendly service.",
            f"Serving {city} and nearby. Book online or call for a free quote today.",
        )
    )

    return AdsDraft(
        business_name=intake.business_name,
        service_category=cat,
        campaign_name=f"{intake.business_name} — {city} Search",
        geo_targets=geo,
        ad_groups=ad_groups,
        negative_keywords=_DEFAULT_NEGATIVES,
        headlines=headlines,
        descriptions=descriptions,
        landing_url=intake.site_url,
        daily_budget=daily_budget,
        monthly_budget=monthly_budget,
    )


def emit_ads_draft(
    intake: ClientIntake,
    docs_root: Path,
    *,
    daily_budget: float | None = None,
    monthly_budget: float | None = None,
) -> Path:
    """Write ``ADS.md`` into a client workspace and return its path."""
    docs_root.mkdir(parents=True, exist_ok=True)
    path = docs_root / "ADS.md"
    draft = draft_google_ads(intake, daily_budget=daily_budget, monthly_budget=monthly_budget)
    path.write_text(draft.to_markdown(), encoding="utf-8")
    return path
