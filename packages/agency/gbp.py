"""Google Business Profile changeset draft (Agency layer, G7 — Package C service).

Turns a :class:`~packages.agency.intake.ClientIntake` into a ``GBP_CHANGESET.md``
the operator copies into the client's Google Business Profile: primary category,
services, hours, a compliant description, contact/booking links, and a photo
checklist. This is the planner-named ``draft_gbp_changeset`` made real.

Advisory by design: GBP has no write here. The doc is a checklist; before
applying, the operator re-reads the live profile and only changes what differs
([D6] — full API drift-diff is a later automation).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.agency.intake import ClientIntake

# GBP descriptions are capped at 750 characters.
_MAX_DESCRIPTION = 750

# Best-effort map from a free-text service_category to a real GBP primary
# category. Substring match (first hit wins); falls back to a title-cased guess
# the operator confirms in GBP.
_GBP_CATEGORY_HINTS: tuple[tuple[str, str], ...] = (
    ("plumb", "Plumber"),
    ("electric", "Electrician"),
    ("roof", "Roofing contractor"),
    ("landscap", "Landscaper"),
    ("garage door", "Garage door supplier"),
    ("house clean", "House cleaning service"),
    ("clean", "House cleaning service"),
    ("auto", "Auto repair shop"),
    ("barber", "Barber shop"),
    ("nail", "Nail salon"),
    ("salon", "Beauty salon"),
    ("massage", "Massage therapist"),
    ("dog groom", "Pet groomer"),
    ("groom", "Pet groomer"),
    ("bakery", "Bakery"),
    ("bak", "Bakery"),
    ("coffee", "Coffee shop"),
    ("restaurant", "Restaurant"),
    ("yoga", "Yoga studio"),
    ("tutor", "Tutoring service"),
    ("music", "Music school"),
    ("account", "Accountant"),
    ("notary", "Notary public"),
)

# Photos GBP rewards; the operator confirms/uploads each.
_PHOTO_CHECKLIST = (
    "Logo",
    "Storefront / exterior",
    "Interior",
    "Team at work / in action",
    "Completed work (before/after where relevant)",
)


def suggest_primary_category(service_category: str) -> str:
    text = service_category.strip().lower()
    for needle, category in _GBP_CATEGORY_HINTS:
        if needle in text:
            return category
    return service_category.strip().title() or "Local business"


@dataclass(frozen=True)
class GbpChangeset:
    business_name: str
    primary_category: str
    description: str
    services: tuple[str, ...] = ()
    hours: str = ""
    phone: str = ""
    website: str = ""
    booking_url: str = ""
    service_area: tuple[str, ...] = ()
    photo_checklist: tuple[str, ...] = _PHOTO_CHECKLIST

    def to_markdown(self) -> str:
        def _bullets(items: tuple[str, ...], empty: str) -> list[str]:
            return [f"- {i}" for i in items] if items else [f"- {empty}"]

        lines = [
            f"# GBP Changeset — {self.business_name}",
            "",
            "> **Draft for the operator.** Apply in Google Business Profile by hand.",
            "> Before changing a field, check the live profile and only update what",
            "> differs (don't overwrite owner edits). [D6]",
            "",
            "## Primary category",
            "",
            f"- **Suggested:** {self.primary_category} _(confirm against GBP's list)_",
            "",
            "## Services",
            "",
            *_bullets(self.services, "_add from intake_"),
            "",
            "## Hours",
            "",
            f"{self.hours or '_TBD — set regular hours_'}",
            "",
            "## Description (≤750 chars)",
            "",
            self.description,
            "",
            "## Contact & links",
            "",
            f"- **Phone:** {self.phone or '_TBD_'}",
            f"- **Website:** {self.website or '_TBD_'}",
            f"- **Booking link:** {self.booking_url or '_none yet_'}",
            "",
            "## Service area",
            "",
            *_bullets(self.service_area, "_primary city_"),
            "",
            "## Photos to add",
            "",
            *[f"- [ ] {p}" for p in self.photo_checklist],
            "",
        ]
        return "\n".join(lines) + "\n"


def _description(intake: ClientIntake) -> str:
    services = ", ".join(intake.services[:5])
    parts = [f"{intake.business_name} provides {intake.service_category} for {intake.city}."]
    if services:
        parts.append(f"We offer {services}.")
    parts.append(
        f"Call {intake.phone} for a free estimate."
        if intake.phone
        else "Contact us for a free estimate."
    )
    return " ".join(parts)[:_MAX_DESCRIPTION]


def draft_gbp_changeset(intake: ClientIntake, *, booking_url: str = "") -> GbpChangeset:
    intake.validate()
    service_area = intake.service_area_cities or ([intake.city] if intake.city else [])
    return GbpChangeset(
        business_name=intake.business_name,
        primary_category=suggest_primary_category(intake.service_category),
        description=_description(intake),
        services=tuple(intake.services),
        hours=intake.hours,
        phone=intake.phone,
        website=intake.site_url,
        booking_url=booking_url,
        service_area=tuple(service_area),
    )


def emit_gbp_changeset(
    intake: ClientIntake, docs_root: Path, *, booking_url: str = ""
) -> Path:
    """Write ``GBP_CHANGESET.md`` into a client workspace and return its path."""
    docs_root.mkdir(parents=True, exist_ok=True)
    path = docs_root / "GBP_CHANGESET.md"
    changeset = draft_gbp_changeset(intake, booking_url=booking_url)
    path.write_text(changeset.to_markdown(), encoding="utf-8")
    return path
