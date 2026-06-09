# Visual Quality Rubric (v3) — the Design Studio scorer

This rubric turns a build's captures into a pass/fail verdict. The **independent
Gemini judge** (`packages/web/gemini_judge.py`) — a different model family from the
Claude builder — scores each category **0–5** against the anchors below from the
desktop + mobile full-page PNGs **plus a sequence of scroll-frame captures (motion
enabled)**, and writes a `scores.json`. `scripts/agency/design_studio.py review`
feeds those into `review_visual_quality()` in
[`packages/web/design_studio.py`](../design_studio.py).

This is a **taste + motion fitness function**, not an a11y/perf/HTML check — those
run in `validation.py` and `ux_audit.py` (performance + accessibility are gated
there, not here). Here we only ask: *does this look like work a studio could charge
five figures for, and does it move like it?*

## How scoring maps to the verdict

- **Overall** = mean of all category scores × 20 (so twelve 4/5 scores → 80/100).
- **Pass bar:** overall ≥ **80/100** AND every category ≥ **4/5**.
- **Critical categories** (a single 3 here fails the build, by code):
  `visual_thesis`, `hero_impact`, `imagery_art_direction`, `ai_house_style`.
- Be a harsh grader. A 3 is "fine, shippable for a cold demo" — which is exactly
  what the premium track exists to reject. Reserve 5 for portfolio-grade work.
  When unsure between two scores, pick the lower one.

