"""Cohort derivation for Phase 1 prospects.

The cohort filter is the no-public-website signal, never the genre. Genres only
produce query cells for Places search.
"""

from __future__ import annotations

from packages.schemas.prospect import HttpCheckClass, MapsWebsiteClass, ProspectRecord

MIN_REVIEW_COUNT = 25


def derive_composite_cohort(record: ProspectRecord) -> str:
    if record.user_ratings_total < MIN_REVIEW_COUNT:
        return "D_low_signal"

    if (
        record.maps_website_class
        in {
            MapsWebsiteClass.ABSENT,
            MapsWebsiteClass.SOCIAL_ONLY,
            MapsWebsiteClass.MARKETPLACE,
        }
        and record.http_check_class is not HttpCheckClass.OK_OWNED
    ):
        return "A_gold"

    if (
        record.maps_website_class is MapsWebsiteClass.PRESENT
        and record.http_check_class
        in {
            HttpCheckClass.DEAD,
            HttpCheckClass.PARKED,
            HttpCheckClass.REDIRECT_SOCIAL,
        }
    ):
        return "B_stale_maps"

    if (
        record.maps_website_class is MapsWebsiteClass.PRESENT
        and record.http_check_class is HttpCheckClass.OK_OWNED
    ):
        return "E_has_site"

    return "Z_needs_review"


def priority_score(record: ProspectRecord, cohort: str | None = None) -> float:
    """Simple v1 priority score.

    Formula: up to 70 points for public demand volume, up to 20 points for star
    rating, plus a cohort bump (10 for A, 6 for B, 2 for Z). It is intentionally
    transparent and easy to replace after validation data exists.
    """

    resolved = cohort or record.composite_cohort or derive_composite_cohort(record)
    review_points = min(record.user_ratings_total, 50) / 50 * 70
    rating_points = ((record.rating or 0) / 5) * 20
    cohort_points = {"A_gold": 10, "B_stale_maps": 6, "Z_needs_review": 2}.get(
        resolved, 0
    )
    return round(review_points + rating_points + cohort_points, 2)

