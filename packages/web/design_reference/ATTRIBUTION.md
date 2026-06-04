# Attribution — design reference data

The palette, font-pairing, and UX-rule reference data in this directory is a
**curated subset** adapted from the **UI UX Pro Max** skill by Next Level Builder.

- **Source:** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
- **Source files:** `src/ui-ux-pro-max/data/colors.csv`, `google-fonts.csv`,
  `ux-guidelines.csv`
- **Source commit:** `b7e3af80f6e331f6fb456667b82b12cade7c9d35` (fetched 2026-06-04)
- **License:** MIT (see `LICENSE` in this directory — retained verbatim per the
  MIT "include the copyright notice in all copies or substantial portions").

## What we took, and what we changed

- We copied **only the ~15 industry palette rows** we map onto our local-SMB
  genres (not the full 161), the **weight/axis facts for ~20 Google Fonts** we
  reference, and the **high-severity accessibility / touch / forms rules**.
- Palettes are **remapped** from the source's SaaS-style "Product Type" keys onto
  our service-business genres (auto repair, plumber, bakery, salon, …). Some
  genres have no clean source match and use our own choice or the HSL synthesizer
  in `packages/web/palette.py`; those are noted inline.
- Hex values are reproduced as published (the source already documents WCAG
  adjustments in its `Notes` column). Re-validate against the actual text/bg
  tokens of any site before shipping.

## Precedence rule (important)

For **bespoke prospect demos** (`docs/demo-site-build-playbook.md`), the palette
is **derived from the business's own visual cues first** (storefront, signage,
logo, photos). This reference is a **fallback / enrichment**, never an override.
