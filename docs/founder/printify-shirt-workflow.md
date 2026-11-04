# HomeFromWorking: repeatable Printify shirt drafts

Use native Duplicate once, replace the front artwork in Printify, then use the reusable command to apply listing copy and verify the copied product settings.

Verified September 4, 2026. This is an operated draft workflow, not unattended publication. Start here for the next owner-selected shirt; broader product research is deferred.

After a shirt has been published to Etsy, use the separate [Multi-Product Listing workflow](printify-multi-product-workflow.md) when the owner wants to offer the same design on additional product types under that Etsy listing.

## Why this process

The first Witch shirt was reconstructed through API product creation. That reused editable product settings but did not perform Printify's native clone, which caused unnecessary preview-photo selection in the browser.

Printify's [public API](https://developers.printify.com/) and [OpenAPI schema](https://developers.printify.com/openapi.json) have no duplicate operation or writable mockup-selection/order interface. Product `images` are read-only. Printify's [native Duplicate action](https://help.printify.com/hc/en-us/articles/4483625856017-How-do-I-duplicate-products-in-Printify) preserves variants, prices, description, mockups, and provider settings.

A disposable native duplicate was first tested with an API artwork replacement: all selected mockups, their sequence, and the primary photo survived. Evidence is in `state/home-from-working/workflow-validation/20260902-native-clone/receipt.json` and adjacent snapshots.

The current multicolor template includes a Printify-created inner-neck `text_layer.svg`. Printify's public API returns that layer but rejects it when the product's print areas are resubmitted. For this template, replace only the front artwork in the signed-in Printify editor, then use `prepare-copy` and `apply-copy`. Those commands verify the browser-placed artwork and update only title, description, and tags, so the neck layer is never resubmitted. The September 4 four-shirt batch verified the full process with 49 enabled variants, 20 selected mockups, individual lead colors, and unchanged prices. Evidence is in `state/home-from-working/drafts/go-with-the-flow-20260904/batch-verification.json`.

Retention through artwork updates is observed behavior, not a promise in the public API documentation. The helper verifies it on every run. Selection metadata returned by this shop is also not fully described in the published schema; missing or changed metadata stops the run for inspection.

## Reuse this template

| Setting | Current reference |
|---|---|
| Shop | HomeFromWorking, `28779955` |
| Template | [Funny Earth](https://printify.com/app/product-details/6a9860cc0bf15ba9490bfe3a), `6a9860cc0bf15ba9490bfe3a` |
| Garment | Gildan 5000, blueprint `6` |
| Provider | Printify Choice, provider `99` |
| Enabled colors | White, Sport Grey, Charcoal, Black, Sand, Natural, Light Blue, Light Pink |
| Enabled variants | 49 available color/size combinations, S–5XL where offered |
| Prices | S–XL $17.99; 2XL $19.99; 3XL $20.99; 4XL–5XL $21.99 |
| Mockups | 20 selected; matching-color Front and Folded 2 are first and second |
| Artwork | One replaceable front image plus the preserved inner-neck `text_layer.svg` |

The template is now linked to Etsy. **Always duplicate it; never apply the draft runner to the template itself.** Resolve a different template only when the owner requests a different configuration. Read current prices from the template; do not recalculate or hardcode a price ladder for each new shirt. Native duplication generates fresh SKUs, which subsequent API updates preserve.

## Per-shirt procedure

1. **Intake.** Use the owner's PNG and requested concept. Prepare a design-specific title, short introduction, and up to 13 Etsy tags. Start every new title with **`[Design name] Heavy Cotton T-Shirt`**, followed by descriptive keywords; for example, `Boo Sheet Heavy Cotton T-Shirt, Cute Ghost Halloween Tee, Funny Spooky Season Graphic`. Keep the full title within 140 characters. This is the owner's standing title preference; existing listings are being corrected manually and should not be renamed as part of a new-draft run. Keep the garment/care/disclosure portion of the existing description. Confirm its disclosure still accurately describes the new artwork's provenance. The owner's explicit request to create this draft authorizes that work; do not ask again for the same permission. Publication remains a separate action.
2. **Native Duplicate, once.** Through the supported signed-in browser tool, locate the exact Funny Earth template in My Products and click its Duplicate action. Record the new product ID from the resulting row or product URL. Confirm it differs from the source and is unlinked. If the click result is uncertain, reconcile the new row/ID before clicking again. Do not use public API `POST products` as a substitute or call private browser endpoints.
3. **Replace the front artwork.** Open the duplicate in Printify's editor, upload the exact PNG, add it to the front, set it to **305%**, center it at **50% horizontal / 50% vertical**, delete the old Earth front image, and leave the inner-neck layer unchanged. Check that the complete image fits the printable area without cropping and record any automatic size cap. Save the product as a draft. For a 1024 × 1536 PNG, the expected saved API scale is about `0.790573`, and the editor reports approximately 98 DPI with Printify enhancement to 300 DPI.
4. **Prepare using `prepare-copy`.** It reads the template and draft, validates the native clone, confirms the exact local PNG name/dimensions and browser placement, and writes an exact review revision. It makes no Printify writes and never resubmits print areas. If preflight fails, resolve the stated mismatch before proceeding.
5. **Record authorization through the existing platform.** Register the proposed pending request in `approval-request.json` through `ControlPlaneService.request_approval` or `POST /approvals`, passing its summary, subject type/ID, action, approval type, and review artifact path. Record the owner's actual authorization through the existing decision workflow, with `decided_by` and notes identifying the request. Do not invent approval, edit the status in a JSON file, or create a new permission prompt when the owner already authorized the exact draft. Pass the resulting shared approval ID to `apply-copy`. The runner cannot grant approval itself.
6. **Apply and verify listing copy.** `apply-copy` updates only title, description, and tags. It verifies that the draft is still unpublished and that the browser-placed artwork, print areas, selected mockups, variants, prices, provider, and settings did not change during the copy update. Keep the draft exclusive to the run until this finishes. The command never publishes.
7. **Choose the lead mockup pair.** In **View all mockups**, retain all 20 template mockups. Replace the template's Black Folded 2 selection with the chosen lead color's Folded 2. In the sortable Selected mockups list, put that color's flat **Front first** and **Folded 2 second**, then click **Save selection** and **Save as draft**. The first image must be the only default. Printify also makes that color's L variant the default; this is expected. Rotate lead colors evenly across a batch so every listing does not start with the same shirt color. Record the chosen lead color. The September 4 cycle was Sport Grey, Light Pink, Sand, and Light Blue.
8. **Final read-back and visual review.** Read the saved product through the API and confirm: unlinked/unpublished; 49 enabled variants; the original enabled variant IDs and prices; exactly 20 selected mockups; matching-color Front/Folded 2 in positions one/two; one default mockup; chosen-color L as the default variant; the exact artwork filename, centered placement and scale; and the inner-neck layer. Open the primary image plus the mockup grid to check readability and placement. Some back/close-up images naturally have no design.
9. **Refresh the saved catalog.** Save the final API product as the run's final snapshot, then run `.venv/bin/python scripts/pod_catalog.py` after the batch. Use `state/home-from-working/catalog/INDEX.md` to find previous designs and `catalog.json` for full saved descriptions, tags, artwork, placement, product details, and chosen lead colors. These are historical snapshots of our runs; manual Printify/Etsy edits made afterward are not automatically captured. Read the current product through the API when its latest configuration matters. Prepared or interrupted runs remain labeled separately from verified saves.

## Commands and inputs

Run from the repository root. Credentials come from macOS Keychain service `ai-company-os`, account `PRINTIFY_API_TOKEN`; the token stays out of command arguments, files, and logs.

This Keychain reference is for Printify only. Etsy API/OAuth credentials use
the repository-root `.etsy.env` exclusively; see
[Etsy credentials and OAuth](etsy-credentials.md). Do not apply the Printify
credential rule to Etsy.

```sh
.venv/bin/python scripts/pod_draft.py inspect
```

For each design, make a new runtime directory such as `state/home-from-working/drafts/go-with-the-flow/` and save `copy.json` there:

```json
{
  "title": "Go With The Flow Otter Heavy Cotton T-Shirt, Cute River Animal Tee, Nature Lover Gift",
  "intro": "A peaceful otter floats downriver beside uplifting Go With The Flow lettering.",
  "tags": ["go with the flow", "otter shirt", "nature lover gift", "positive quote tee"]
}
```

The examples below contain placeholders. Replace the draft ID, PNG path, and approval ID with the verified values for that run.

```sh
.venv/bin/python scripts/pod_draft.py prepare-copy \
  --draft-id NEW_NATIVE_COPY_ID \
  --artwork /absolute/path/to/design.png \
  --copy state/home-from-working/drafts/go-with-the-flow/copy.json \
  --run-dir state/home-from-working/drafts/go-with-the-flow \
  --scale-percent 305

.venv/bin/python scripts/pod_draft.py apply-copy \
  --run-dir state/home-from-working/drafts/go-with-the-flow \
  --approval-id SHARED_PLATFORM_APPROVAL_ID
```

`prepare-copy` creates `template.json`, `before.json`, `review.json`, and a **proposed pending** `approval-request.json`. `apply-copy` loads the real decision from the shared ApprovalStore and requires `approval_type=pod_draft_update`, `subject_type=pod_manifest`, the exact review revision, and `action=update_printify_draft`.

### Larger-placement standard

The owner requested approximately **305% in the Printify editor / 98 DPI** for new shirt drafts. Pass `--scale-percent 305` to `prepare-copy`. This is an explicit sizing option; omitting it preserves the earlier 8 × 12-inch calculation. Do not retroactively resize existing products.

At 300 DPI, editor percentage maps to `original pixels × percentage / 100 / 300` inches. A 1024 × 1536 PNG at 305% is about **10.41 × 15.62 inches at 98.4 DPI**. The public API's `scale` is a different number: printed width divided by the print area's width. The helper converts between them and records the requested percentage, applied percentage, inches, and DPI in the approved review. This is now the default requested placement for new owner-selected shirt drafts; pass `--scale-percent 305` explicitly so the review records it.

Percentage placement is centered horizontally and vertically. If 305% would extend outside the 3951 × 4919-pixel print area, the helper reduces the percentage uniformly to fit the complete image without cropping. For example, a 1536 × 1024 landscape image is capped at about **257.23%, 13.17 × 8.78 inches, 116.6 DPI**. Report a cap to the owner rather than claiming every image reached 305%.

Live verification on `breathing-manually-1` showed **304.97%**, **10.41 × 15.61 inches**, and **98 DPI → 300 DPI enhancement** in the editor (minor display rounding). All six trial drafts retained 14 mockups and their existing variants/prices. Evidence: `state/home-from-working/drafts/science-humor-20260903/batch-verification.json` and the first draft's `editor-verification.json`. Transparent padding is included in the percentage calculation, so visible artwork can differ in size between files; report significant padding instead of silently cropping or modifying originals.

Use the original PNG pixels. [Printify says it automatically enhances low-resolution print files before production](https://help.printify.com/hc/en-us/articles/4483601444113-How-do-I-get-a-high-quality-design-file), with limits to the improvement; this does not certify native 300-DPI artwork. The existing template's editor was observed displaying “Resolution will be enhanced (97 DPI → 300 DPI).” Confirm the resulting layer dimensions/DPI when first validating a new sizing mode, then retain the normal one-preview review per draft.

Successful `prepare-copy` / `apply-copy` execution saves `update-request.json`, `after.json`, and `receipt.json`; there is no API upload. Save a fresh final snapshot after changing the lead mockups. Account/runtime snapshots stay under `state/`; do not commit them or recreate this code in a per-shirt scratch script.

## Placement and supported scope

- Use one PNG with its original pixels and transparency. The public-API `prepare` route accepts up to 5 MiB; the browser-upload plus `prepare-copy` route accepts up to Printify's 100 MiB browser limit. No automatic background removal, flattening, or upscaling.
- By default, artwork fits within **8 × 12 inches**, preserving aspect ratio, horizontally centered with a 5% top inset on the tested Gildan 5000 / provider 99 print area (3951 × 4919 pixels at 300 DPI). The explicit `--scale-percent` option uses the centered larger-placement mode described above.
- Effective DPI is reported for review. For example, 1024 × 1536 at 8 × 12 inches is **128 DPI**. A successful API save does not certify physical print quality.
- Exactly one image on the front plus the template's unchanged inner-neck `text_layer.svg`; back and sleeve locations stay empty. Do not include the neck layer in a public API update request.
- On every native duplicate, remove the copied old front artwork so the new draft contains only the selected new front image. This is standing owner intent and does not require a new design-choice approval for each draft; still obey any runtime policy that requires action-time confirmation for the destructive browser click.
- Native draft copies legitimately omit `external`; shipping linkage on the published source is not proof of linkage on the draft. The helper compares the available product settings and preserves reported draft shipping metadata. Verify the actual shipping profile when preparing publication.
- New garment/provider configurations, multiple artwork layers, personalization, and Etsy-only attributes require an explicit extension of this workflow. This command does not update Etsy or publish a listing.

## Recovery and token discipline

Reuse the same run directory after a failure. An approved revision is tied to the exact file hash, target ID, copy, placement, and baseline. Changing those inputs requires a new review revision. Run directories and cached upload receipts are trusted local operating state, created with restrictive permissions, not signed attestations against a local owner editing files. Do not edit receipts to make a check pass or substitute artwork IDs. Invoke the CLI: it loads the decision from ApprovalStore; the underlying Python functions accept injected dependencies for testing and are not an authorization boundary against arbitrary local Python code.

If an upload result is uncertain, the saved attempt marker stops automatic re-upload; reconcile Printify's upload library before proceeding. If an update succeeded but its response was lost, a retry reads the draft and recognizes the applied result instead of sending the update again. Never recreate the product to recover a failed update.

Use compact API summaries for routine checks. Do not re-research Printify, inventory all Etsy listings, generate a fresh script, or walk through every browser setting per design. Browser work is limited to **native Duplicate, front-art replacement, lead-pair selection, and one visual review**. A failed preservation check warrants targeted investigation, not silent manual rebuilding.

## Implementation and verification

- CLI: `scripts/pod_draft.py`
- API orchestration: `packages/pod/runner.py`
- Clone/placement/preservation checks: `packages/pod/template.py`
- Shared approval policy: `packages/policies/pod.py`
- Tests: `tests/python/unit/test_pod_runner.py`, `tests/python/unit/test_pod_template.py`, `tests/python/unit/test_pod_catalog.py`

```sh
.venv/bin/pytest tests/python/unit/test_pod_runner.py tests/python/unit/test_pod_template.py tests/python/unit/test_pod_catalog.py -q
```

The live experiment validates the native Duplicate/API behavior; offline tests validate the reusable command's guards and recovery. No further live test product is needed just to rerun those tests.

## Launch strategy overlay — September 6, 2026

This document remains the authoritative procedure for an owner-selected single-shirt draft. The Day 1–21 launch plan adds a commercial gate before that procedure starts:

- Blanket multi-product conversion is paused. A single shirt with size/color variations remains the default.
- The only proposed product-format experiment is six matched shirt-only controls versus six shirt, hoodie, and crewneck treatments. `state/home-from-working/operations/pilot.json` is a proposal, not publication approval.
- Launch shipping is $4.95 buyer-paid U.S. standard shipping. Do not enable a free-shipping guarantee or absorb unverified multi-item shipping.
- Offsite Ads are opted out while optional, but economics must remain contribution-positive under a 15% stress case.
- Current 1024 × 1536 source art may be usable with Printify enhancement, but it does not meet the new production-master gate. Regenerate only evidence-qualified pilot assets; do not upscale the whole catalog by default.
- The existing long title format remains historical/current workflow behavior. Concise title v2 (fewer than 15 words) is allowed only in its separate controlled cohort after the Etsy CSV is backed up.
- Etsy API work is read-only until linked-draft mapping is proven. No registry, score, Project chat, or OAuth token grants publication authority.

Operational source of truth: `state/home-from-working/operations/README.md`. Implementation design: `docs/plans/2026-09-06-home-from-working-days-1-21-design.md`.
