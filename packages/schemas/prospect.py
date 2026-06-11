"""Prospect schema for the WAAS local-SMB pipeline.

Records are intentionally separate from discovery ``OpportunityRecord`` objects:
they describe candidate businesses, not validated product wedges. The schema
uses frozen dataclasses and explicit JSON conversion to match the rest of the
repo's persisted state conventions.
"""

from __future__ import annotations

from dataclasses import dataclass
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


class HumanVerified(str, Enum):
    UNSET = "unset"
    TRUE = "true"
    FALSE = "false"


class WebVerifyVerdict(str, Enum):
    UNVERIFIED = "unverified"
    OWNED_SITE = "owned_site"
    SOCIAL_ONLY = "social_only"
    MARKETPLACE_ONLY = "marketplace_only"
    NONE_FOUND = "none_found"
    AMBIGUOUS = "ambiguous"


class ProspectStatus(str, Enum):
    RAW = "raw"
    MAPS_ENRICHED = "maps_enriched"
    SOURCE_ENRICHED = "source_enriched"
    HTTP_ENRICHED = "http_enriched"
    ERROR = "error"


class EngagementStatus(str, Enum):
    """Sales/relationship track for the agency layer (Phase 3).

    Separate from ``ProspectStatus`` (which is purely scan-pipeline state).
    These states are **operator-set only** — there are no automated transitions
    and no outreach send path is introduced by the schema. Compliance gates
    (TCPA/CAN-SPAM consent) for any state past ``PROPOSAL_SENT`` land with the
    Phase 8 messaging work, not here.
    """

    NONE = "none"
    CONTACTED = "contacted"
    REPLIED = "replied"
    PROPOSAL_SENT = "proposal_sent"
    WON = "won"
    ONBOARDED = "onboarded"
    LOST = "lost"


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
    human_verified: HumanVerified = HumanVerified.UNSET
    human_verified_at: str = ""
    human_verify_note: str = ""

    # Search-backed web-presence verification. These fields are the gate between
    # raw directory/Maps candidates and any outreach-ready prospect list.
    web_verify_class: str = ""
    web_verify_verdict: WebVerifyVerdict = WebVerifyVerdict.UNVERIFIED
    web_verify_url: str = ""
    web_verify_confidence: float = 0.0
    web_verify_note: str = ""
    web_verified_at: str = ""
    web_verify_method: str = ""

    # Contact channels. Filled by the manual (browser) verification sweep so the
    # outreach layer has a reachable channel without re-browsing. Outreach reads
    # these; Phase 1 scan/HTTP paths leave them blank.
    contact_email: str = ""
    contact_instagram: str = ""
    contact_facebook: str = ""
    contact_booking_url: str = ""
    contact_source: str = ""
    contact_collected_at: str = ""

    # Open-source / third-party source provenance. Google Places records leave
    # these blank; Overture/FSQ imports fill them so every warehouse row can be
    # traced back to the source-run ledger and query that created it.
    source_name: str = ""
    source_record_id: str = ""
    source_run_key: str = ""
    source_query: str = ""
    source_confidence: float = 0.0
    source_collected_at: str = ""

    # Lifecycle.
    status: ProspectStatus = ProspectStatus.RAW
    # Agency layer (Phase 3) — operator-set sales track; no automated transitions.
    engagement_status: EngagementStatus = EngagementStatus.NONE
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
            "human_verified": self.human_verified.value,
            "human_verified_at": self.human_verified_at,
            "human_verify_note": self.human_verify_note,
            "web_verify_class": self.web_verify_class,
            "web_verify_verdict": self.web_verify_verdict.value,
            "web_verify_url": self.web_verify_url,
            "web_verify_confidence": self.web_verify_confidence,
            "web_verify_note": self.web_verify_note,
            "web_verified_at": self.web_verified_at,
            "web_verify_method": self.web_verify_method,
            "contact_email": self.contact_email,
            "contact_instagram": self.contact_instagram,
            "contact_facebook": self.contact_facebook,
            "contact_booking_url": self.contact_booking_url,
            "contact_source": self.contact_source,
            "contact_collected_at": self.contact_collected_at,
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
            "source_run_key": self.source_run_key,
            "source_query": self.source_query,
            "source_confidence": self.source_confidence,
            "source_collected_at": self.source_collected_at,
            "status": self.status.value,
            "engagement_status": self.engagement_status.value,
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
            human_verified=HumanVerified(
                str(
                    payload.get("human_verified", HumanVerified.UNSET.value)
                    or HumanVerified.UNSET.value
                )
            ),
            human_verified_at=str(payload.get("human_verified_at", "")),
            human_verify_note=str(payload.get("human_verify_note", "")),
            web_verify_class=str(payload.get("web_verify_class", "")),
            web_verify_verdict=WebVerifyVerdict(
                str(
                    payload.get("web_verify_verdict", WebVerifyVerdict.UNVERIFIED.value)
                    or WebVerifyVerdict.UNVERIFIED.value
                )
            ),
            web_verify_url=str(payload.get("web_verify_url", "")),
            web_verify_confidence=_web_confidence_float(
                payload.get("web_verify_confidence", 0)
            ),
            web_verify_note=str(payload.get("web_verify_note", "")),
            web_verified_at=str(payload.get("web_verified_at", "")),
            web_verify_method=str(payload.get("web_verify_method", "")),
            contact_email=str(payload.get("contact_email", "")),
            contact_instagram=str(payload.get("contact_instagram", "")),
            contact_facebook=str(payload.get("contact_facebook", "")),
            contact_booking_url=str(payload.get("contact_booking_url", "")),
            contact_source=str(payload.get("contact_source", "")),
            contact_collected_at=str(payload.get("contact_collected_at", "")),
            source_name=str(payload.get("source_name", "")),
            source_record_id=str(payload.get("source_record_id", "")),
            source_run_key=str(payload.get("source_run_key", "")),
            source_query=str(payload.get("source_query", "")),
            source_confidence=float(payload.get("source_confidence", 0) or 0),
            source_collected_at=str(payload.get("source_collected_at", "")),
            status=ProspectStatus(str(payload.get("status", ProspectStatus.RAW.value))),
            engagement_status=EngagementStatus(
                str(payload.get("engagement_status", EngagementStatus.NONE.value))
            ),
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


def _web_confidence_float(value: object) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, str):
        mapped = {"high": 0.9, "medium": 0.6, "low": 0.3}.get(value.strip().lower())
        if mapped is not None:
            return mapped
    return float(value)  # type: ignore[arg-type]
