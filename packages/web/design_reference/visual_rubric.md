# Visual Quality Rubric — the Design Studio scorer

This rubric is how the **premium track** turns two screenshots into a pass/fail
verdict. An agent (or a person) looks at the captured desktop and mobile
full-page PNGs and scores each category **0–5** against the anchors below, then
writes a `scores.json`. `scripts/agency/design_studio.py review` feeds those into
`review_visual_quality()` in [`packages/web/design_studio.py`](../design_studio.py).

This is deliberately a **taste fitness function**, not an a11y/HTML check — those
already run in `validation.py` and `ux_audit.py`. Here we only ask: *does this
look like work a studio could charge five figures for?*

## How scoring maps to the verdict

- **Overall** = mean of all category scores × 20 (so six 4/5 scores → 80/100).
- **Pass bar:** overall ≥ **80/100** AND every category ≥ **4/5**.
- **Critical categories** (a single 3 here fails the build, by code):
  `visual_thesis`, `hero_impact`, `imagery_art_direction`.
- Be a harsh grader. A 3 is "fine, shippable for a cold demo" — which is exactly
  what the premium track exists to reject. Reserve 5 for work you'd put in a
  portfolio. When unsure between two scores, pick the lower one.

## `scores.json` shape

```json
[
  {"category": "visual_thesis",          "score": 4, "note": "one-line why"},
  {"category": "hero_impact",            "score": 5, "note": "..."},
  {"category": "imagery_art_direction",  "score": 4, "note": "..."},
  {"category": "typography",             "score": 4, "note": "..."},
  {"category": "layout_composition",     "score": 4, "note": "..."},
  {"category": "copy_specificity",       "score": 5, "note": "..."}
]
```

Score **all six** categories. Every `note` must point at something concrete in
the screenshot ("hero is a centered stock photo with a gradient overlay"), not a
vibe. The note is the audit trail for why the build passed or failed.

---

## Categories & anchors

### `visual_thesis` — is there one memorable idea? *(critical)*
Does the page commit to a single concept you could describe in one sentence, and
does every section serve it? This is the #1 separator between a template and a
custom build.
- **0–1** No idea. Generic section stack that could belong to any business.
- **2–3** A theme is implied (a color, a tagline) but the layout doesn't commit;
  it reads as a nicer template.
- **4** A clear concept you can name, carried through hero, sections, and imagery.
- **5** A concept so specific and well-executed it becomes the brand. Removing it
  would collapse the page.

### `hero_impact` — does the first screen feel expensive? *(critical)*
Judge the top viewport alone. Would it stop a scroll on Dribbble?
- **0–1** Default heading + paragraph + button on a flat background.
- **2–3** Tidy and readable but forgettable; centered text over a plain or stock image.
- **4** Composed hero — deliberate type scale, real focal image or scene,
  intentional negative space, a single confident CTA.
- **5** Presentation-worthy. Strong focal composition, type/image tension,
  atmosphere (depth, light, texture, or motion implied by layout).

### `imagery_art_direction` — is the image system cohesive and owned? *(critical)*
- **0–1** Obvious mismatched stock, or empty/placeholder image boxes.
- **2–3** Decent photos but inconsistent crop, color, or lighting; they don't feel
  like one shoot.
- **4** Images share one crop/color/lighting logic and express the concept.
- **5** Art-directed: bespoke or curated imagery (incl. concept-led generated
  sets) that looks commissioned for this business and this page.

### `typography` — is the type distinctive and well-set?
- **0–1** One default system font, flat scale, no hierarchy.
- **2–3** Safe sans stack; hierarchy present but timid; cramped or loose spacing.
- **4** Distinctive display face paired with a clean body; clear scale contrast;
  controlled measure and rhythm.
- **5** Type *is* part of the art direction — confident scale jumps, precise
  tracking/leading, editorial detail (labels, numerals, pull quotes).

### `layout_composition` — varied rhythm, not a stacked template?
- **0–1** Identical full-width centered blocks top to bottom.
- **2–3** Mostly uniform cards/grids; little asymmetry or spatial interest.
- **4** Varied section rhythm — asymmetry, bento/editorial moments, deliberate
  whitespace, alignment to a real grid.
- **5** Composition itself carries meaning; layout surprises without breaking
  usability. Mobile is recomposed, not just reflowed.

### `copy_specificity` — grounded and concrete, or filler?
- **0–1** Lorem/scaffold tokens, or fabricated claims/awards/testimonials.
- **2–3** Generic marketing speak ("quality you can trust") with no specifics.
- **4** Specific, evidence-grounded copy: real services, real proof, concrete CTA.
- **5** Every line earns its place and is sourced from real business evidence; no
  claim that couldn't be defended.

---

## Reviewer procedure (for the agent)

1. Open `design-studio/screenshots/desktop.png` and `mobile.png`.
2. Read `design-studio/packet.md` — score against the concept the packet set, not
   a generic ideal. (Did the build deliver the intended thesis?)
3. Score all six categories with concrete notes. Grade down on doubt.
4. Write `design-studio/scores.json` and run
   `python scripts/agency/design_studio.py review --target <dir> --scores design-studio/scores.json`.
5. If it fails, the notes are the revision brief. Fix the build and re-capture —
   don't re-score the same pixels hoping for a different number.
