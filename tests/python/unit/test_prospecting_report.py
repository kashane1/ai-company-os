from __future__ import annotations

from packages.prospecting.report import render_phase2_cohort_report
from packages.schemas.prospect import HttpCheckClass, MapsWebsiteClass, ProspectRecord


def test_phase2_report_includes_required_sections() -> None:
    records = [
        ProspectRecord(
            place_id="places/a",
            display_name="A Business",
            formatted_address="Seattle, WA",
            phone="",
            types=[],
            city_id="seattle",
            genre_id="beauty_salon",
            grid_cell_id="seattle:beauty_salon",
            maps_website_class=MapsWebsiteClass.ABSENT,
            user_ratings_total=75,
            http_check_class=HttpCheckClass.SKIPPED,
            composite_cohort="A_gold",
            priority_score=75,
        ),
        ProspectRecord(
            place_id="places/z",
            display_name="Z Business",
            formatted_address="Seattle, WA",
            phone="",
            types=[],
            city_id="seattle",
            genre_id="auto_repair",
            grid_cell_id="seattle:auto_repair",
            maps_website_class=MapsWebsiteClass.PRESENT,
            user_ratings_total=100,
            http_check_class=HttpCheckClass.TIMEOUT,
            composite_cohort="Z_needs_review",
            priority_score=40,
            last_error="persistent timeout",
        ),
    ]

    report = render_phase2_cohort_report(
        records,
        before_counts={"Z_needs_review": 31, "A_gold": 10},
        exported_count=1,
    )

    assert "# Prospecting Phase 2 Cohort Report" in report
    assert "| before | Z_needs_review | 31 |" in report
    assert "| after | Z_needs_review | 1 |" in report
    assert "## Top Genres By A_gold" in report
    assert "## Priority Score Distribution" in report
    assert "Exported cohort-A rows: 1" in report
    assert "A_gold target: 50" in report
    assert "A_gold actual: 1" in report
    assert "persistent timeout" in report
