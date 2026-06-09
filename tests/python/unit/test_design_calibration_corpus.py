"""Integrity of the judge calibration corpus (design engine v3 — Phase 2).

The live `calibrate` run needs a Gemini key; here we lock that the gold corpus on
disk is well-formed and its referenced screenshots exist, so a drift check can't
silently no-op on a broken corpus. The harness logic itself is covered by
`test_web_design_loop.py::test_calibration_detects_judge_drift`.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
GOLD = REPO / "products" / "better-business-web" / "portfolio" / "calibration" / "gold.json"


def test_gold_corpus_is_well_formed_and_resolvable() -> None:
    samples = json.loads(GOLD.read_text())
    assert len(samples) >= 3, "calibration corpus should have a few samples to have teeth"
    seen_ids = set()
    for sample in samples:
        assert sample["id"] not in seen_ids, f"duplicate gold id {sample['id']}"
        seen_ids.add(sample["id"])
        assert sample["expected"] in ("good", "bad")
        shots = sample["screenshots"]
        assert {"desktop", "mobile"}.issubset(shots), sample["id"]
        for path in shots.values():
            assert (REPO / path).exists(), f"{sample['id']} references missing {path}"


def test_corpus_can_catch_a_too_lenient_judge() -> None:
    # Today every sample is below the five-figure bar (expected "bad"), so the corpus
    # has teeth against a judge that rates generic work as passing.
    samples = json.loads(GOLD.read_text())
    assert any(s["expected"] == "bad" for s in samples)