> **v3 note.** Awwwards juries weight Design 40 / Usability 30 / Creativity 20 /
> Content 10. We approximate that target with an **equal per-category floor + a
> critical gate** rather than weighted averaging — strictly *harder* to pass (a
> weak dimension can't be compensated by a strong one), and less fragile to score.
> Weighted aggregation is a possible later refinement.

## `scores.json` shape

```json
[
  {"category": "visual_thesis",        "score": 4, "note": "one-line why"},
  {"category": "hero_impact",          "score": 5, "note": "..."},
  {"category": "imagery_art_direction","score": 4, "note": "..."},
  {"category": "typography",           "score": 4, "note": "..."},
  {"category": "color_system",         "score": 4, "note": "..."},
  {"category": "layout_composition",   "score": 4, "note": "..."},
  {"category": "whitespace_depth",     "score": 4, "note": "..."},
  {"category": "motion_quality",       "score": 4, "note": "..."},
  {"category": "signature_moment",     "score": 4, "note": "..."},
  {"category": "conversion_strength",  "score": 4, "note": "..."},
  {"category": "copy_specificity",     "score": 5, "note": "..."},
  {"category": "ai_house_style",       "score": 5, "note": "..."}
]
```

Score **all twelve**. Every `note` must point at something concrete (a font-family,
a hex, a DOM/scroll observation), not a vibe — the note is the audit trail.

---

## Categories & anchors

### `visual_thesis` — is there one memorable idea? *(critical)*
Does the page commit to a single concept you could describe in one sentence, and
does every section serve it? The #1 separator between a template and a custom build.
- **0–1** No idea; generic section stack that could belong to any business.
- **2–3** A theme is implied (a color, a tagline) but the layout doesn't commit; reads as a nicer template.
- **4** A clear concept you can name, carried through hero, sections, and imagery.
- **5** A concept so specific and well-executed it becomes the brand; removing it would collapse the page.

### `hero_impact` — does the first screen feel expensive? *(critical)*
Judge the top viewport alone. Would it stop a scroll on Dribbble?
- **0–1** Default heading + paragraph + button on a flat background.
- **2–3** Tidy and readable but forgettable; centered text over a plain or stock image.
- **4** Composed hero — deliberate type scale, real focal image or scene, intentional negative space, one confident CTA.
- **5** Presentation-worthy. Full-bleed/treated imagery, type *over* image, atmosphere (depth, light, texture, motion).

### `imagery_art_direction` — is the image system cohesive and owned? *(critical)*
- **0–1** Mismatched stock, or empty/placeholder image boxes.
- **2–3** Decent photos but inconsistent crop/color/lighting; they don't feel like one shoot.
- **4** Images share one crop/color/lighting logic and express the concept.
- **5** Art-directed: bespoke or curated imagery (incl. concept-led generated sets), one full-bleed moment, looks commissioned for this business.

### `typography` — is the type distinctive and well-set?
- **0–1** One default system font, flat scale, no hierarchy.
- **2–3** Safe sans stack; hierarchy present but timid; cramped or loose spacing.
- **4** Distinctive display face paired with a clean body; clear scale contrast; controlled measure and rhythm.
- **5** Type *is* art direction — confident 3×+ scale jumps, precise tracking/leading, editorial detail (labels, numerals, pull quotes).

### `color_system` — dominant color + sharp accent, deliberate?
- **0–1** Off-brand or default; purple→violet "aurora" regardless of business.
- **2–3** Timid, even palette; no clear accent; light/dark feels accidental.
- **4** A dominant brand color + one sharp accent, used consistently, AA-clear.
- **5** A color world with a point of view; deliberate light/dark; accent deployed with restraint for emphasis.

### `layout_composition` — varied rhythm, not a stacked template?
- **Defect cap:** if any section is a near-duplicate of another (the same hero
  image or headline shown twice down the page), score **2 or lower** and say so —
  a repeated section is a build defect, not "rhythm".
- **0–1** Identical full-width centered blocks top to bottom; or a section repeated.
- **2–3** Mostly uniform cards/grids; little asymmetry or spatial interest.
- **4** Varied section rhythm — asymmetry, bento/editorial moments, deliberate whitespace, alignment to a real grid.
- **5** Composition carries meaning; intentional asymmetry/overlap on a disciplined baseline grid; mobile recomposed, not just reflowed.

### `whitespace_depth` — does it breathe, and is there real depth?
- **0–1** Cramped or arbitrary gaps; everything coplanar with hairline borders.
- **2–3** Consistent-ish spacing but flat; one reused glow/shadow as the only depth.
- **4** A consistent spacing scale; sections breathe; real elevation/layering (shadows, overlap, foreground/background separation).
- **5** Spacing creates tension (compression/expansion); layered depth and overlap make the page feel built, not stacked.

### `motion_quality` — cohesive, restrained motion? *(judge from scroll frames)*
- **0–1** No motion, or scattered random fade-ins; a bouncing scroll-mouse indicator; visible jank.
- **2–3** Some reveals but generic/uniform; motion doesn't feel designed.
- **4** A cohesive motion language (shared easing/durations); smooth scroll; scroll-linked reveals that serve content.
- **5** Choreographed motion — staggered reveals, parallax/pin used purposefully, micro-interactions; restraint over spectacle; reads 60fps.

### `signature_moment` — one unforgettable on-concept moment? *(judge from scroll frames)*
- **0–1** Nothing memorable; indistinguishable from a template.
- **2–3** One mild flourish, but generic or off-concept.
- **4** A distinct moment (a WebGL hero, a kinetic reveal, a bespoke transition) that fits the concept.
- **5** One unforgettable, on-concept interaction executed flawlessly — the thing you'd remember and describe.

### `conversion_strength` — does it sell?
- **0–1** Buried or missing CTA; no value prop; unearned stat bar.
- **2–3** A CTA exists but the offer is vague; proof is decorative, not placed to persuade.
- **4** Sharp offer, clear primary CTA, social proof placed for persuasion, low friction.
- **5** A confident conversion path — offer + CTA hierarchy + proof choreographed so the next action is obvious and earned.

### `copy_specificity` — grounded and concrete, or filler?
- **0–1** Lorem/scaffold tokens, or fabricated claims/awards/testimonials.
- **2–3** Generic marketing speak ("quality you can trust") with no specifics.
- **4** Specific, evidence-grounded copy: real services, real proof, concrete CTA.
- **5** Every line earns its place and is sourced from real business evidence; brand-voiced; no claim that couldn't be defended.

### `ai_house_style` — free of the cheap/AI "tells"? *(critical)*
Score 5 only if the page avoids the generic-AI house style. Each tell present
drives the score down; **several tells → 0–2**.
The tells: default sans used flat · purple/indigo "aurora" gradient background ·
multi-color gradient headline text · three-boxes-with-icons feature grid ·
centered-everything hero · glassmorphism everywhere · one radius + one 0.1-opacity
shadow on everything · floating fake stat/social-proof bar · bouncing scroll-mouse
indicator · fake dashboard/analytics mockup · generic copy ("transform your
workflow") · functional hollowness (no hover/focus states, no form validation).
- **0–1** Three or more tells; unmistakably AI-generated house style.
- **2–3** One or two prominent tells.
- **4** No prominent tells; a couple of safe defaults.
- **5** Zero tells; the page reads as deliberately art-directed by a human studio.

---

## Reviewer procedure (for the agent doing it by hand)

1. Open `design-studio/screenshots/desktop.png`, `mobile.png`, and any
   `frames/` scroll captures.
2. Read `design-studio/packet.md` — score against the concept the packet set, not a
   generic ideal. (Did the build deliver the intended thesis?)
3. Score all twelve categories with concrete notes. Grade down on doubt.
4. Write `design-studio/scores.json` and run
   `python scripts/agency/design_studio.py review --target <dir> --scores design-studio/scores.json`.
5. If it fails, the notes are the revision brief. Fix the build and re-capture —
   don't re-score the same pixels hoping for a different number. (The autonomous
   loop `design_loop.py run` does this revise-and-recapture for you.)
