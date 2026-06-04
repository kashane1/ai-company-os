# Font pairing reference (curated)

Display + body pairings grouped by vibe, curated from UI UX Pro Max
`google-fonts.csv` (MIT — see `ATTRIBUTION.md`). All families are Google Fonts;
the **weights listed are verified present** in the source's `Styles` column, so a
`@fontsource` import or a CSS2 URL using exactly these weights will resolve. For
production, **self-host via `@fontsource` / `@fontsource-variable`** (no FOUT, no
Google tracking) per the craft-pass; CDN is fine for a quick preview.

> Pick by the vibe the human chose in `03-design-direction.md`. Heading carries
> personality; body stays clean and legible. Don't request a weight not listed.

| Vibe | Display (heading) | Weights | Body | Weights | Fits |
|---|---|---|---|---|---|
| industrial | Oswald | 500, 600, 700 | Inter | 400, 500, 600 | auto, garage door, roofer |
| trades | Archivo | 600, 700, 800 | Inter | 400, 500, 600 | plumber, electrician, HVAC |
| vintage | Oswald | 600, 700 | Inter | 400, 500 | barber shop |
| elegant | Playfair Display | 500, 600, 700 | Inter | 400, 500 | beauty/nail salon |
| elegant-alt | Cormorant Garamond | 500, 600, 700 | Mulish | 400, 500, 600 | salon, boutique |
| warm | Fraunces | 400, 500, 600, 700 | Nunito | 400, 600, 700 | bakery, restaurant |
| warm-alt | Lora | 500, 600, 700 | Inter | 400, 500 | coffee shop, cafe |
| playful | Fredoka | 500, 600, 700 | Nunito | 400, 600 | dog groomer, kids, music |
| calm | Spectral | 400, 500, 600 | Inter | 400, 500 | massage, yoga, wellness |
| friendly | Poppins | 500, 600, 700 | Inter | 400, 500 | tutoring, childcare |
| friendly-alt | Manrope | 600, 700, 800 | Inter | 400, 500 | general SMB, modern |
| professional | Sora | 600, 700 | Inter | 400, 500 | accountant, notary, legal |
| professional-alt | Spectral | 500, 600 | Inter | 400, 500 | accountant (serif authority) |

**Pairing rules**
- Strong size contrast between heading and body; tighten display tracking.
- Tabular/lining numerals for prices, hours, phone numbers.
- One display + one body is enough — a third family rarely helps.
- Variable fonts (Fraunces, Inter, Archivo, Oswald, Manrope, Sora, Lora) let you
  pick intermediate weights, but for self-hosted **static** instances only ship
  the weights above.
