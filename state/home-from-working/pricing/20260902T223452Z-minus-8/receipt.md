# HomeFromWorking — $8 T-shirt price reduction

Completed 2026-09-02 through the Printify public API for shop `28779955`.
The user explicitly authorized reducing every listed T-shirt size by $8.
Authentication used macOS Keychain service `ai-company-os`, account
`PRINTIFY_API_TOKEN`, through `packages.config.secrets`; no token was stored here.

## Result

Five products, 40 enabled size variants, each reduced exactly 800 cents from
`before.json`. All 552 disabled variants per product retained their original
prices and disabled state. All five products already had visible Etsy listings
when this operation began; no new listing was published.

| Shirt | Printify ID | Existing Etsy ID |
| --- | --- | --- |
| Currently Avoiding Something | `6a989820c07f91a2ff0aa2b8` | `4567628531` |
| List of Lists | `6a988f0a00aa8684080e906c` | `4567628456` |
| Minimalist Astronomy | `6a98877e4ac00e7da5019a50` | `4567593986` |
| Shrimp Fried This Rice | `6a9880c14ac00e7da501950b` | `4567588636` |
| Photographic Earth | `6a9860cc0bf15ba9490bfe3a` | `4567549394` |

| Size | New retail price |
| --- | --- |
| S, M, L | $15.99 |
| XL | $15.99, except Minimalist Astronomy $16.99 (previously $24.99) |
| 2XL | $17.99 |
| 3XL | $18.99 |
| 4XL, 5XL | $19.99 |

## Verification

- Retrieved every product after the write and after sync; every enabled variant
  matched its original price minus $8. Retained every SKU, size/color selection,
  default variant, artwork asset and placement, mockup, description, title, tag,
  shipping setting, and external listing ID.
- Sent five publish requests with only `variants: true`; title, description,
  images, tags, key features, and shipping profile sync were false.
- All five API products returned unlocked and visible after synchronization.
  Printify's product list independently showed all five as **Published**.
- Printify's astronomy pricing table showed profit estimates $6.15 for S/M/L,
  $7.06 for XL, $6.42 for 2XL, $6.40 for 3XL, $6.83 for 4XL, and $6.86 for 5XL.
  The exact requested $8 cut therefore does not reach $5–$6 profit on every size.

## API behavior observed

Product updates require the complete variant list. The script submitted only
variant ID, SKU, price, enabled state, and default state. It uses the fixed
baseline, so repeating it does not subtract another $8.

Printify regenerates a renderer `imageId` on reads and normalizes print-area
defaults from `background: transparent` to absent and `font_color: auto` to
`#000` on these white shirts. Verification excludes those equivalent defaults
while checking actual artwork asset IDs, per-layer font colors, and placement.

The system Python lacked a working default CA bundle; using certifi with normal
certificate verification resolved the connection. Product-list limit is 50
maximum; the default paginated endpoint was used after a rejected limit of 100.

The per-product request, response, verification, and sync files provide the
original and resulting values. Do not apply another relative reduction unless
the user requests a new price change.
