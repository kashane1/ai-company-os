# Better Business Web V2 Landing Design

## Goal

Replace the current Better Business Web homepage with a v2 landing page while preserving the existing homepage as `/v1`.

## Direction

V2 should feel like a dark aquatic, dimensional operating console for a small-business web studio. The page should borrow the vertical editorial rhythm from the `layout_idea` reference: oversized type, offset image panels, narrow decorative rails, and sections that feel like a scrolling portfolio sequence rather than a conventional SaaS stack.

The color system should lean into the provided palette:

- Abyssal teal: `#063F47`
- Deep cyan: `#195F60`
- Pale mist: `#CBECEF`
- Near-black: `#0B0405`

The 3D reference should influence surface treatment: beveled buttons, inset highlights, deep shadows, lifted dashboard panels, and a central preview object with depth. The styleguide reference should inform tokenization and reusability rather than literal content.

## Page Structure

1. Hero: large promise, concise supporting copy, two CTAs, and a dimensional central studio preview.
2. Proof strip: compact metrics that reinforce turnaround, no-upfront-payment, and industry breadth.
3. Scrollytelling sections: three offset feature bands for preview-first build, conversion clarity, and launch support.
4. Package lab: a reusable dimensional card grid for the current offer ladder.
5. Closing CTA: direct invitation to request a free review.

## Implementation Notes

- Preserve v1 by copying the current homepage to `src/pages/v1.astro`.
- Keep v2 content data-driven in `src/data/landing-v2.mjs`.
- Put the new reusable page UI in `src/components/LandingV2.astro`.
- Keep page-level wiring in `src/pages/index.astro`.
- Avoid touching unrelated legal/footer edits already present in the worktree.

## Verification

- Run `npm run check` from `products/better-business-web/site`.
- Run `npm run build` from `products/better-business-web/site`.
- Start the Astro dev server and open the local homepage in the in-app browser.
- Inspect desktop and mobile widths for text fit, overlapping UI, and visual depth.
