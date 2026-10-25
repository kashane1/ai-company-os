from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
CATALOG = REPO / "state/home-from-working/catalog/catalog.json"
# Runtime state under state/ is git-ignored, so these checks run only on the operator Mac.
requires_local_state = pytest.mark.skipif(
    not CATALOG.exists(), reason="requires local HomeFromWorking runtime state"
)


@requires_local_state
def test_generation_creates_manual_worksheet_sections_and_provisional_concepts(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/home_from_working_opportunities.py",
            "--catalog",
            "state/home-from-working/catalog/catalog.json",
            "--output-root",
            str(tmp_path),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "70 listings" in result.stdout
    with (tmp_path / "marketplace-insights-template.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 15
    assert all(not row["searches_30d"] and not row["competing_listings"] for row in rows)

    sections = json.loads((tmp_path / "sections.json").read_text())
    assert sum(len(section["listing_keys"]) for section in sections["sections"].values()) == 70
    assert "exception" in sections["sections"]

    concepts = json.loads((tmp_path / "opportunities/scored-concepts.json").read_text())
    assert len(concepts["concepts"]) == 29
    hang_in_there = next(
        concept
        for concept in concepts["concepts"]
        if concept["candidate_id"] == "hang-in-there-20260902/hang-in-there"
    )
    assert len(hang_in_there["source_record_keys"]) == 3
    assert all(concept["score"]["status"] == "blocked_unknown_hard_gate" for concept in concepts["concepts"])
    assert all(concept["score"]["eligible"] is False for concept in concepts["concepts"])
    assert all(concept["score"]["weighted_score"] is None for concept in concepts["concepts"])


@requires_local_state
def test_completed_insights_are_imported_without_overwriting_and_affect_ranking(
    tmp_path: Path,
) -> None:
    insights = tmp_path / "completed-insights.csv"
    insights.write_text(
        "query,observed_at,searches_30d,competing_listings,related_queries,trend,dominant_visual_pattern,price_band_usd,buyer_occasion,notes\n"
        "breathing manually shirt,2026-09-06,1000,10000,science joke;rabbit hole,rising,bold text,$20-$30,self purchase,manual observation\n"
        "encouragement shirt,2026-09-06,10,100000,,flat,animals,$15-$25,gift,manual observation\n"
    )
    original = insights.read_text()
    output_root = tmp_path / "output"

    subprocess.run(
        [
            sys.executable,
            "scripts/home_from_working_opportunities.py",
            "--catalog",
            "state/home-from-working/catalog/catalog.json",
            "--output-root",
            str(output_root),
            "--insights",
            str(insights),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert insights.read_text() == original
    payload = json.loads((output_root / "opportunities/scored-concepts.json").read_text())
    breathing = next(
        concept for concept in payload["concepts"]
        if "breathing-manually" in concept["candidate_id"]
    )
    assert breathing["marketplace_evidence"]["matched_queries"] == [
        "breathing manually shirt"
    ]
    assert breathing["score"]["factor_scores"]["buyer_demand"] == 85.0
    assert breathing["score"]["factor_scores"]["competitive_room"] == 25.0
    assert breathing["score"]["status"] == "blocked_unknown_hard_gate"
    assert breathing["evidence_rank"] is not None
    assert breathing["objective_evidence_coverage"] == 0.45
    assert breathing["evidence_qualified"] is False
    assert payload["founder_review_shortlist"] == []


@requires_local_state
def test_generation_does_not_use_design_folder_or_partial_words_for_query_evidence(
    tmp_path: Path,
) -> None:
    insights = tmp_path / "completed-insights.csv"
    insights.write_text(
        "query,observed_at,searches_30d,competing_listings,related_queries,trend,dominant_visual_pattern,price_band_usd,buyer_occasion,notes\n"
        "funny cat shirt,2026-09-06,3200,208400,,falling,text,$15-$25,gift,manual\n"
        "halloween work shirt,2026-09-06,157,17200,,falling,text,$15-$25,gift,manual\n"
        "funny astronomy shirt,2026-09-06,33,9800,,falling,text,$15-$25,gift,manual\n"
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/home_from_working_opportunities.py",
            "--catalog",
            "state/home-from-working/catalog/catalog.json",
            "--output-root",
            str(tmp_path / "output"),
            "--insights",
            str(insights),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads((tmp_path / "output/opportunities/scored-concepts.json").read_text())
    caterpillar = next(
        concept
        for concept in payload["concepts"]
        if concept["candidate_id"] == "motivation-animal-shirts-20260904/turning-leaf"
    )
    steak = next(
        concept
        for concept in payload["concepts"]
        if concept["candidate_id"] == "witch-venus-steak-20260902/chicken-fried-steak"
    )
    assert caterpillar["marketplace_evidence"]["matched_queries"] == []
    assert steak["marketplace_evidence"]["matched_queries"] == []
