#!/usr/bin/env python3
"""Generate HomeFromWorking's manual Etsy research worksheet and provisional backlog.

This script performs no Etsy access. Marketplace Insights data must be entered by
the founder in Etsy's seller tool, then imported through the opportunity package.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.home_from_working.opportunities import (
    FACTOR_WEIGHTS,
    MARKETPLACE_COLUMNS,
    SECTION_LABELS,
    HardGates,
    classify_listing,
    marketplace_factor_scores,
    parse_marketplace_insights,
    score_candidate,
)

# These queries deliberately combine broad buyer intent with the shop's strongest
# concepts. They are the first 15 manual searches named in the launch audit.
MARKETPLACE_QUERIES = (
    "funny work from home shirt",
    "funny coworker shirt",
    "coworker gift shirt",
    "breathing manually shirt",
    "funny raccoon shirt",
    "snack lover shirt",
    "funny cat shirt",
    "cat pun shirt",
    "wombat poop shirt",
    "animal fact shirt",
    "science humor shirt",
    "funny astronomy shirt",
    "motivational animal shirt",
    "encouragement shirt",
    "halloween work shirt",
)


def _load_records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError(f"{path} does not contain a records list")
    return [record for record in records if isinstance(record, dict)]


def _title(record: dict[str, Any]) -> str:
    copy = record.get("copy")
    if isinstance(copy, dict) and isinstance(copy.get("title"), str):
        return copy["title"]
    return str(record.get("key", "Untitled concept"))


def _concept_id(record: dict[str, Any]) -> str:
    design = str(record.get("design") or "unassigned")
    variant = str(record.get("variant") or str(record.get("key", "unknown")).rsplit("/", 1)[-1])
    variant = re.sub(r"-\d+$", "", variant)
    return f"{design}/{variant}"


def _concept_label(title: str) -> str:
    label = re.split(r"\s+(?:Heavy Cotton|Shirt,|Watercolor|Black and White|3D Cartoon)", title, maxsplit=1)[0]
    return label.strip(" ,") or title


def _heuristic_factors(section: str) -> dict[str, float | None]:
    """Score only non-market, non-live attributes; see output provenance."""
    return {
        "buyer_demand": None,
        "competitive_room": None,
        "buyer_clarity": 65.0 if section != "exception" else 35.0,
        "brand_fit": 75.0 if section != "exception" else 20.0,
        "visual_differentiation": 40.0,
        "product_fit": 50.0,
    }


def _write_worksheet(path: Path) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=MARKETPLACE_COLUMNS)
        writer.writeheader()
        for query in MARKETPLACE_QUERIES:
            writer.writerow({column: query if column == "query" else "" for column in MARKETPLACE_COLUMNS})


def _load_insights(path: Path) -> list[Any]:
    with path.open(encoding="utf-8") as stream:
        return parse_marketplace_insights(stream)


def generate(
    *,
    catalog_path: Path,
    output_root: Path,
    insights_path: Path | None = None,
) -> tuple[int, int]:
    records = _load_records(catalog_path)
    output_root.mkdir(parents=True, exist_ok=True)
    opportunities_dir = output_root / "opportunities"
    opportunities_dir.mkdir(parents=True, exist_ok=True)
    worksheet_path = output_root / "marketplace-insights-template.csv"
    if not worksheet_path.exists():
        _write_worksheet(worksheet_path)
    evidence_path = insights_path or worksheet_path
    insights = _load_insights(evidence_path)

    sections: dict[str, dict[str, Any]] = {
        code: {"label": label, "listing_keys": [], "assignments": []}
        for code, label in SECTION_LABELS.items()
    }
    concept_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in sorted(records, key=lambda item: str(item.get("key", ""))):
        title = _title(record)
        key = str(record.get("key", ""))
        assignment = classify_listing(title=title, key=key)
        section = sections[assignment.primary]
        section["listing_keys"].append(key)
        section["assignments"].append(
            {
                "key": key,
                "title": title,
                "secondary": assignment.secondary,
                "rationale": assignment.rationale,
                "confidence": assignment.confidence,
            }
        )
        concept_records[_concept_id(record)].append(record)

    sections_payload = {
        "schema_version": 1,
        "source": str(catalog_path),
        "method": "deterministic keyword classification; exceptions are intentionally retained",
        "sections": sections,
    }
    (output_root / "sections.json").write_text(json.dumps(sections_payload, indent=2) + "\n")

    concepts: list[dict[str, Any]] = []
    for candidate_id, members in sorted(concept_records.items()):
        lead = members[0]
        title = _title(lead)
        assignment = classify_listing(title=title, key=str(lead.get("key", "")))
        factors = _heuristic_factors(assignment.primary)
        marketplace = marketplace_factor_scores(
            insights,
            candidate_text=f"{title} {str(lead.get('key', '')).rsplit('/', 1)[-1]}",
            section=assignment.primary,
        )
        factors["buyer_demand"] = marketplace["buyer_demand"]
        factors["competitive_room"] = marketplace["competitive_room"]
        score = score_candidate(candidate_id, HardGates(None, None, None, None), factors)
        objective_evidence_coverage = sum(
            FACTOR_WEIGHTS[name] / 100
            for name in ("buyer_demand", "competitive_room")
            if factors[name] is not None
        )
        concepts.append(
            {
                "candidate_id": candidate_id,
                "label": _concept_label(_title(lead)),
                "section": assignment.primary,
                "source_record_keys": [str(member.get("key", "")) for member in members],
                "marketplace_evidence": marketplace,
                "hard_gate_provenance": "unknown: no live IP clearance, production-master review, margin table, or policy review imported",
                "factor_provenance": {
                    "buyer_demand": f"manual Etsy Marketplace Insights from {evidence_path}",
                    "competitive_room": f"manual Etsy Marketplace Insights from {evidence_path}",
                    "buyer_clarity": "conservative deterministic shop-copy heuristic; not buyer evidence",
                    "brand_fit": "deterministic four-section assignment; not buyer evidence",
                    "visual_differentiation": "held conservative pending visual review",
                    "product_fit": "held conservative pending live product/economics review",
                },
                "score": score.to_dict(),
                "objective_evidence_coverage": round(objective_evidence_coverage, 4),
                "evidence_qualified": False,
                "evidence_qualification_status": (
                    "not_qualified: remaining weighted factors are deterministic heuristics "
                    "or pending review, and hard gates have not been imported"
                ),
                "evidence_rank": None,
            }
        )

    rankable = [
        concept
        for concept in concepts
        if concept["marketplace_evidence"]["evidence_complete"] is True
    ]
    rankable.sort(
        key=lambda concept: (
            -float(concept["score"]["available_points"]),
            str(concept["candidate_id"]),
        )
    )
    for rank, concept in enumerate(rankable, start=1):
        concept["evidence_rank"] = rank
    shortlist = [
        str(concept["candidate_id"])
        for concept in rankable
        if concept["score"]["eligible"] is True
        and concept["score"]["weighted_score"] is not None
    ][:3]
    concepts_payload = {
        "schema_version": 1,
        "status": "provisional",
        "method": (
            "Manual Marketplace Insights values are mapped deterministically; no counts are "
            "fabricated. Evidence rank does not bypass unknown hard gates."
        ),
        "marketplace_insights_source": str(evidence_path),
        "factor_weights": FACTOR_WEIGHTS,
        "founder_review_shortlist": shortlist,
        "concepts": concepts,
    }
    (opportunities_dir / "scored-concepts.json").write_text(json.dumps(concepts_payload, indent=2) + "\n")
    return len(records), len(concepts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("state/home-from-working/catalog/catalog.json"))
    parser.add_argument("--output-root", type=Path, default=Path("state/home-from-working/operations"))
    parser.add_argument(
        "--insights",
        type=Path,
        help="founder-completed Marketplace Insights CSV; defaults to the output worksheet",
    )
    args = parser.parse_args()
    listings, concepts = generate(
        catalog_path=args.catalog,
        output_root=args.output_root,
        insights_path=args.insights,
    )
    print(f"Generated worksheet, sections, and {concepts} provisional concepts from {listings} listings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
