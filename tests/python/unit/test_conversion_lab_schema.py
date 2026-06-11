from __future__ import annotations

import pytest

from packages.schemas.conversion_lab import (
    ConversionAction,
    ConversionLabInput,
    ConversionLabReport,
    PersonaReview,
    Scorecard,
)


def test_conversion_lab_input_round_trips() -> None:
    payload = {
        "product_id": "smooth-med-spa-site",
        "vertical": "med_spa",
        "target_action": "booking",
        "url": "https://example.com",
        "page_copy": "Book a consultation today.",
        "known_objections": ["Is it safe?", "How much does it cost?"],
    }

    item = ConversionLabInput.from_dict(payload)

    assert item.target_action is ConversionAction.BOOKING
    assert item.to_dict() == payload


def test_conversion_lab_report_round_trips() -> None:
    report = ConversionLabReport(
        product_id="smooth-med-spa-site",
        vertical="med_spa",
        scorecard=Scorecard(
            clarity=7,
            trust=5,
            offer_strength=6,
            friction=4,
            local_relevance=8,
            conversion_action=6,
        ),
        persona_reviews=[
            PersonaReview(
                persona_id="nervous-first-time-buyer",
                likely_action="hesitate",
                objections=["No pricing context"],
                trust_gaps=["No provider credentials"],
                useful_rewrites=["Add consultation reassurance"],
                clarity_notes=["The basic offer is understandable"],
                confidence="medium",
            )
        ],
        top_blockers=["Pricing is unclear"],
        top_trust_gaps=["Credentials are buried"],
        recommended_rewrites={"hero": "Feel confident before your first treatment."},
        confidence_label="medium",
    )

    assert ConversionLabReport.from_dict(report.to_dict()) == report


def test_scorecard_rejects_out_of_range_scores() -> None:
    with pytest.raises(ValueError, match="clarity"):
        Scorecard(
            clarity=11,
            trust=5,
            offer_strength=6,
            friction=4,
            local_relevance=8,
            conversion_action=6,
        )
