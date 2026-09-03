# POD Artwork Generator Design

**Date:** 2026-09-03  
**Status:** Approved  
**Owner:** HomeFromWorking founder

## Goal

Create a reusable repo skill that turns a short merchandise-design idea into
several founder-cleared art directions, generated transparent PNG concepts, and
one inspected final artwork file. The workflow should work for shirts, mugs, and
other Printify products without requiring the founder to prescribe an art style.

## Decisions

- Call the capability **POD Artwork Generator** rather than “photo generator”
  because the supplied references span illustration, typography, engraving,
  gothic art, scientific graphics, and photoreal cutouts.
- Keep the canonical definition under `skills/canonical/pod-artwork-generator/`
  and provide a Codex adapter. Add a narrow route in `AGENTS.md` so future Codex
  sessions discover it from ordinary requests for shirt, mug, merchandise, or
  transparent print artwork.
- Require a style-direction checkpoint for every new design. Codex proposes
  three to five genuinely different directions, recommends the strongest fit,
  and waits for founder clearance before generating any image.
- Default to four directions when the founder does not specify a count. The
  founder may approve one or several directions for generation.
- Use the built-in image-generation path by default. Generate one image per
  approved direction rather than treating a batch as one prompt.
- Store project-bound working outputs under
  `state/home-from-working/artwork/<design-slug>/<run-id>/` and never overwrite
  an existing final without explicit replacement instructions.
- Do not copy the supplied reference PNGs into the repository. Preserve the
  useful visual vocabulary in a maintained style-direction reference instead.

## Workflow

1. Read the idea, exact wording when present, target product when known, and any
   stated constraints. Ask one concise question only when a missing fact would
   materially change the design.
2. Propose three to five art-direction cards. Each card names the direction and
   describes its medium, mood, palette, composition, typography treatment,
   product fit, and reason it suits the idea. Make the set meaningfully diverse,
   not palette swaps of one layout.
3. Stop for founder clearance. Do not generate images from uncleared directions,
   even when the request asks for speed or asks Codex to skip questions.
4. Generate one transparent PNG concept for each cleared direction. Keep the
   idea and exact wording stable while varying the approved visual treatment.
5. Show the concepts with clear labels. The founder selects a concept, requests
   a targeted revision, or returns to art direction.
6. Refine the selected concept and inspect the final file. Confirm that it has
   actual transparent pixels and visible artwork, clean isolated edges, no
   rectangular backdrop or mockup, no unintended crop, readable and exact text,
   and acceptable behavior on light, dark, and neutral previews.
7. Report the final path, dimensions, alpha result, exact prompt, and any
   product-specific limitation. A successful image-generation response alone is
   not a print-readiness claim.

## Product Adaptation

When the target product is unknown, create an isolated master composition and
state the assumed orientation. Once a product is chosen, preserve the approved
art direction but recompose when its print area needs a different aspect ratio.
In particular, do not stretch a shirt design into a mug wrap. Use product-native
layouts while retaining the same concept and visual language.

## Style Vocabulary

The supplied examples establish useful starting families: retro mascot and
halftone, cute character art, monochrome engraving, ornate gothic, photoreal
cutout, cinematic science/fact graphic, and bold type-forward minimalism. These
are a menu, not a mandatory set. Codex chooses directions that fit the specific
idea and may introduce other commercially suitable treatments.

## Boundaries

This skill creates and inspects artwork only. It does not upload to Printify,
modify a draft, create an Etsy listing, change prices, or publish anything. The
existing repeatable Printify workflow begins only after the founder selects the
final artwork, and its product/publication approval gates remain separate.

## Verification

- Run baseline scenarios without the new skill to identify natural behavior
  gaps, especially skipped style clearance, weak product adaptation, and casual
  transparency assumptions.
- Add happy-path, boundary, and adversarial behavioral fixtures.
- Validate the canonical contract and registry reconciliation.
- Run the same scenarios with the completed skill and confirm it proposes style
  directions, stops for clearance, preserves exact wording, validates real
  transparency, and refuses unapproved external actions.

### RED-phase baseline observed

An independent agent without this skill accepted the rush instruction and said,
“I’ll pick four distinct print-friendly directions and generate them now.” For a
mug reference it chose one direction and would “generate one
horizontal/landscape design,” without a clearance checkpoint or provider safe-area
validation. For the Printify request it planned to “upload it to Printify as a
draft” after making its own subjective choice. Across the three cases,
transparency and exact wording were visually assumed rather than checked against
the file. These are the concrete gaps the skill must close.
