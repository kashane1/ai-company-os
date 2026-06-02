"""Prospect schema for the WAAS local-SMB pipeline.

Records are intentionally separate from discovery ``OpportunityRecord`` objects:
they describe candidate businesses, not validated product wedges. The schema
uses frozen dataclasses and explicit JSON conversion to match the rest of the
repo's persisted state conventions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class MapsWebsiteClass(str, Enum):
    ABSENT = "absent"
    PRESENT = "present"
    SOCIAL_ONLY = "social_only"
    MARKETPLACE = "marketplace"


class HttpCheckClass(str, Enum):
    SKIPPED = "skipped"
    OK_OWNED = "ok_owned"
    REDIRECT_SOCIAL = "redirect_social"
    DEAD = "dead"
    PARKED = "parked"
    TIMEOUT = "timeout"
    ERROR = "error"


class GoogleSearchCheck(str, Enum):
    SKIPPED = "skipped"


class ReviewTier(str, Enum):
    R0 = "R0"


class ProspectStatus(str, Enum):
    RAW = "raw"
    MAPS_ENRICHED = "maps_enriched"
    HTTP_ENRICHED = "http_enriched"
    ERROR = "error"


@dataclass(frozen=True)
class HttpCheck:
    http_check_class: HttpCheckClass
    final_url: str = ""
    status: int | None = None
    checked_at: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "http_check_class": self.http_check_class.value,
            "final_url": self.final_url,
            "status": self.status,
            "checked_at": self.checked_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "HttpCheck":
        return cls(
            http_check_class=HttpCheckClass(
                str(payload.get("http_check_class", HttpCheckClass.SKIPPED.value))
            ),
            final_url=str(payload.get("final_url", "")),
            status=_opt_int(payload.get("status")),
            checked_at=str(payload.get("checked_at", "")),
            error=str(payload.get("error", "")),
        )


@dataclass(frozen=True)
class ProspectRecord:
    # Identity.
    place_id: str
    display_name: str
    formatted_address: str
    phone: str
    types: list[str]
    city_id: str
    genre_id: str
    grid_cell_id: str

    # Maps website signal.
    maps_website_uri: str = ""
    maps_website_host: str = ""
    maps_website_class: MapsWebsiteClass = MapsWebsiteClass.ABSENT

    # Demand proxy.
    rating: float | None = None
    user_ratings_total: int = 0

    # HTTP enrichment.
    http_check_class: HttpCheckClass = HttpCheckClass.SKIPPED
    http_final_url: str = ""
    http_status: int | None = None
    http_checked_at: str = ""
    http_skip_reason: str = ""

    # Phase 1 intentionally skips Google search and review text.
    google_search_check: GoogleSearchCheck = GoogleSearchCheck.SKIPPED
    review_tier: ReviewTier = ReviewTier.R0

    # Derived.
    composite_cohort: str = ""
    priority_score: float = 0.0

    # Lifecycle.
    status: ProspectStatus = ProspectStatus.RAW
    created_at: str = ""
    updated_at: str = ""
    last_error: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "place_id": self.place_id,
            "display_name": self.display_name,
            "formatted_address": self.formatted_address,
            "phone": self.phone,
            "types": list(self.types),
            "city_id": self.city_id,
            "genre_id": self.genre_id,
            "grid_cell_id": self.grid_cell_id,
            "maps_website_uri": self.maps_website_uri,
            "maps_website_host": self.maps_website_host,
            "maps_website_class": self.maps_website_class.value,
            "rating": self.rating,
            "user_ratings_total": self.user_ratings_total,
            "http_check_class": self.http_check_class.value,
            "http_final_url": self.http_final_url,
            "http_status": self.http_status,
            "http_checked_at": self.http_checked_at,
            "http_skip_reason": self.http_skip_reason,
            "google_search_check": self.google_search_check.value,
            "review_tier": self.review_tier.value,
            "composite_cohort": self.composite_cohort,
            "priority_score": self.priority_score,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ProspectRecord":
        return cls(
            place_id=str(payload["place_id"]),
            display_name=str(payload.get("display_name", "")),
            formatted_address=str(payload.get("formatted_address", "")),
            phone=str(payload.get("phone", "")),
            types=[str(item) for item in list(payload.get("types", []))],
            city_id=str(payload.get("city_id", "")),
            genre_id=str(payload.get("genre_id", "")),
            grid_cell_id=str(payload.get("grid_cell_id", "")),
            maps_website_uri=str(payload.get("maps_website_uri", "")),
            maps_website_host=str(payload.get("maps_website_host", "")),
            maps_website_class=MapsWebsiteClass(
                str(payload.get("maps_website_class", MapsWebsiteClass.ABSENT.value))
            ),
            rating=_opt_float(payload.get("rating")),
            user_ratings_total=int(payload.get("user_ratings_total", 0) or 0),
            http_check_class=HttpCheckClass(
                str(payload.get("http_check_class", HttpCheckClass.SKIPPED.value))
            ),
            http_final_url=str(payload.get("http_final_url", "")),
            http_status=_opt_int(payload.get("http_status")),
            http_checked_at=str(payload.get("http_checked_at", "")),
            http_skip_reason=str(payload.get("http_skip_reason", "")),
            google_search_check=GoogleSearchCheck(
                str(payload.get("google_search_check", GoogleSearchCheck.SKIPPED.value))
            ),
            review_tier=ReviewTier(str(payload.get("review_tier", ReviewTier.R0.value))),
            composite_cohort=str(payload.get("composite_cohort", "")),
            priority_score=float(payload.get("priority_score", 0) or 0),
            status=ProspectStatus(str(payload.get("status", ProspectStatus.RAW.value))),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
            last_error=str(payload.get("last_error", "")),
        )


def replace_record(record: ProspectRecord, **updates: object) -> ProspectRecord:
    payload = record.to_dict()
    payload.update(updates)
    return ProspectRecord.from_dict(payload)


def _opt_float(value: object) -> float | None:
    return None if value is None else float(value)  # type: ignore[arg-type]


def _opt_int(value: object) -> int | None:
    return None if value is None else int(value)  # type: ignore[arg-type]
