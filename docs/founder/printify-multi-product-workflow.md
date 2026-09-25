# HomeFromWorking: repeatable Printify Multi-Product Listing drafts

Convert one published Etsy-linked Printify product into a Multi-Product Listing, add reviewed product formats, and stop at an unpublished Printify draft. This extends the [repeatable shirt workflow](printify-shirt-workflow.md); it does not replace the single-shirt draft process.

**Current rollout policy (2026-09-07):** run new conversions in small, receipted waves outside the frozen eight-listing format cohort. The default expansion is the existing shirt plus one hoodie and one crewneck. The verified 12-product pilot below remains useful browser/recovery evidence, but it is not the default assortment for the 90-day rollout. A multi-product listing adds buyer choice; it must not be represented as creating multiple independently searchable Etsy listings.

Verified with the Wombat Poop Black and White pilot on September 3–4, 2026. The pilot retained the existing Etsy-linked shirt as the primary product, expanded the group to 12 products, rebalanced the gallery to one mockup per product (12/20 selected), and remained unpublished.

## What the feature creates

Printify creates one Multi-Product Listing around the existing Etsy-linked product. The group has one Etsy-facing title, description, tag set, mockup gallery, category, shipping profile, and product-type selector. Each item inside the group remains an individual Printify product with its own provider, variants, price, artwork placement, mockups, title, and product-specific description.

Printify's UI says conversion keeps the existing Etsy listing, reviews, and SEO. The [official Multi-Product Listing guide](https://help.printify.com/hc/en-us/articles/45606975744529-How-can-I-create-a-Multi-Product-Listing-on-Etsy) documents a limit of 20 products, 400 variants, and 70 options in one listing. Personalization is not supported. Product variation names must be distinct.

