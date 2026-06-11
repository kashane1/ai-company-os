from __future__ import annotations

from packages.prospecting.qualification import next_qualification_plan
from packages.schemas.prospect import MapsWebsiteClass, ProspectRecord, WebVerifyVerdict


def _record(
    place_id: str,
    *,
    cohort: str,
    score: float,
    verdict: WebVerifyVerdict = WebVerifyVerdict.UNVERIFIED,
) -> ProspectRecord:
    return ProspectRecord(
        place_id=place_id,
        display_name=place_id.rsplit("/", 1)[-1].replace("-", " ").title(),
        formatted_address="Seattle, WA",
        phone="+1 206-555-0100",
        types=["local_business"],
        city_id="seattle",
        genre_id="auto_repair",
        grid_cell_id="seattle:auto_repair",
        maps_website_class=MapsWebsiteClass.ABSENT,
        user_ratings_total=75,
        composite_cohort=cohort,
        priority_score=score,
        web_verify_verdict=verdict,
    )


def test_next_qualification_plan_prefers_unverified_marketplace_review_bucket() -> None:
    plan = next_qualification_plan(
        [
            _record("places/a-gold", cohort="A_gold", score=95),
            _record("places/a2-best", cohort="A2_marketplace_review", score=80),
            _record("places/a2-done", cohort="A2_marketplace_review", score=90,
                    verdict=WebVerifyVerdict.MARKETPLACE_ONLY),
        ],
        provider="brave",
        limit=25,
    )

    assert plan.action == "verify_current_warehouse"
    assert plan.cohort == "A2_marketplace_review"
    assert plan.command == (
        "python scripts/prospect_scan.py verify-web "
        "--provider brave --cohort A2_marketplace_review --limit 1"
    )
    assert plan.candidate_place_ids == ["places/a2-best"]


def test_next_qualification_plan_falls_back_to_new_source_collection_when_exhausted() -> None:
    plan = next_qualification_plan(
        [
            _record(
                "places/done",
                cohort="A2_marketplace_review",
                score=80,
                verdict=WebVerifyVerdict.MARKETPLACE_ONLY,
            )
        ],
        provider="dataforseo",
        limit=25,
    )

    assert plan.action == "collect_new_source_data"
    assert plan.cohort == ""
    assert "source-run ledger" in plan.reason


def test_next_qualification_plan_picks_unverified_source_candidates_after_maps_buckets() -> None:
    plan = next_qualification_plan(
        [
            _record(
                "source/overture:fresh-1",
                cohort="S_source_candidate",
                score=30,
            ),
            _record(
                "source/overture:done",
                cohort="S_source_candidate",
                score=35,
                verdict=WebVerifyVerdict.NONE_FOUND,
            ),
        ],
        provider="brave",
        limit=25,
    )

    assert plan.action == "verify_current_warehouse"
    assert plan.cohort == "S_source_candidate"
    assert plan.command == (
        "python scripts/prospect_scan.py verify-web "
        "--provider brave --cohort S_source_candidate --limit 1"
    )
    assert plan.candidate_place_ids == ["source/overture:fresh-1"]
