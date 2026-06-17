from __future__ import annotations

from packages.prospecting.census import build_census, render_census
from packages.schemas.prospect import MapsWebsiteClass, ProspectRecord, WebVerifyVerdict


def _rec(
    place_id: str,
    *,
    source: str = "dataforseo",
    cohort: str = "A_gold",
    method: str = "",
    verdict: WebVerifyVerdict = WebVerifyVerdict.UNVERIFIED,
    phone: str = "",
    email: str = "",
) -> ProspectRecord:
    return ProspectRecord(
        place_id=place_id,
        display_name="Biz",
        formatted_address="1 St",
        phone=phone,
        types=[],
        city_id="seattle",
        genre_id="nail_salon",
        grid_cell_id="seattle:nail_salon",
        maps_website_class=MapsWebsiteClass.ABSENT,
        source_name=source,
        composite_cohort=cohort,
        web_verify_method=method,
        web_verify_verdict=verdict,
        contact_email=email,
    )


def test_census_counts_sources_cohorts_and_verification() -> None:
    records = [
        _rec("a", method="manual_browser", verdict=WebVerifyVerdict.NONE_FOUND, phone="1"),
        _rec("b", method="manual_browser", verdict=WebVerifyVerdict.OWNED_SITE),
        _rec("c", source="overture", cohort="S_source_candidate"),  # unverified
    ]
    census = build_census(records)
    assert census.total == 3
    assert census.by_source == {"dataforseo": 2, "overture": 1}
    cohorts = {c.cohort: c for c in census.by_cohort}
    assert cohorts["A_gold"].total == 2 and cohorts["A_gold"].verified == 2
    assert cohorts["S_source_candidate"].unverified == 1
    assert census.by_method["(unverified)"] == 1
    assert census.verified_verdicts["none_found"] == 1


def test_census_ready_to_build_only_counts_verified_targets() -> None:
    records = [
        # target: verified none_found, has phone, no digital contact
        _rec("t1", method="manual_browser", verdict=WebVerifyVerdict.NONE_FOUND, phone="1"),
        # target with a digital contact (email)
        _rec("t2", method="manual_browser", verdict=WebVerifyVerdict.SOCIAL_ONLY, email="x@y.com"),
        # NOT a target: owned_site verdict
        _rec("d1", method="manual_browser", verdict=WebVerifyVerdict.OWNED_SITE),
        # NOT a target: unverified
        _rec("u1"),
    ]
    census = build_census(records)
    assert len(census.ready_to_build) == 1
    roll = census.ready_to_build[0]
    assert roll.cohort == "A_gold" and roll.source == "dataforseo"
    assert roll.targets == 2
    assert roll.with_phone == 1
    assert roll.with_digital_contact == 1


def test_render_census_is_markdown() -> None:
    records = [_rec("a", method="brave", verdict=WebVerifyVerdict.NONE_FOUND)]
    out = render_census(build_census(records))
    assert "# Prospect Census" in out
    assert "## Ready to build" in out