The public [Printify API](https://developers.printify.com/) and its OpenAPI schema do not expose Multi-Product Listing creation, conversion, membership, ordering, shared copy, or combined mockup selection. Use the signed-in browser for those operations. Use the public API afterward to inspect every underlying product ID, its variants, prices, artwork, and Etsy linkage.

## Approval boundary

The owner's request to run a named pilot or convert named listings authorizes reversible Printify draft work. Save the result as a draft. Publishing or synchronizing the expanded listing to Etsy remains a separate action and requires explicit approval. Do not change product prices unless the owner separately requests that pricing change.

## Preflight

1. Record the source Printify product ID, title, Etsy linkage, enabled variants, prices, selected mockups, and primary mockup through the public API.
2. Confirm that the source is the intended published Etsy listing. The conversion entry appears under **More actions → Convert to Multi-Product Listing**.
3. Inspect the design's contrast, aspect ratio, transparent padding, and readable text. Choose only product colors and dimensions on which the artwork remains legible.
4. Choose the expansion products. The current pilot set is a Gildan 18500 hoodie, cotton canvas tote, kiss-cut sticker, vertical poster, ceramic mug, Gildan 5000B kids shirt, Rabbit Skins 3322 infant shirt, Gildan 64000 Softstyle shirt, Gildan 18000 crewneck, 8 × 10 stretched matte canvas, and 9 × 12 rolled poster. Change this set when the design or audience calls for different products.
5. Review providers and shipping costs before eventual publication. One Etsy shipping profile applies to every item in the listing even when Printify uses multiple providers.

## Browser procedure

1. In **My Products**, open the exact source row's three-dot menu and click **Convert to Multi-Product Listing** once. Wait for Printify's success message and record the new Multi-Product Listing UUID and URL. If the outcome is uncertain, reconcile the Multi-Product Listings tab before clicking again.
2. Open the group and click **Add item**. Use **Add this design to another product** to create a component, or use **Your products** to search for and attach an already configured draft by its exact title. Add products one at a time or in a single unchanged search result; the picker does not retain earlier selections when its search term changes.
3. Save group membership before navigating into **Edit details**. Printify can lose unsaved membership changes when the component editor opens. The reliable order is: add the component, save the group membership, reopen the component editor, then configure it.
4. Open **Edit details → Edit design** for every added product. If the owner already resized and positioned the design, record those values and inspect the mockup before changing anything. Otherwise, select the artwork, click **Fit to placeholder**, center it horizontally and vertically, and inspect the reported inches, scale, and DPI. Adjust if needed for the product's print area; never reuse one scale across products. Restrict variants, then click **Save product** to return to that component's details page.
5. On the component's details page, write the product-specific title and description and click **Save as draft**. Reopen the Multi-Product Listing before configuring the next component.
6. Restrict variants deliberately. A black design should not be offered on dark garments where it disappears. Do not leave every default color or poster size enabled simply because Printify selected it.
7. Give every item a short, distinct **Variation name for Etsy listing**, such as `Unisex Heavy Cotton Tee`, `Heavy Blend Hoodie`, or `11 oz Ceramic Mug`.
8. Replace the group's shared title and description with copy that accurately covers all included products. Keep the title within 140 characters and begin with `[Design name] Heavy Cotton T-Shirt` when the primary product is the standard shirt. List each product's material, size choices, intended use, and any relevant limitation in the shared description.
9. Replace shirt-only tags with up to 13 terms that describe the design and the range of products. Keep each Etsy tag within 20 characters.
10. Open **View all mockups** and build the shared gallery deliberately. For the current apparel workflow, keep exactly 8 shirt, 6 hoodie, and 6 crewneck images in that order. The final image in each product block is its white size chart. Keep the shirt primary and folded mockups the same color, rotate the primary shirt color between listings, and mix product-only and human-model scenes across the remaining slots. Use the three product-name buttons at the top of Printify's mockup library to switch between the shirt, hoodie, and crewneck native libraries; do not upload generated component files when these native selectors are available. Wait about one second between selections. Confirm both `20/20 selected` and 20 visibly rendered tiles; if the counter claims 20 while only 8 render, click **Clear all** and rebuild the full ordered set.
11. Keep **Only show in-stock variants and hide any out-of-stock variants** unless the owner requests another policy. Review the shared shipping warning. Do not publish.
12. Click **Save as draft**. Confirm the Multi-Product Listings tab shows the expected product count (three for the current shirt + hoodie + crewneck workflow) and `Unpublished` status.

## Current three-apparel profile

Use these exact enabled colors for the current template cohort:

- Gildan 5000 shirt: Light Blue, Natural, Military Green, White, Black, Sand, Gold, Orange, Light Pink, Sport Grey.
- Gildan 18500 hoodie: Ash, Sport Grey, White, Black, Military Green, Light Pink, Sand, Charcoal, Light Blue, Indigo Blue.
- Gildan 18000 crewneck: Irish Green, Light Blue, Light Pink, Sand, Sport Grey, White, Black, Gold, Indigo Blue, Ash.

Use the approved retail-price ladders on every enabled color variant, not only the visible size summary row:

- Shirt: S–XL $17.99; 2XL $19.99; 3XL $20.99; 4XL–5XL $21.99.
- Hoodie: S–XL $27.99; 2XL $29.99; 3XL $32.99; 4XL $35.99; 5XL $38.99.
- Crewneck: S–XL $29.99; 2XL $32.99; 3XL $34.99; 4XL $36.99; 5XL $38.99.

Printify can leave legacy prices on only some color-size variants while the collapsed size row looks correct. After saving, inspect the underlying products through the public API and compare the complete enabled-variant color set and retail-price set with this profile. A mixed price set or an eleventh color is a failed draft and must be corrected before review.

## Placement rules from the first pilot

These are design-specific starting points, not universal product presets. The pilot artwork was a 1024 × 1536 transparent PNG with a 2:3 aspect ratio. Every product received its own fit, scale, and DPI review; never copy a transform between products.

| Product | Enabled variants | Placement result | Effective DPI shown by Printify |
|---|---|---|---|
| Gildan 5000 shirt | White, S–5XL | Existing reviewed shirt placement | Existing product |
| Gildan 18500 hoodie | White, S–5XL | 5.32 × 7.98 in, 155.79%, left 27.79%, top 0 | 192 |
| Cotton canvas tote | Natural, 15 × 16 in | 8 × 12 in, 234.38%, left 10%, top 0 | 128 |
| Kiss-cut sticker | White vinyl, 2/3/4/6 in | 1.85 × 2.77 in, 54.16%, left 16.67%, top 0 | 276 |
| Matte vertical poster | Matte, 8 × 12 in only | 8.04 × 12.06 in, 235.53%, left 0.12%, top 0 | 127 |
| Ceramic mug | White, 11 oz | 2.49 × 3.73 in, 72.91%, left 36.17%, top 0 | 411 |
| Gildan 5000B kids shirt | White, XS–XL | 8 × 12 in, 234.38%, left 9.36%, top 0 | 127 |
| Rabbit Skins 3322 infant shirt | White, 6M–24M | 4.6 × 6.9 in, 134.77%, left 2.23%, top 0 | 222 |
| Gildan 64000 Softstyle shirt | White, S–4XL | 10.41 × 15.62 in, 305%, left 15.3%, top 4.07% | 98 → 300 enhancement |
| Gildan 18000 crewneck | White, S–5XL | 10.41 × 15.62 in, 305%, left 15.3%, top 4.07% | 98 → 300 enhancement |
| Stretched matte canvas | 8 × 10 in vertical, 1.25 in depth | Owner placement retained: 7.18 × 10.77 in, 210.36%, left 5.12%, top -1.51%; white background; no side printing | 142 |
| Rolled poster | 9 × 12 in vertical; Fine Art, Matte, and Semi Glossy | Owner placement retained: 8.4 × 12.6 in, 246.14%, left 3.63%, top -0.47%; white background | 121 |

The poster was restricted to 8 × 12 because the source ratio matches it and the larger default sizes reduced the reported resolution as low as 35 DPI. Select poster sizes from the source artwork's aspect ratio and effective DPI; do not copy this exact size restriction when a future file supports larger formats. The hoodie, tote, sticker, poster, mug, kids shirt, infant shirt, Softstyle shirt, and crewneck each required independent placement review.

For apparel, the owner's current large-placement trial targets approximately 305% and 98 DPI when the complete design fits safely. Printify reports an automatic enhancement to 300 DPI, but that message does not make a low-resolution source equivalent to native 300-DPI artwork. For mugs, posters, stickers, and bags, prioritize complete composition and readable text over a fixed percentage.

## Copy rules

- Save product-specific titles and descriptions on each underlying product. Describe only enabled colors, sizes, materials, and use cases. Product descriptions were entered through each component's Edit details flow during the pilot.
- Write a separate shared description on the Multi-Product Listing. Explain how to choose the product type and disclose that products from different providers can ship separately.
- Keep the HomeFromWorking production-partner sentence and an artwork-provenance disclosure that matches the actual design.
- Never claim a product is waterproof, dishwasher-safe, oversized, or available in a color or size unless its current Printify details support the claim.
- Preserve the component copy and the final group copy in the run directory under `state/home-from-working/multi-product-listings/`.

## Shipping and pricing review

Printify warns that products from different providers are produced and shipped separately. Etsy applies one shipping price to the order through the group's single shipping profile. Before publication, compare the profile against each product's actual shipping charge and decide whether to include some shipping cost in product prices. The [Printify multiple-item shipping guide](https://help.printify.com/hc/en-us/articles/4483643971473-How-are-shipping-costs-calculated-for-multiple-items) explains why products from different providers can incur separate shipping charges.

Newly added products may start with Printify's default margin. Draft creation does not authorize a pricing decision. Record those prices in the receipt and review them separately before the expanded Etsy listing is published.

## Verification and receipt

After saving the group:

1. Reopen the Multi-Product Listing and confirm the shared title, description, 13 tags, variation names, product count, mockup count, shipping warning, and unpublished status.
2. Run `.venv/bin/python scripts/pod_draft.py inspect --product-id PRODUCT_ID` for the primary product and every added component. Confirm the primary remains Etsy-linked and each added product remains unlinked until the group is published.
3. Compare enabled variants, every enabled variant's retail price, selected product mockups, and artwork transforms with the reviewed choices. Do not accept the collapsed pricing row as sufficient evidence; use the public API to detect hidden per-color legacy prices. Visually inspect at least one preview per product.
4. Save a `receipt.json` with the group UUID, component IDs, copy, variation names, placements, variant restrictions, prices, warnings, and `etsy_publish_requested: false`.
5. Refresh the existing shirt catalog with `.venv/bin/python scripts/pod_catalog.py`. The current catalog builder indexes verified shirt runs; component descriptions and current API verification live in this Multi-Product Listing's run directory.

The first pilot receipt is at `state/home-from-working/multi-product-listings/wombat-black-white-20260903/receipt.json`. It records the 12 product members, one-per-product mockup selection (12/20), per-item transforms, restricted variants, copy, warnings, and `etsy_publish_requested: false`.

## Recovery and token discipline

Reuse the recorded Multi-Product Listing URL and underlying product IDs. Do not reconvert the source, rebuild an added product because one field is wrong, or repeat broad Printify research on each design. Fix the specific component, save it, return to the existing group, and run the verification checklist again.

When scaling this to many published listings, process one listing at a time until shipping, pricing, categories, and Etsy variation behavior have been reviewed on the pilot. Browser work remains necessary for Multi-Product Listing operations; compact API inspections and saved receipts handle reconciliation and future lookup.
