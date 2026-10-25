# HomeFromWorking listing image improvement plan

Prepared September 8, 2026. Status: proposed plan; no listing edits or image generation performed. Objective: help buyers understand the design, garment, options, and sizing, while establishing an economical repeatable gallery workflow.

## Starting evidence and selection

The September 7 dashboard observation recorded 10 visits, 17 total views, and zero orders for its displayed seven-day range. These are historical observations, not today's totals or evidence of winning designs. The current Etsy snapshot omits image objects; 20 selected Printify mockups does not prove 20 live Etsy images. Refresh exact image IDs/order and current product mappings before choosing replacements.

Start with one complete prototype for the founder-selected snacks raccoon, Etsy `4570959040`. Its September 7 publication readback identifies a shirt-only listing linked to Printify `6a9f0ae10ea1dd638e082657`. Confirm it has not since been converted. This is separate from the older snacks sweatshirt listing.

Once the prototype is reviewed, expand to two more noncohort listings: provisionally Boo Sheet distressed `4567718416` (two recorded views, a very weak signal) and one evergreen candidate chosen from refreshed listing statistics and a visual audit. Prefer a different buyer theme for the evergreen slot. Boo Sheet cute `4567698241` is a fallback, not a second proven winner. Wombat watercolor `4568401115` requires identity verification before selection.

Prioritize observed relevant visits/favorites/orders where available, readable artwork at thumbnail size, verified offered products, a clear fixable gallery gap, and seasonal relevance. Do not fabricate scores from missing metrics. No duplicate Etsy listings are needed.

Exclude all eight frozen format-cohort IDs: `4568145936`, `4568131553`, `4567760813`, `4567775968`, `4567763906`, `4567763566`, `4568140935`, `4568411346`. Keep any listing undergoing founder-led multi-product conversion out of image rollout until its configuration is stable.

## Gallery template

This is a recommended sequence, not a requirement to remove useful existing images or fill every available slot. Preserve images linked to variation choices. Check live capacity before adding media.

| Position | Buyer question | Content |
| --- | --- | --- |
| 1 | What am I buying? | Accurate Printify front mockup of the actual garment, offered color, and saved artwork placement. Clear product, readable joke, generous crop margin; no collage or badges. |
| 2 | What does the design look like? | Same-color Printify Folded 2/alternate view where it genuinely reveals the design. A labeled artwork-detail panel is an alternative; never present enlarged source art as proof of physical ink or fabric quality. |
| 3 | Which product can I choose? | For multi-product listings, clearly labeled provider mockups of the actual tee, hoodie, and crewneck, with “Choose one item.” For shirt-only listings, an accurate provider model/alternate view if available. |
| 4 | Which colors are offered? | Actual enabled colors with exact option names. Retain separate linked color photos where needed. Verify color availability by size and product type. |
| 5–6 | Which size should I choose? | Readable provider-specific measurements in inches/cm and measuring instructions. Split by garment when needed; never apply the tee chart to a hoodie. |
| Next | How might this fit into my day? | One supplemental illustrative lifestyle scene, after factual product/fit information. |
| Next | How do I care for/order it? | Short card based on verified garment care and current fulfillment facts. Refer buyers to live delivery estimates; avoid dated promises or baked-in prices. |
| Remaining | Is there another useful view? | Necessary color-linked images, provider back views, and garment-specific details. Retain useful coverage; assess redundant images individually. |

For the raccoon, use the current lead color if it reads well. A proposed supplemental scene is a cozy reading nook with the shirt beside a small snack bowl and book. Keep the product and printed joke unobstructed; props are not included. A scene label should read “AI-assisted illustrative mockup — not a sample photo.” That label is our clarity standard, not quoted Etsy-mandated wording, and it cannot excuse an inaccurate garment.

## Asset quality and accuracy

Use original high-resolution provider assets. Target 3000 x 2250 landscape for newly composed cards where suitable; retain native provider aspect/resolution when better. Render information cards from vector text/shapes so typography stays crisp. Avoid enlarging low-resolution garment previews and calling them higher-detail images. Review Etsy's square, portrait, and landscape thumbnail crops plus mobile readability.

Use the garment/provider and print placement as the factual reference. AI must not invent a different collar, fit, fabric weight, sleeves, color, printing method, or design size. Never use an AI close-up as evidence of material/print quality. Prefer generating background/props only and preserving the provider product depiction. If an AI edit alters the garment, reject it; use another accurate provider mockup if a reliable scene cannot be produced. Physical samples remain deferred as requested.

The HomeFromWorking browser ChatGPT Project is the preferred place to generate the one scene, following the founder's existing preference. First inspect the existing session and repository artwork/mockup adapter instructions. Supply a compact brief and verified reference; save selected output and prompt in the repo. Do not assume browser generation is unlimited or that it removes all agent usage. Use at most two scene attempts initially; report a mismatch before spending on repeated retries.

