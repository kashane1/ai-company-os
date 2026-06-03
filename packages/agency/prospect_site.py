"""Prospect → preview-site glue (Agency layer).

Turns a verified prospect warehouse record (``state/prospects/records/*.json``)
into a one-page **preview** site and (optionally) deploys it to Netlify as a
*draft* deploy — the private ``{mockup_url}`` the outreach library's
``email/with-mockup.md`` template references.

This is deliberately thin: it composes pieces that already exist rather than
forking a new "site factory".

    record  ->  ClientIntake            (this module: intake_from_record)
            ->  scaffold token context  (packages.agency.intake.to_site_context)
            ->  index.html              (packages.web.scaffold.render_landing_html, no Node)
            ->  Netlify draft deploy     (packages.web.deploy.NetlifyDeployTarget, production=False)
            ->  mockup_url written back to the record

Preview (draft) deploys are intentionally **ungated** per
``packages/policies/deploy_readiness.py`` — only production deploys, custom
domains, and hosting spend require approval. So a preview mockup never needs an
approval gate; promoting one to production later does.

No Node is required for the preview: ``render_landing_html`` emits the same
markup Astro would, with CSS inlined, as a single self-contained HTML file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.agency.demo_theme import DemoTheme, apply_theme, theme_for_record
from packages.agency.intake import ClientIntake
from packages.web.deploy import DeployAccount, DeployResult, DeployTarget
from packages.web.scaffold import render_landing_html, unfilled_tokens

# --- Genre → site framing -------------------------------------------------
# Maps the warehouse ``genre_id`` to human-readable site copy. ``category``
# slots into sentences like "Trusted {category} in {city}" and "reliable
# {category} for {city}", so it must read naturally as a noun phrase.


@dataclass(frozen=True)
class GenreProfile:
    category: str
    services: tuple[str, ...]


GENRE_PROFILES: dict[str, GenreProfile] = {
    "plumber": GenreProfile("plumbing", ("Repairs & leaks", "Water heaters", "Drain cleaning")),
    "electrician": GenreProfile(
        "electrical services", ("Wiring & panels", "Lighting", "Repairs & safety")
    ),
    "roofer": GenreProfile("roofing", ("Roof repair", "Replacement", "Inspections")),
    "landscaper": GenreProfile(
        "landscaping", ("Lawn care", "Design & planting", "Cleanups")
    ),
    "house_cleaning": GenreProfile(
        "house cleaning", ("Recurring cleans", "Deep cleans", "Move-in/move-out")
    ),
    "garage_door": GenreProfile(
        "garage door service", ("Repairs", "Spring replacement", "New installs")
    ),
    "auto_repair": GenreProfile(
        "auto repair", ("Diagnostics", "Brakes & tires", "Scheduled maintenance")
    ),
    "barber_shop": GenreProfile("barbering", ("Haircuts", "Fades", "Beard trims")),
    "beauty_salon": GenreProfile("salon services", ("Hair", "Color", "Styling")),
    "nail_salon": GenreProfile("nail care", ("Manicures", "Pedicures", "Gel & acrylics")),
    "massage_therapy": GenreProfile(
        "massage therapy", ("Deep tissue", "Relaxation", "Sports recovery")
    ),
    "dog_groomer": GenreProfile("dog grooming", ("Full grooms", "Baths", "Nail trims")),
    "bakery": GenreProfile("baked goods", ("Fresh bread", "Custom cakes", "Pastries")),
    "coffee_shop": GenreProfile("coffee", ("Espresso drinks", "Pastries", "Cold brew")),
    "restaurant": GenreProfile("dining", ("Dine-in", "Takeout", "Catering")),
    "yoga_studio": GenreProfile("yoga classes", ("Vinyasa", "Beginner classes", "Workshops")),
    "tutoring": GenreProfile("tutoring", ("Math & science", "Reading & writing", "Test prep")),
    "music_lessons": GenreProfile(
        "music lessons", ("Private lessons", "All ages", "Multiple instruments")
    ),
    "accountant": GenreProfile(
        "accounting services", ("Tax prep", "Bookkeeping", "Payroll")
    ),
    "notary": GenreProfile("notary services", ("Mobile notary", "Loan signings", "Acknowledgments")),
}

_DEFAULT_PROFILE = GenreProfile("local services", ("Quality work", "Fair pricing", "Local & reliable"))

# City ids that don't title-case cleanly.
_CITY_OVERRIDES = {"washington_dc": "Washington, DC", "new_york": "New York", "el_paso": "El Paso"}


def city_label(city_id: str) -> str:
    if city_id in _CITY_OVERRIDES:
        return _CITY_OVERRIDES[city_id]
    return " ".join(part.capitalize() for part in city_id.split("_"))


def _state_from_address(formatted_address: str) -> str:
    """Best-effort '..., Albuquerque, NM 87110, USA' -> 'NM'."""
    parts = [p.strip() for p in formatted_address.split(",")]
    for part in parts:
        toks = part.split()
        if toks and len(toks[0]) == 2 and toks[0].isupper():
            return toks[0]
    return ""


def intake_from_record(record: dict) -> ClientIntake:
    """Map a warehouse record to a validated :class:`ClientIntake`."""
    genre = str(record.get("genre_id", ""))
    profile = GENRE_PROFILES.get(genre, _DEFAULT_PROFILE)
    city = city_label(str(record.get("city_id", "")))
    state = _state_from_address(str(record.get("formatted_address", "")))
    where = f"{city}, {state}" if (city and state) else (city or state)
    intake = ClientIntake(
        business_name=str(record.get("display_name", "")).strip() or "Local Business",
        service_category=profile.category,
        city=where,
        services=list(profile.services),
        phone=str(record.get("phone", "")).strip(),
        reviews_note=(
            f"{record.get('rating')}★ from {record.get('user_ratings_total')} Google reviews"
            if record.get("user_ratings_total")
            else ""
        ),
    )
    intake.validate()
    return intake


def apply_profile(context: dict[str, str], profile: dict, record: dict) -> dict[str, str]:
    """Overlay REAL Google Places data onto the scaffold context.

    Weaves real business attributes into the existing template tokens (no
    template fork): the editorial summary becomes the hero subhead, real opening
    hours and location become the first two FAQ answers, the primary type
    sharpens the eyebrow, and the rating becomes a factual testimonial. Anything
    the profile lacks falls back to the genre-default copy already in ``context``.
    """
    ctx = dict(context)
    summary = str((profile.get("editorialSummary") or {}).get("text", "")).strip()
    primary = str((profile.get("primaryTypeDisplayName") or {}).get("text", "")).strip()
    hours = [str(h) for h in (profile.get("regularOpeningHours") or {}).get("weekdayDescriptions", [])]
    address = str(profile.get("formattedAddress") or record.get("formatted_address", "")).strip()
    phone = str(profile.get("nationalPhoneNumber") or record.get("phone", "")).strip()
    rating = profile.get("rating") or record.get("rating")
    count = profile.get("userRatingCount") or record.get("user_ratings_total")

    if primary:
        ctx["EYEBROW"] = f"{primary} · {ctx.get('EYEBROW', '').split('·')[-1].strip() or address}"
    if summary:
        ctx["HERO_SUBHEAD"] = summary
    if hours:
        ctx["FAQ_1_Q"] = "What are your hours?"
        ctx["FAQ_1_A"] = " · ".join(hours)
    if address:
        ctx["FAQ_2_Q"] = "Where are you located?"
        loc = address + (f" Call {phone}." if phone else "")
        ctx["FAQ_2_A"] = loc
    if rating and count:
        ctx["TESTIMONIAL"] = f"Rated {rating}★ by {count}+ customers on Google."
        ctx["TESTIMONIAL_AUTHOR"] = "— Verified Google reviews"
    return ctx


def profile_fields_used(profile: dict) -> list[str]:
    """Which real fields a profile actually contributed (for transparency)."""
    used = []
    if (profile.get("editorialSummary") or {}).get("text"):
        used.append("editorial_summary")
    if (profile.get("primaryTypeDisplayName") or {}).get("text"):
        used.append("primary_type")
    if (profile.get("regularOpeningHours") or {}).get("weekdayDescriptions"):
        used.append("hours")
    if profile.get("rating") and profile.get("userRatingCount"):
        used.append("rating")
    return used


def render_preview_html(
    record: dict,
    profile: dict | None = None,
    *,
    theme: DemoTheme | None = None,
    themed: bool = True,
) -> str:
    """Render the preview page HTML for a record (no Node, no network).

    When ``profile`` (a Google Places Details payload) is given, real business
    data is overlaid onto the page; otherwise genre-default copy is used.

    Unless ``themed`` is False, a deterministic per-business :class:`DemoTheme`
    (palette + font pairing + layout variant, derived offline from ``genre_id`` +
    ``place_id``) is applied so demos don't all look like the same template.
    Pass ``theme`` to override the derived one.
    """
    context = intake_from_record(record).to_site_context()
    if profile:
        context = apply_profile(context, profile, record)
    html = render_landing_html(context)
    leftover = unfilled_tokens(html)
    if leftover:  # render guard — never ship a page with visible {{TOKENS}}
        raise ValueError(f"unfilled template tokens: {leftover}")
    if themed:
        html = apply_theme(html, theme or theme_for_record(record))
    return html


def write_preview_dist(record: dict, out_dir: Path, profile: dict | None = None) -> Path:
    """Write a single-file ``dist/index.html`` preview under ``out_dir``.

    Returns the ``dist`` directory (ready for zip-deploy or local opening).
    """
    dist = out_dir / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(render_preview_html(record, profile), encoding="utf-8")
    return dist


# One shared Netlify site holds ALL prospect previews. Each preview is a
# *draft* deploy to it, so every prospect gets a unique, private permalink
# (``<deploy_id>--<PREVIEW_SITE_NAME>.netlify.app``) without creating a new site
# or a production deploy per prospect. Keep this name short: the 24-char
# deploy-id prefix + "--" + this name must stay within the 63-char DNS label
# limit (24 + 2 + 12 = 38 here, comfortably under).
PREVIEW_SITE_NAME = "bbw-previews"


def preview_site_name(record: dict) -> str:
    """A stable, Netlify-safe *slug* for a prospect (no longer a site name).

    Kept as a per-prospect identifier (used in labels/filenames); prospect
    previews are now draft deploys to the shared ``PREVIEW_SITE_NAME`` site
    rather than one Netlify site each.
    """
    from packages.agency.templates import slugify

    slug = slugify(str(record.get("display_name", "")))
    city = str(record.get("city_id", "")).replace("_", "-")
    return f"preview-{slug}-{city}"[:63].strip("-")


@dataclass(frozen=True)
class PreviewResult:
    place_id: str
    site_name: str
    dist_dir: Path
    deployed: bool
    mockup_url: str = ""
    site_id: str = ""
    deploy_id: str = ""


def build_preview_for_record(
    record: dict,
    out_dir: Path,
    *,
    target: DeployTarget | None = None,
    account: DeployAccount | None = None,
    profile: dict | None = None,
    site_name: str = PREVIEW_SITE_NAME,
) -> PreviewResult:
    """Build the preview; if ``target`` is given, publish it to Netlify.

    With no ``target`` this is a pure local build (the safe default).

    With a ``target`` the mockup is published as a **draft deploy** to a single
    **shared** preview site (``site_name``, default :data:`PREVIEW_SITE_NAME`).
    Each draft gets its own private permalink
    (``<deploy_id>--<site_name>.netlify.app``) — exactly the "deploy preview for
    client review" model — so we do **not** create a new Netlify site or run a
    production deploy per prospect. That is the credit/site-count saver: hundreds
    of previews cost one site and cheap draft deploys, not hundreds of production
    sites.

    A short ``site_name`` keeps the draft permalink within the 63-char DNS-label
    limit (the old per-prospect ``preview-<business>-<city>`` site names were
    what pushed drafts over it — hence the earlier production-per-site workaround
    this replaces).

    Promoting a preview to **production** (a client's or the agency's real site)
    and any **custom domain / DNS** remain separate, approval-gated actions
    (see ``packages/agency/launch.py`` + ``packages/policies/deploy_readiness.py``).
    """
    dist = write_preview_dist(record, out_dir, profile)
    place_id = str(record.get("place_id", ""))
    if target is None:
        return PreviewResult(place_id, site_name, dist, deployed=False)

    site = target.ensure_site(site_name, account=account)
    # Draft (production=False): client-review permalink, never the live URL.
    result: DeployResult = target.deploy(site, dist, production=False)
    return PreviewResult(
        place_id=place_id,
        site_name=site_name,
        dist_dir=dist,
        deployed=True,
        mockup_url=result.url,
        site_id=site.site_id,
        deploy_id=result.deploy_id,
    )
