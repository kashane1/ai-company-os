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
corpus is now **two-sided**: the known-`"bad"` legacy/below-bar samples catch a judge
that's too lenient, and `flagship-med-spa-pass` — the **first flagship that cleared
the gate live (87/100)** — catches one that's too harsh. Add more `"good"` exemplars
as future flagships pass.

(Third-party Awwwards screenshots are intentionally NOT committed here — licensing.
Good exemplars come from our own pass-grade builds.)
