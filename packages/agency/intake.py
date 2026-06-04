"""Client intake schema + renderers (Agency layer, Phase 4).

A :class:`ClientIntake` is the structured capture the ``client-intake`` skill
produces. It feeds two outputs:

* ``CLIENT_BRIEF.md`` (via :func:`render_brief`) — the human workspace doc;
* the scaffold token context (via :meth:`ClientIntake.to_site_context`) — reusing
  ``packages/web/scaffold.local_business_context`` so the existing Astro template
  renders a local-business site without forking a new "site factory".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.web.scaffold import local_business_context


@dataclass(frozen=True)
class ClientIntake:
    business_name: str
    service_category: str  # e.g. "plumbing", "med spa", "barber"
    city: str
    services: list[str] = field(default_factory=list)
    region: str = ""
    ideal_customer: str = ""
    hours: str = ""
    phone: str = ""
    photos: list[str] = field(default_factory=list)
    reviews_note: str = ""
    competitors: list[str] = field(default_factory=list)
    tagline: str = ""
    site_url: str = "https://example.com"
    service_area_cities: list[str] = field(default_factory=list)
    travel_radius_miles: int | None = None
    service_area_notes: str = ""
    matrix_approved: bool = False
    matrix_approved_by: str = ""
    matrix_approved_at: str = ""

    def validate(self) -> None:
        if not self.business_name.strip():
            raise ValueError("intake: business_name is required")
        if not self.service_category.strip():
            raise ValueError("intake: service_category is required")
        if not self.city.strip():
            raise ValueError("intake: city is required")
        if self.travel_radius_miles is not None and self.travel_radius_miles < 0:
            raise ValueError("intake: travel_radius_miles must be non-negative")

    def to_site_context(self) -> dict[str, str]:
        return local_business_context(
            self.business_name,
            service_category=self.service_category,
            city=self.city,
            services=self.services,
            phone=self.phone,
            tagline=self.tagline or None,
            site_url=self.site_url,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "business_name": self.business_name,
            "service_category": self.service_category,
            "city": self.city,
            "services": list(self.services),
            "region": self.region,
            "ideal_customer": self.ideal_customer,
            "hours": self.hours,
            "phone": self.phone,
            "photos": list(self.photos),
            "reviews_note": self.reviews_note,
            "competitors": list(self.competitors),
            "tagline": self.tagline,
            "site_url": self.site_url,
            "service_area_cities": list(self.service_area_cities),
            "travel_radius_miles": self.travel_radius_miles,
            "service_area_notes": self.service_area_notes,
            "matrix_approved": self.matrix_approved,
            "matrix_approved_by": self.matrix_approved_by,
            "matrix_approved_at": self.matrix_approved_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ClientIntake":
        return cls(
            business_name=str(payload["business_name"]),
            service_category=str(payload["service_category"]),
            city=str(payload["city"]),
            services=[str(x) for x in list(payload.get("services", []))],
            region=str(payload.get("region", "")),
            ideal_customer=str(payload.get("ideal_customer", "")),
            hours=str(payload.get("hours", "")),
            phone=str(payload.get("phone", "")),
            photos=[str(x) for x in list(payload.get("photos", []))],
            reviews_note=str(payload.get("reviews_note", "")),
            competitors=[str(x) for x in list(payload.get("competitors", []))],
            tagline=str(payload.get("tagline", "")),
            site_url=str(payload.get("site_url", "https://example.com")),
            service_area_cities=[
                str(x) for x in list(payload.get("service_area_cities", []))
            ],
            travel_radius_miles=(
                int(payload["travel_radius_miles"])
                if payload.get("travel_radius_miles") is not None
                else None
            ),
            service_area_notes=str(payload.get("service_area_notes", "")),
            matrix_approved=bool(payload.get("matrix_approved", False)),
            matrix_approved_by=str(payload.get("matrix_approved_by", "")),
            matrix_approved_at=str(payload.get("matrix_approved_at", "")),
        )


def render_brief(intake: ClientIntake) -> str:
    """Render the ``CLIENT_BRIEF.md`` body from a validated intake."""
    intake.validate()
    services = "\n".join(f"  - {s}" for s in intake.services) or "  - _TBD_"
    competitors = "\n".join(f"  - {c}" for c in intake.competitors) or "  - _none recorded_"
    photos = "\n".join(f"  - {p}" for p in intake.photos) or "  - _none provided_"
    return "\n".join(
        [
            f"# Client Brief — {intake.business_name}",
            "",
            f"- **Business type:** {intake.service_category}",
            f"- **Location:** {intake.city}{(', ' + intake.region) if intake.region else ''}",
            f"- **Travel radius:** {_radius(intake)}",
            f"- **Service area:** {_service_area(intake)}",
            f"- **Phone:** {intake.phone or '_TBD_'}",
            f"- **Hours:** {intake.hours or '_TBD_'}",
            f"- **Ideal customer:** {intake.ideal_customer or '_TBD_'}",
            "",
            "## Services",
            services,
            "",
            "## Photos",
            photos,
            "",
            "## Reviews",
            f"{intake.reviews_note or '_none recorded_'}",
            "",
            "## Competitors",
            competitors,
            "",
        ]
    )


def _radius(intake: ClientIntake) -> str:
    if intake.travel_radius_miles is None:
        return "_TBD_"
    return f"{intake.travel_radius_miles} miles"


def _service_area(intake: ClientIntake) -> str:
    cities = intake.service_area_cities or [intake.city]
    notes = f" — {intake.service_area_notes}" if intake.service_area_notes else ""
    return f"{', '.join(cities)}{notes}"
