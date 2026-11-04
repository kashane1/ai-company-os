---
status: ready
priority: p1
issue_id: "091"
tags: [home-from-working, artwork, pilot, image-generation]
dependencies: ["088"]
---

# Regenerate only the pilot production masters that fail preflight

## Problem Statement

All 70 recorded artwork files are readable but fail the new production-master gate, typically because they are 1024×1536 and produce only about 85 effective DPI at a 12-inch print width. Blindly regenerating all 70 would spend time and image-generation allowance before demand evidence selects the right cohort.

## Findings

- `asset-audit.json` records 70 failures with per-file dimensions, hashes, DPI, transparency, and padding checks.
- The founder selected Option 1: regenerate only an evidence-qualified pilot cohort rather than all 70 assets.
- Marketplace Insights now ranks 14 of 29 deduplicated concepts with complete numeric metrics, while Etsy eligibility and other hard gates remain pending live read-only reconciliation.
- The first marketplace-prioritized brief is `I Was Told There Would Be Snacks`, backed by the strongest demand among the evidence-qualified concept pool and prepared as four distinct direction cards. This was a prioritization decision, not production or publication clearance.
- The founder prefers AI hero scenes over ordering samples during this phase.
- The founder selected the generated `style-3` `Empty Bowl, Full Betrayal` concept on 2026-09-07. A built-in refinement was rejected for a baked checkerboard and missing alpha; the selected original was instead corrected deterministically into a 3600 × 3600 transparent master at 300 effective DPI.

## Proposed Solutions

### Option 1: Regenerate the selected pilot cohort first

**Approach:** After evidence confirms the cohort, create true production masters for only the treatment/control assets that fail, then preflight them deterministically. Generate optional AI lifestyle scenes separately and label them illustrative.

**Pros:** Limits image usage and protects experimental comparability.  
**Cons:** Defers most of the catalog.  
**Effort:** Depends on accepted generations  
**Risk:** Low.

### Option 2: Upscale all 70 immediately

**Approach:** Batch upscale without concept prioritization.

**Pros:** Fast apparent coverage.  
**Cons:** May preserve weak typography/artifacts and spends usage on low-priority designs.  
**Effort:** High  
**Risk:** Medium to high quality risk.

## Recommended Action

Use Option 1. Founder approves each concept/direction, while deterministic asset checks run automatically. Do not treat a synthetic lifestyle scene as the print master or a physical sample.

The next executable step is to prepare four materially different style cards for the strongest eligible concept. Built-in image generation remains blocked until the founder explicitly clears one or more `style-N` IDs.

## Technical Details

**Affected files:**

- `state/home-from-working/operations/asset-audit.json`
- `state/home-from-working/operations/pilot.json`
- `state/home-from-working/artwork/`
- `state/home-from-working/artwork/snacks-raccoon/20260906-marketplace-priority/direction-cards.json`
- `state/home-from-working/artwork/snacks-raccoon/20260906-marketplace-priority/written-examples.md`

## Resources

- `state/home-from-working/operations/project-pack/PROJECT_INSTRUCTIONS.md`
- `state/home-from-working/operations/project-pack/CHAT_TEMPLATES.md`

## Acceptance Criteria

- [x] Live/evidence-qualified pilot cohort is fixed before regeneration.
- [x] Founder selected the evidence-qualified-pilot-first approach.
- [x] Founder approved the `style-3` custom execution `Empty Bowl, Full Betrayal` for the first snacks-raccoon concept.
- [ ] All selected pilot production masters pass PNG, transparency, dimensions, effective-DPI, padding, legibility, and hash checks.
- [x] The first selected snacks-raccoon production master passes PNG, transparency, dimensions, effective-DPI, padding, legibility, contrast, and hash checks; remaining cohort masters are not yet approved or generated.
- [ ] AI lifestyle scenes have an illustrative-mockup manifest and accurate product appearance.
- [ ] Web/API image usage and human rework are recorded per accepted asset.

## Work Log

### 2026-09-06 - Preflight completed

**By:** Codex

**Actions:** Audited 70 recorded source images and retained failures rather than silently accepting low-resolution assets.

### 2026-09-06 - Option 1 approved

**By:** Codex

**Actions:** Recorded the founder's decision to regenerate only the evidence-qualified cohort. Kept generation behind live Etsy eligibility and explicit style-card clearance.

**Learnings:** Marketplace metrics can prioritize which cards to prepare, but they do not replace IP, policy, production, margin, or live-listing gates.

### 2026-09-06 - First direction cards prepared

**By:** Codex

**Actions:** Prepared four contract-shaped, materially distinct directions for `I Was Told There Would Be Snacks` and recommended `style-1` (Empty Diner, Retro Mascot). Recorded zero generation calls and zero listing mutations.

**Learnings:** The next step requires the founder to clear one or more exact `style-N` IDs. The earlier approval of Option 1 selected the pilot-first workflow but did not approve a creative direction.

### 2026-09-06 - Sixteen written examples added

**By:** Codex

**Actions:** Expanded each of the four parent directions into four concise written executions so the founder can choose both the visual family and a preferred composition before spending image-generation calls.

