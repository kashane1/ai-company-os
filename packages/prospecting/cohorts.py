"""Cohort derivation and priority scoring for prospects.

The cohort filter is the no-public-website signal, never the genre. Genres only
produce query cells for Places search.

Cohorts:
- ``A_gold``: no owned web presence at all (absent or social-only) — prime leads.
- ``A2_marketplace_review``: only a third-party booking/marketplace page (Vagaro,
  Square, Fresha, Yelp, etc.). No owned site, but page quality varies — a
  SECONDARY cold-outreach bucket that needs manual review before pitching.
- ``B_stale_maps``: has a site on Maps but it's dead/parked/redirecting.
- ``E_has_site``: real working owned site (includes website builders like
  Squarespace/Wix). Deprioritized.
- ``D_low_signal``: too few reviews to act on. ``Z_needs_review``: ambiguous.

Priority score formula: ``cohort_weight * demand_factor``. ``cohort_weight``
ranks no-site/stale signals ahead of ambiguous or has-site rows:
``A_gold=100``, ``A2_marketplace_review=85``, ``B_stale_maps=80``,
``Z_needs_review=40``, ``D_low_signal=15``, and ``E_has_site=5``.
``demand_factor`` is ``min(user_ratings_total / 100, 1.0)``. The score is rounded
to two decimals and is deterministic/idempotent for warehouse backfills.
"""

from __future__ import annotations

from packages.schemas.prospect import HttpCheckClass, MapsWebsiteClass, ProspectRecord

MIN_REVIEW_COUNT = 25


def derive_composite_cohort(record: ProspectRecord) -> str:
    if record.user_ratings_total < MIN_REVIEW_COUNT:
        return "D_low_signal"

    # Marketplace/booking-only presence is a SECONDARY manual-review bucket, not a
    # prime lead and not a drop. No owned website — just a third-party page — and
    # often the best pitch target, but page quality varies, so route it here for
    # review before outreach. Checked before A_gold so it never folds in.
    if record.maps_website_class is MapsWebsiteClass.MARKETPLACE:
        return "A2_marketplace_review"

    if (
        record.maps_website_class
        in {
            MapsWebsiteClass.ABSENT,
            MapsWebsiteClass.SOCIAL_ONLY,
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

    if (
        record.maps_website_class is MapsWebsiteClass.PRESENT
        and record.http_check_class is HttpCheckClass.SKIPPED
        and record.http_skip_reason == "present_site_not_in_deterministic_sample"
    ):
        return "E_has_site"

    return "Z_needs_review"


def priority_score(record: ProspectRecord, cohort: str | None = None) -> float:
    resolved = cohort or record.composite_cohort or derive_composite_cohort(record)
    cohort_weight = {
        "A_gold": 100,
        "A2_marketplace_review": 85,
        "B_stale_maps": 80,
        "Z_needs_review": 40,
        "D_low_signal": 15,
        "E_has_site": 5,
    }.get(resolved, 0)
    demand_factor = min(max(record.user_ratings_total, 0) / 100, 1.0)
    return round(cohort_weight * demand_factor, 2)
