from __future__ import annotations

from pathlib import Path

from packages.agency.conversion_lab import render_report_markdown, write_report
from packages.schemas.conversion_lab import ConversionLabReport, PersonaReview, Scorecard


def _report() -> ConversionLabReport:
    return ConversionLabReport(
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
                clarity_notes=["The first appointment flow is partly clear"],
                confidence="medium",
            )
        ],
        top_blockers=["Pricing is unclear"],
        top_trust_gaps=["Credentials are buried"],
        recommended_rewrites={"Hero": "Feel confident before your first treatment."},
        confidence_label="medium",
    )


def test_render_report_markdown_contains_client_sections() -> None:
    markdown = render_report_markdown(_report())

    assert "# Conversion Lab Report: smooth-med-spa-site" in markdown
    assert "## Executive Summary" in markdown
    assert "## Scorecard" in markdown
    assert "| Clarity | 7 |" in markdown
    assert "## Persona Feedback" in markdown
    assert "nervous-first-time-buyer" in markdown
    assert "Pricing is unclear" in markdown
    assert "Feel confident before your first treatment." in markdown
    assert "does not replace live analytics" in markdown


def test_write_report_uses_state_client_artifact_path(tmp_path: Path) -> None:
    path = write_report(_report(), root=tmp_path, run_id="2026-06-11-001")

    expected = (
        tmp_path
        / "state"
        / "clients"
        / "smooth-med-spa-site"
        / "conversion_lab"
        / "2026-06-11-001"
        / "REPORT.md"
    )
    assert path == expected
    assert path.exists()
    assert "docs" not in path.parts
