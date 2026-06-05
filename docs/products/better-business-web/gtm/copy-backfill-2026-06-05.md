# Copy Backfill — 2026-06-05

One-time `copy-review` pass over copy that shipped *before* the voice system
existed: the live marketing site + all 8 published demos (plan Phase 3 backfill).

**Method:** the literal anti-slop gate from `voice.md`'s "Banned everywhere" list,
run over **caller-extracted visible prose** (`<style>`/`<script>`/tags stripped) —
not raw HTML. (A naive grep of raw HTML flagged 200+ hits, all CSS `transform:` /
SVG `transform=` — markup, not copy. This is exactly why `copy-review` judges
prose, not markup.) Judgment layer (em-dash budget, rhythm, constructions)
spot-checked; no systemic issues.

**Headline result:** marketing + 8/8 demos pass the literal gate. The first run of
the voice system confirms the existing copy is already largely on-voice (matches
`voice-calibration.md`). One demo (barbering) has two minor word-level fixes
queued at source.

| Surface | Verdict | Findings | Decision |
|---|---|---|---|
| Marketing — `LandingBody.astro` | ✅ pass | none | none |
| `portfolio.json` / `packages.json` (prose) | ✅ pass | none | none |
| auto-repair | ✅ pass | none | none |
| coffee | ✅ pass | none | none |
| dog-grooming | ✅ pass | none | none |
| gun-store | ✅ pass | none | none |
| nails | ✅ pass | none | none |
| plumbing | ✅ pass | none | none |
| baked-goods | ✅ pass (1 benign) | "not just" in *"a place to linger, not just grab-and-go"* — natural usage, **not** the banned "it's not just X, it's Y" construction | accept, no change |
| barbering | ⚠️ minor | "seamless" (*"blended clean and seamless from the skin up"*) + "bespoke" (*"quote anything bespoke before the first cut"*) — grounded craft terms, but both on the banned-everywhere list | **grandfather + follow-up:** fix at the `dist-v2/` source and rebuild the portfolio (`scripts/agency/build_portfolio_demos.py`). Do **not** hand-edit the generated `public/work/barbering/index.html` — it's regenerated, and is mid-webp-migration. Suggested: "seamless" → "clean", "anything bespoke" → "any custom work". |

**Follow-up (1):** barbering demo source copy — 2 word swaps, applied at `dist-v2/`
then re-run the portfolio build. Bounded; not a rebuild of the demo.