**Learnings:** The examples are selection aids, not new top-level direction IDs. Clearance still requires an exact parent `style-N`; the founder may additionally name an example letter.

### 2026-09-06 - Empty Bowl initial concept generated

**By:** Codex

**Actions:** Recorded explicit founder clearance, made one built-in image-generation call, saved the transparent initial PNG, and inspected light, dark, and neutral composites. Exact wording, transparency, visible content, padding, and visual contrast pass.

**Learnings:** The 1254 × 1254 concept is only 104.5 effective DPI at a 12-inch print width, so it remains a concept preview and fails the production-master gate until the founder keeps it and authorizes a high-resolution correction/refinement path.

### 2026-09-07 - Founder selection and production master completed

**By:** Codex

**Actions:** Recorded the founder's decision to keep `style-3`. Retained a failed built-in refinement for audit history, then preserved the selected transparent artwork and uniformly enlarged it with added transparent safe-area padding. Validated the 3600 × 3600 master and three garment-background previews.

**Learnings:** The built-in edit returned an RGB checkerboard and could not be used. The deterministic master retains the selected pixels and wording, has real alpha, and reaches 300 effective DPI at a 12-inch print width without redesigning the concept.

### 2026-09-07 - First master entered the reusable shirt-draft workflow

**By:** Codex

**Actions:** Added the reusable `printify-shirt-draft` canonical skill and Codex adapter. After founder approval, read the current Funny Earth template, created exactly one native duplicate (`6a9f0ae10ea1dd638e082657`), verified it is unlinked and unpublished with 49 variants, unchanged prices, and 20 mockups, then uploaded and centered the approved raccoon master. The in-progress editor is paused before deleting the old Earth front layer because that destructive browser click requires action-time confirmation.

**Learnings:** The 3600 × 3600 square master is width-limited by the 3951 × 4919 print area. Printify's 109.74% fitted scale keeps the complete master visible; forcing the nominal 305% placement would crop it. The copy input contains one raccoon intro and relies on the template's existing single valid AI disclosure, avoiding the redundant paragraph found in the earlier trust-copy run.

### 2026-09-07 - Front replacement saved and copy revision prepared

**By:** Codex

**Actions:** After the founder's action-time confirmation, deleted only the copied Earth front layer, verified the raccoon is the sole front image, preserved the inner-neck layer, and saved the unlinked unpublished draft. Recorded old-front removal as standing owner intent for all future native duplicates. Fixed the reusable review path to support Printify's 100 MiB browser upload limit while retaining the public API's 5 MiB limit. Prepared and registered pending copy revision `8844f471f0fcc1746a19416cf7bd72a49468b1799cdb7cc924525dc449360825` with zero account writes from the prepare step.

**Learnings:** The 8.18 MiB raccoon master is valid for Printify's browser uploader but correctly remains too large for the public upload endpoint used by the API-only route. Draft-copy preparation must validate the browser limit without weakening the API upload guard. The product-details screen showed the new duplicate's GPSR checkbox unchecked, so that setting must be reconciled during publication readiness rather than silently changed under copy approval.

### 2026-09-07 - Raccoon shirt draft verified for founder review

**By:** Codex

**Actions:** Recorded the founder's exact approval for revision `8844f471f0fcc1746a19416cf7bd72a49468b1799cdb7cc924525dc449360825` in the shared ApprovalStore and applied only title, description, and tags. Retained the high-contrast Black Front/Folded 2 lead pair, saved the draft, restored the source template's exact GPSR safety information, and confirmed Standard shipping with free shipping and Etsy off-site ads disabled. Completed browser and API readbacks and refreshed the 71-record product catalog.

**Learnings:** GPSR is returned by the Printify API as `safety_information` but is not preserved by native Duplicate. Restoring it creates one intentional final-state difference from the pre-copy draft baseline; diagnostics confirmed that `safety_information` and the volatile `updated_at` field were the only top-level changes, and the restored value exactly matches the source template.

### 2026-09-07 - Founder publication reconciled and monitoring started

**By:** Codex

**Actions:** Recorded the founder's manual publication, captured new sanitized GET-only Printify and Etsy snapshots, and verified Printify product `6a9f0ae10ea1dd638e082657` is linked to active Etsy listing `4570959040`. Readback confirmed the approved title and 13 tags, AI-assistance and production-partner language, 49 enabled offerings, the existing buyer-paid shipping profile, and unchanged $20.99 3XL pricing. Refreshed the canonical registry and moved this listing into Layer-3 7/14/30-day monitoring. Agent account writes during readback: zero.

**Learnings:** The raccoon listing is a shirt-only creative pilot with a cold-start age effect, so it must not be added to or used to interpret the frozen eight-listing product-format cohort. Its first checkpoints are September 14, September 21, and October 7 at 4:07 PM Pacific.

## Notes

The selected snacks-raccoon master is validated locally and is the sole front artwork on published Printify product `6a9f0ae10ea1dd638e082657`, linked to active Etsy listing `4570959040`. Exact copy revision `8844f471f0fcc1746a19416cf7bd72a49468b1799cdb7cc924525dc449360825` was approved before the draft review; the founder later published it manually. Future listing changes remain separately gated.
