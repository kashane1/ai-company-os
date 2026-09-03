# HomeFromWorking: repeatable Printify shirt drafts

Use native Duplicate once, then the reusable API command to replace artwork and listing copy while retaining the template's mockups, variants, and prices.

Verified September 2, 2026. This is an operated draft workflow, not unattended publication. Start here for the next owner-selected shirt; broader product research is deferred.

## Why this process

The first Witch shirt was reconstructed through API product creation. That reused editable product settings but did not perform Printify's native clone, which caused unnecessary preview-photo selection in the browser.

Printify's [public API](https://developers.printify.com/) and [OpenAPI schema](https://developers.printify.com/openapi.json) have no duplicate operation or writable mockup-selection/order interface. Product `images` are read-only. Printify's [native Duplicate action](https://help.printify.com/hc/en-us/articles/4483625856017-How-do-I-duplicate-products-in-Printify) preserves variants, prices, description, mockups, and provider settings.

A disposable native duplicate was tested with an API artwork replacement: all **14 selected mockups, their sequence, and the primary photo survived**. Visual inspection showed the new design rendered on the retained mockups. The test copy was deleted, the six original products were unchanged, and no publish request was made. Evidence is in `state/home-from-working/workflow-validation/20260902-native-clone/receipt.json` and adjacent snapshots.

Retention through artwork updates is observed behavior, not a promise in the public API documentation. The helper verifies it on every run. Selection metadata returned by this shop is also not fully described in the published schema; missing or changed metadata stops the run for inspection.

## Reuse this template

| Setting | Current reference |
|---|---|
| Shop | HomeFromWorking, `28779955` |
| Template | [Resting Witch Face](https://printify.com/app/product-details/6a98ae4aaa543bfeff0f8735), `6a98ae4aaa543bfeff0f8735` |
| Garment | Gildan 5000, blueprint `6` |
| Provider | Printify Choice, provider `99` |
| Enabled options | White, S–5XL; eight variants |
| Mockups | 14 selected; front is primary |
| Artwork | One front image; no back, sleeve, or neck artwork |

The template is now linked to Etsy. **Always duplicate it; never apply the draft runner to the template itself.** Resolve a different template only when the owner requests a different configuration. Read current prices from the template; do not recalculate or hardcode a price ladder for each new shirt. Native duplication generates fresh SKUs, which subsequent API updates preserve.

## Per-shirt procedure

1. **Intake.** Use the owner's PNG and requested concept. Prepare a design-specific title, short introduction, and up to 13 Etsy tags. Start every new title with **`[Design name] Heavy Cotton T-Shirt`**, followed by descriptive keywords; for example, `Boo Sheet Heavy Cotton T-Shirt, Cute Ghost Halloween Tee, Funny Spooky Season Graphic`. Keep the full title within 140 characters. This is the owner's standing title preference; existing listings are being corrected manually and should not be renamed as part of a new-draft run. Keep the garment/care/disclosure portion of the existing description. Confirm its disclosure still accurately describes the new artwork's provenance. The owner's explicit request to create this draft authorizes that work; do not ask again for the same permission. Publication remains a separate action.
2. **Native Duplicate, once.** Through the supported signed-in browser tool, locate the exact template in My Products and click its Duplicate action. Record the new product ID from the resulting row or product URL. Confirm it differs from the source and is unlinked. If the click result is uncertain, reconcile the new row/ID before clicking again. Do not use public API `POST products` as a substitute, private browser endpoints, or mockup reselection.
3. **Prepare using the command below.** It reads the source and copy, validates the clone, measures the PNG, calculates placement, and writes an exact review revision. It makes no Printify writes. If preflight fails, resolve the stated mismatch before uploading.
4. **Record authorization through the existing platform.** Register the proposed pending request in `approval-request.json` through `ControlPlaneService.request_approval` or `POST /approvals`, passing its summary, subject type/ID, action, approval type, and review artifact path. Record the owner's actual authorization through the existing decision workflow, with `decided_by` and notes identifying the request. Do not invent approval, edit the status in a JSON file, or create a new permission prompt when the owner already authorized the exact draft. Pass the resulting shared approval ID to `apply`. The runner cannot grant approval itself.
5. **Apply and verify.** The command uploads the exact PNG once, then updates only title, description, tags, and print areas on the copied draft. It checks the resulting artwork, selected mockups/order/primary, all variant prices/SKUs/flags, provider, and reported settings. Keep this draft exclusive to the run: no concurrent UI edits or publication until verification finishes. The client checks linkage immediately before updating, but the public API has no documented atomic draft-only update condition. The command itself never publishes.
6. **One visual review.** Open the new draft and inspect the primary image plus the mockup grid for readable text, expected placement, and regenerated artwork. Some back/close-up images naturally have no design. Do not reselect all photos when the retained set passes verification. Return the draft link and any material print-quality concern to the owner.
7. **Refresh the saved catalog.** Run `.venv/bin/python scripts/pod_catalog.py` after the batch. Use `state/home-from-working/catalog/INDEX.md` to find previous designs and `catalog.json` for full saved descriptions, tags, artwork, placement, and product details. These are historical snapshots of our runs; manual Printify/Etsy edits made afterward are not automatically captured. Read the current product through the API when its latest configuration matters. Prepared or interrupted runs remain labeled separately from verified saves.

## Commands and inputs

Run from the repository root. Credentials come from macOS Keychain service `ai-company-os`, account `PRINTIFY_API_TOKEN`; the token stays out of command arguments, files, and logs.

```sh
.venv/bin/python scripts/pod_draft.py inspect
```

For each design, make a new runtime directory such as `state/home-from-working/drafts/resting-witch-v2/` and save `copy.json` there:

```json
{
  "title": "Resting Witch Face Heavy Cotton T-Shirt, Funny Halloween Witch Graphic Tee",
  "intro": "A grumpy witch and bold Resting Witch Face lettering bring a little attitude to spooky season.",
  "tags": ["resting witch face", "witch shirt", "halloween shirt", "spooky season"]
}
```

The examples below contain placeholders. Replace the draft ID, PNG path, and approval ID with the verified values for that run.

```sh
.venv/bin/python scripts/pod_draft.py prepare \
  --draft-id NEW_NATIVE_COPY_ID \
  --artwork /absolute/path/to/design.png \
  --copy state/home-from-working/drafts/resting-witch-v2/copy.json \
  --run-dir state/home-from-working/drafts/resting-witch-v2

.venv/bin/python scripts/pod_draft.py apply \
  --run-dir state/home-from-working/drafts/resting-witch-v2 \
  --approval-id SHARED_PLATFORM_APPROVAL_ID
```

`prepare` creates `template.json`, `before.json`, `review.json`, and a **proposed pending** `approval-request.json`. `apply` loads the real decision from the shared ApprovalStore and requires `approval_type=pod_draft_update`, `subject_type=pod_manifest`, the exact review revision, and `action=update_printify_draft`.

### Larger-placement trial, September 3

The owner requested approximately **305% in the Printify editor / 98 DPI** for the September 3 science/humor batch. Pass `--scale-percent 305` to `prepare` for this mode. This is an explicit sizing option; omitting it preserves the earlier 8 × 12-inch behavior. Do not apply this trial to existing products.

At 300 DPI, editor percentage maps to `original pixels × percentage / 100 / 300` inches. A 1024 × 1536 PNG at 305% is about **10.41 × 15.62 inches at 98.4 DPI**. The public API's `scale` is a different number: printed width divided by the print area's width. The helper converts between them and records the requested percentage, applied percentage, inches, and DPI in the approved review.

Percentage placement is centered horizontally and vertically. If 305% would extend outside the 3951 × 4919-pixel print area, the helper reduces the percentage uniformly to fit the complete image without cropping. For example, a 1536 × 1024 landscape image is capped at about **257.23%, 13.17 × 8.78 inches, 116.6 DPI**. Report a cap to the owner rather than claiming every image reached 305%.

Live verification on `breathing-manually-1` showed **304.97%**, **10.41 × 15.61 inches**, and **98 DPI → 300 DPI enhancement** in the editor (minor display rounding). All six trial drafts retained 14 mockups and their existing variants/prices. Evidence: `state/home-from-working/drafts/science-humor-20260903/batch-verification.json` and the first draft's `editor-verification.json`. Transparent padding is included in the percentage calculation, so visible artwork can differ in size between files; report significant padding instead of silently cropping or modifying originals.

Use the original PNG pixels. [Printify says it automatically enhances low-resolution print files before production](https://help.printify.com/hc/en-us/articles/4483601444113-How-do-I-get-a-high-quality-design-file), with limits to the improvement; this does not certify native 300-DPI artwork. The existing template's editor was observed displaying “Resolution will be enhanced (97 DPI → 300 DPI).” Confirm the resulting layer dimensions/DPI when first validating a new sizing mode, then retain the normal one-preview review per draft.

Successful execution saves `upload.json`, `update-request.json`, `after.json`, and `receipt.json`. Account/runtime snapshots stay under `state/`; do not commit them or recreate this code in a per-shirt scratch script.

## Placement and supported scope

- One PNG up to 5 MiB, using its original pixels and transparency. No automatic background removal, flattening, or upscaling.
- By default, artwork fits within **8 × 12 inches**, preserving aspect ratio, horizontally centered with a 5% top inset on the tested Gildan 5000 / provider 99 print area (3951 × 4919 pixels at 300 DPI). The explicit `--scale-percent` option uses the centered larger-placement mode described above.
- Effective DPI is reported for review. For example, 1024 × 1536 at 8 × 12 inches is **128 DPI**. A successful API save does not certify physical print quality.
- Exactly one existing image per front print area; other locations must have no artwork. The API request omits empty placeholders because Printify rejected them during the live test.
- Native draft copies legitimately omit `external`; shipping linkage on the published source is not proof of linkage on the draft. The helper compares the available product settings and preserves reported draft shipping metadata. Verify the actual shipping profile when preparing publication.
- New garment/provider configurations, multiple artwork layers, personalization, and Etsy-only attributes require an explicit extension of this workflow. This command does not update Etsy or publish a listing.

## Recovery and token discipline

Reuse the same run directory after a failure. An approved revision is tied to the exact file hash, target ID, copy, placement, and baseline. Changing those inputs requires a new review revision. Run directories and cached upload receipts are trusted local operating state, created with restrictive permissions, not signed attestations against a local owner editing files. Do not edit receipts to make a check pass or substitute artwork IDs. Invoke the CLI: it loads the decision from ApprovalStore; the underlying Python functions accept injected dependencies for testing and are not an authorization boundary against arbitrary local Python code.

If an upload result is uncertain, the saved attempt marker stops automatic re-upload; reconcile Printify's upload library before proceeding. If an update succeeded but its response was lost, a retry reads the draft and recognizes the applied result instead of sending the update again. Never recreate the product to recover a failed update.

Use compact API summaries for routine checks. Do not re-research Printify, inventory all Etsy listings, generate a fresh script, or walk through every browser setting per design. Browser work should normally be limited to **native Duplicate and one visual review**. A failed preservation check warrants targeted investigation, not silent manual rebuilding.

## Implementation and verification

- CLI: `scripts/pod_draft.py`
- API orchestration: `packages/pod/runner.py`
- Clone/placement/preservation checks: `packages/pod/template.py`
- Shared approval policy: `packages/policies/pod.py`
- Tests: `tests/python/unit/test_pod_runner.py`, `tests/python/unit/test_pod_template.py`

```sh
.venv/bin/pytest tests/python/unit/test_pod_runner.py tests/python/unit/test_pod_template.py -q
```

The live experiment validates the native Duplicate/API behavior; offline tests validate the reusable command's guards and recovery. No further live test product is needed just to rerun those tests.
