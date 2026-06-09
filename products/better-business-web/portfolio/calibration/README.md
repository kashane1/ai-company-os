# Judge calibration corpus

`gold.json` is the gold-standard set the **independent Gemini judge** is re-scored
against to catch **drift** (design engine v3, Phase 2). Run:

```
python scripts/agency/design_loop.py calibrate --gold products/better-business-web/portfolio/calibration/gold.json
```

`calibrate()` (in `packages/web/design_loop.py`) re-scores each sample and compares
the pass/fail verdict to its `expected` label. If a known-bad sample is judged
"good" (or vice versa), the judge has drifted → the loop halts rather than trust it.
Needs `GEMINI_API_KEY` (the judge is a live, non-Claude model).

## Sample shape

```json
{ "id": "...", "expected": "good" | "bad", "note": "why", "screenshots": {"desktop": "<path>", "mobile": "<path>"} }
```

Paths are **repo-root-relative** (run `calibrate` from the repo root). For
single-image references both `desktop` and `mobile` point at the same full-page PNG
— calibration tests the judge's *taste discrimination*, not responsive correctness.

## Status (2026-06-08) — honest

By the strict five-figure bar, **nothing currently in-repo clears the gate**, so the
starter corpus is all `expected: "bad"`. This already has teeth: it catches a judge
that's too lenient (rates a $500 template or a below-bar build as passing). It does
**not** yet catch a judge that's too harsh — that needs `expected: "good"`
exemplars, which get added when the **first flagship build clears the gate**
(Phase 5). When that happens, drop its desktop/mobile PNGs here labelled `"good"`.

(Third-party Awwwards screenshots are intentionally NOT committed here — licensing.
Good exemplars come from our own pass-grade builds.)
