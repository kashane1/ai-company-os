from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/agency/run_conversion_lab.py")


def test_run_conversion_lab_prepare_and_render(tmp_path: Path) -> None:
    page_copy = tmp_path / "page.txt"
    page_copy.write_text("Book a consultation today.", encoding="utf-8")

    prepare = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "prepare",
            "--root",
            str(tmp_path),
            "--product-id",
            "smooth-med-spa-site",
            "--vertical",
            "med_spa",
            "--target-action",
            "booking",
            "--url",
            "https://example.com",
            "--page-copy-file",
            str(page_copy),
            "--run-id",
            "2026-06-11-001",
        ],
        check=True,
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )
    prepared = json.loads(prepare.stdout)
    run_dir = Path(prepared["run_dir"])

    assert (run_dir / "INPUT.json").exists()
    assert (run_dir / "PROMPTS.md").exists()
    assert "Book a consultation today." in (run_dir / "PROMPTS.md").read_text(encoding="utf-8")

    reviews = tmp_path / "reviews.json"
    reviews.write_text(
        json.dumps(
            {
                "product_id": "smooth-med-spa-site",
                "vertical": "med_spa",
                "scorecard": {
                    "clarity": 7,
                    "trust": 5,
                    "offer_strength": 6,
                    "friction": 4,
                    "local_relevance": 8,
                    "conversion_action": 6,
                },
                "persona_reviews": [
                    {
                        "persona_id": "nervous-first-time-buyer",
                        "likely_action": "hesitate",
                        "objections": ["No pricing context"],
                        "trust_gaps": ["No provider credentials"],
                        "useful_rewrites": ["Add consultation reassurance"],
                        "clarity_notes": ["The consultation CTA is visible"],
                        "confidence": "medium",
                    }
                ],
                "top_blockers": ["Pricing is unclear"],
                "top_trust_gaps": ["Credentials are buried"],
                "recommended_rewrites": {
                    "Hero": "Feel confident before your first treatment."
                },
                "confidence_label": "medium",
            }
        ),
        encoding="utf-8",
    )

    render = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "render",
            "--root",
            str(tmp_path),
            "--product-id",
            "smooth-med-spa-site",
            "--run-id",
            "2026-06-11-001",
            "--reviews-json",
            str(reviews),
        ],
        check=True,
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )
    rendered = json.loads(render.stdout)

    report = Path(rendered["report"])
    assert report == run_dir / "REPORT.md"
    assert "Conversion Lab Report" in report.read_text(encoding="utf-8")
