"""Tests for the analyst calibration eval (E7).

The canonical dataset must score 100% against the deterministic heuristic
provider — that's the drift tripwire. If a weight, threshold, or heuristic
change breaks calibration, this test fails.
"""

from __future__ import annotations

from packages.discovery.analyst import HeuristicSignalProvider
from packages.discovery.calibration import (
    CalibrationCase,
    default_calibration_cases,
    run_calibration,
)
from packages.discovery.scoring import load_scoring_config
from packages.schemas.opportunity import (
    EvidenceKind,
    EvidenceLink,
    OpportunityRecord,
    OpportunitySignals,
    SourceRef,
)


def test_default_dataset_is_fully_calibrated_against_heuristic() -> None:
    report = run_calibration(default_calibration_cases(), HeuristicSignalProvider())
    assert report.accuracy == 1.0, f"calibration drift: {[f.detail for f in report.failures]}"
    assert report.total == 5


def test_report_markdown_renders() -> None:
    report = run_calibration(default_calibration_cases(), HeuristicSignalProvider())
    md = report.to_markdown()
    assert "# Analyst calibration" in md
    assert "accuracy" in md


def test_detects_a_miscalibrated_case() -> None:
    # A case that claims a clearly-weak wedge should advance — the gate disagrees,
    # so the eval must flag it as a failure (proving it isn't a rubber stamp).
    bad_case = CalibrationCase(
        name="impossible",
        record=OpportunityRecord(
            id="opp_x",
            title="t",
            problem="p",
            audience="a",
            source=SourceRef(connector="hackernews"),
            evidence=[EvidenceLink(url="https://x/1", kind=EvidenceKind.OTHER)],
            signals=OpportunitySignals(),  # all zeros -> score 0
        ),
        expect_advance=True,
    )
    report = run_calibration([bad_case], HeuristicSignalProvider(), config=load_scoring_config())
    assert report.accuracy == 0.0
    assert report.failures[0].name == "impossible"


def test_provider_declining_matches_a_no_advance_label() -> None:
    # No evidence -> heuristic returns None -> that satisfies expect_advance=False.
    case = CalibrationCase(
        name="no_evidence",
        record=OpportunityRecord(
            id="opp_e",
            title="t",
            problem="p",
            audience="a",
            source=SourceRef(connector="hackernews"),
            evidence=[],
            signals=None,
        ),
        expect_advance=False,
    )
    report = run_calibration([case], HeuristicSignalProvider())
    assert report.accuracy == 1.0