## Execution and reusable process

1. Audit the raccoon first: current Etsy gallery, variation-photo links, Printify mockups, configuration, source resolution, measurements, and image provenance. Capture the baseline and create a contact sheet showing existing order and proposed order.
2. Build the prototype from existing provider assets plus reusable color/size/care card templates and at most one lifestyle scene. Create desktop/mobile previews and record each asset's purpose, source, hash, and garment/color mapping.
3. Present one concrete review pack: exact listing ID, ordered images, any removal/replacement, alt text, linked-photo preservation, and before/after gallery. Public application follows the user's approval of that concrete result.
4. Apply one listing and verify gallery order, hero crop, offered variants, option-photo links, and saved public display. Retain backups and recovery instructions; restored images may receive new IDs, so variation links must be reconciled rather than assuming rollback preserves IDs.
5. Refine the template from the first run, then prepare the two additional listings as one batch. Record founder review time, agent usage where available, browser actions, generation attempts, and total elapsed time. Make efficiency targets from measured first-run costs.
6. Codify the proven procedure in a reusable image-gallery adapter and lightweight manifest/helper using existing approval and receipt mechanisms. Avoid building a full new automation subsystem before the prototype works.

Use APIs for supported metadata/image reads and local assembly, and browser interaction for Printify selection and unsupported gallery controls. Existing Etsy tooling is read-only, and the last documented OAuth grant is `shops_r listings_r`; image writes are not already implemented. Etsy documents image uploads with write authorization. Evaluate an image-only API path after the first prototype: verify current endpoint behavior, scopes, ordering, capacity, and variation mapping. Keep existing read-only tools read-only; any future write helper should have bounded inputs and recovery checks. A first small rollout can use the browser without waiting for that implementation.

Etsy custom gallery work must survive future Printify publication. Before each later sync, inspect available publishing selections and preserve custom photos where supported. Otherwise reapply the approved gallery from its saved manifest and verify it. Do not republish an entire multi-product payload merely to update photos. Record concurrent conversions in the change log.

## Measurement and rollout fit

Days 22–45: prototype, review, and first small image batch. Days 46–75: review at 7/14/30 days after each image change and refine the reusable process. Days 76–90: expand the template to more listings with observed demand and sound economics.

A full gallery refresh is one bundled merchandising intervention. It cannot identify which individual image caused a change. Preserve other major listing variables during observation; record unavoidable inventory changes, conversions, seasonality, and the recent shop-wide trust/banner updates. Keep new-listing age separate from gallery-change age, especially for the raccoon.

Use listing visits/views with their exact Etsy labels, orders, favorites when exposed, and sizing/product-choice questions. Calculate CTR only when corresponding impressions and clicks are actually available; never substitute shop visits. Review conversion only with a compatible denominator and date range. Low traffic means an inconclusive commercial result, not a failed image stack. Seven/14/30-day reviews are scheduling checkpoints, not statistical proof. The existing format-pilot threshold is not a significance threshold for this image project.

Success before meaningful traffic: accurate product depiction, readable thumbnails/cards, correct option mapping, no missing useful images, and a verified repeatable update. Later success: a sustained improvement consistent with buyer behavior and fewer product-choice questions, described as observational. Test alternative hero images separately after the gallery and traffic are stable.

## Founder involvement

Founder reviews the first contact sheet and scene, then approves the exact public gallery change. The agent can do inspection, asset preparation, factual checks, review packs, application within authorization, verification, and reporting. Only unresolved product facts, a required account consent, or a creative choice the agent cannot infer need founder input. No physical samples are required for this phase.

## Evidence and current sources

- Local: `state/home-from-working/operations/day-22-90-plan.md`, `pilot.json`, `contender-watchlist.md`, `shop-scorecard.md`, `raccoon-publication-readback-20260907.json`.
- Existing workflow: `docs/founder/printify-shirt-workflow.md`, `docs/founder/printify-multi-product-workflow.md`.
- [Etsy listing image requirements](https://www.etsy.com/legal/policy/listing-image-requirements/253962679005): permits stock mockups for original artwork printed by production partners onto base products; this is not blanket permission for inaccurate AI product depictions.
- [Etsy image quality and cropping](https://help.etsy.com/hc/en-us/articles/115015663347-Requirements-and-Best-Practices-for-Images-in-Your-Etsy-Shop).
- [Etsy variation photos](https://help.etsy.com/hc/en-us/articles/115015664047-Listing-Variations).
- [Etsy listing and image API tutorial](https://developers.etsy.com/documentation/tutorials/listings/).
