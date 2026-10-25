---
status: ready
priority: p0
issue_id: "090"
tags: [home-from-working, etsy, trust, shipping, disclosure]
dependencies: ["088"]
---

# Approve and apply Etsy trust disclosures

## Problem Statement

Buyer-facing production-partner, AI, dispatch-origin, processing, returns, and sizing fields cannot be assumed from historical Printify receipts. Applying prepared public copy requires action-time founder approval after live evidence is reconciled. The requested shipping baseline is already live and requires no change.

## Findings

- Live Etsy reconciliation is complete. Of 70 local records, 56 have stable live Etsy matches and 14 remain unmatched/catalog-only.
- The first corrected trust audit still had a phrase-matching defect: it did not recognize the live wording `AI image-generation tool`. After a live preflight exposed the defect, the detector was fixed test-first. The current audit reports AI disclosure pass for all 56 stable live matches, unknown for 14 catalog-only records, and zero AI-disclosure failures. All 70 remain `blocked_unknown` because Etsy's API omits other per-listing trust fields.
- Etsy requires applicable listings to disclose both production partners and seller-prompted AI use.
- The approved launch baseline is $4.95 buyer-paid U.S. shipping with no free-shipping guarantee.
- Live Shop Manager verification found 74 active listings on the fixed $4.95/$2.40 U.S. Printify profile, one active listing on the fixed $8.79/$2.09 U.S. Printful profile, zero active listings on the explicitly free profile, and the shop-wide free-shipping guarantee off.
- A separate Printify V2 catalog read verifies $4.95 first-item and $2.40 additional-item standard U.S. fulfillment expense for all 49 enabled shirt-template variants; buyer charges and fulfillment costs are not inferred from each other.
- Offsite Ads are already opted out and verified by dated screenshot.
- Signed-in read-only inspection confirms the production-partner profile is `Printify`, publicly shown as `A print shop`, in Wilmington, Delaware, and used in 83 listings.
- The active snacks-raccoon pilot treatment listing has Printify attached, a 3–5 business-day made-to-order processing window, 30-day returns/exchanges, the approved buyer-paid Printify shipping profile, and an AI-assistance disclosure already present. This verifies the pilot listing, not every active listing.
- The founder approved revision `a868a517…`, but execution stopped after one description when the next live listing showed an existing valid AI disclosure. Offline inspection confirmed that all 15 targets already had equivalent AI-disclosure copy. The founder then approved exact rollback revision `54395858…`; the redundant second paragraph was removed from listing `4567764430`, the original valid disclosure was preserved, and the remaining 14 were not edited.
- Draft copy and a buyer-reassurance checklist exist in `state/home-from-working/operations/trust-copy-draft.md`.

## Proposed Solutions

### Option 1: Review once, apply only verified fields

**Approach:** After OAuth reconciliation, present a diff for the shop About section, production-partner profile, and applicable AI disclosure. Founder approves the exact public revision before Etsy is changed.

**Pros:** Accurate, consistent, and efficient.  
**Cons:** Needs one focused founder review.  
**Effort:** 20–40 minutes review plus execution  
**Risk:** Low to medium because public copy is affected.

### Option 2: Leave public fields unchanged

**Approach:** Do not edit until each listing is reviewed manually.

**Pros:** No immediate account mutation.  
**Cons:** Trust/policy gaps may persist and Days 1–7 cannot exit.  
**Effort:** None now  
**Risk:** Medium.

## Recommended Action

Do not apply the superseded 15-listing manifest. The approved exact rollback is complete. Retain the existing valid AI-disclosure wording on all 15 listings and continue treating batch-wide production/processing fields as unknown until verified.

## Technical Details

**Affected areas:** Etsy Shop Manager About, production partners, and applicable listing descriptions. Shipping is evidence-only unless a later discrepancy is found. New listings/publication remain out of scope.

## Resources

- [Etsy Creativity Standards](https://www.etsy.com/legal/creativity/)
- [Etsy production partners](https://help.etsy.com/hc/en-us/articles/360000336547-Working-with-Production-Partners-on-Etsy)
- `state/home-from-working/operations/trust-copy-draft.md`

## Acceptance Criteria

- [x] Live listing, origin, returns, sizing, production-partner collection, and shipping-profile evidence is captured. Etsy's read endpoints still omit per-listing partner attachment and processing-range fields, so those checks remain explicitly unknown rather than failed.
- [x] Every proposed change is shown as an exact public-copy change manifest.
- [x] Founder approved exact revision `a868a517…` at action time; execution was stopped safely after one target when its underlying audit assumption proved false.
- [ ] Every applicable listing discloses the actual production partner and AI assistance.
- [x] U.S. standard buyer shipping is $4.95/$2.40 for the 74-listing Printify profile and $8.79/$2.09 for the one-listing Printful profile; free-shipping guarantee is off.
- [x] Printify standard U.S. fulfillment expense is independently verified at $4.95/$2.40 for every enabled shirt-template variant.
- [x] Post-change readback matches the approved rollback revision for listing `4567764430`; the original valid disclosure and all protected fields were preserved.

## Work Log

### 2026-09-06 - Draft prepared

**By:** Codex

**Actions:** Chose the shipping baseline, verified Offsite Ads, researched current Etsy disclosure rules, and drafted non-public trust copy.

### 2026-09-06 - Shipping baseline verified

**By:** Codex

**Actions:** Read the signed-in Shipping Settings without saving changes. Verified the shop-wide guarantee is off, the explicit free profile has zero active listings, and the 74-listing Printify profile already charges $4.95 for the first U.S. item and $2.40 for an additional item. Saved dated JSON and screenshot evidence.

### 2026-09-06 - Remaining shipping evidence completed

**By:** Codex

**Actions:** Opened the one-listing Printful profile read-only, recorded its fixed $8.79/$2.09 U.S. charge, and canceled without saving. Separately joined the live Printify shirt template's 49 enabled variants to the named V2 standard-shipping endpoint, which verified a $4.95/$2.40 fulfillment cost for every enabled variant.

### 2026-09-06 - Live trust evidence reconciled

**By:** Codex

**Actions:** Captured all 75 active Etsy listings with per-listing detail GETs and corrected the audit so unavailable production-partner/processing fields remain unknown. Verified that size information passes for all 56 stable live matches and identified 15 descriptions missing the required AI-assistance wording.

**Learnings:** Public-copy approval can now target the 15 confirmed AI-disclosure gaps. Production-partner attachment and processing time still require a bounded signed-in Etsy UI readback before any change is proposed.

### 2026-09-06 - Pilot trust settings verified in Etsy UI

**By:** Codex

**Actions:** Inspected the production-partner manager and active snacks-raccoon multi-product listing without saving. Confirmed Printify/A print shop, made-to-order production, 3–5 day processing, 30-day returns/exchanges, buyer-paid shipping, and existing AI-assistance disclosure on the pilot listing.

**Learnings:** The pilot treatment listing is correctly configured for the checked trust fields. The read-only API still cannot prove these fields across every listing, so batch-wide unknowns remain unknown rather than being promoted to pass or failure.

### 2026-09-06 - Exact 15-listing disclosure preview prepared

**By:** Codex

**Actions:** Prepared a no-write manifest naming all 15 live listing IDs, the one exact paragraph to append, action-time preconditions, prohibited side effects, and a revision hash. No Etsy field was changed.

**Learnings:** Approval can now be narrow and revision-bound. It covers only the exact description additions in SHA-256 revision `a868a517bca8f70c04bc2bbaeac9ddfcd89b415b23b97808d4a61e62409d28cf`; it does not approve publication or any other listing mutation.

### 2026-09-07 - Approved batch stopped after live safety discovery

**By:** Codex

**Actions:** Verified the approved manifest hash, title, and normalized source description before editing listing `4567764430`. Added the exact approved paragraph and read it back successfully. Stopped before the second write because the second description already contained clear AI-assistance wording. Inspected all 15 source descriptions and confirmed the same valid disclosure family in every target. Recaptured the 75-listing Etsy snapshot and verified the one applied listing changed only its description plus Etsy's `updated_timestamp`; the remaining 14 descriptions were not edited.

**Learnings:** The detector's phrase list—not the listings—caused the 15 failures. The audit now recognizes `AI image-generation tool`, and all 56 stable live matches pass AI disclosure. A one-listing rollback revision `54395858488933c6f80f5b441cda2f52a7cc347be39ae8f8b92fd281084968ce` is prepared to remove the redundant appended paragraph, but requires founder approval because it is a new public edit.

### 2026-09-07 - Exact rollback applied and verified

**By:** Codex

**Actions:** Applied founder-approved revision `54395858488933c6f80f5b441cda2f52a7cc347be39ae8f8b92fd281084968ce` to listing `4567764430` in the signed-in Etsy editor. Removed the exact trailing paragraph once, recaptured the live Etsy snapshot, and compared the retained before/after records.

**Learnings:** Only `description` and Etsy's `updated_timestamp` changed. The original `AI image-generation tool` disclosure remained, the redundant paragraph is absent, and every protected listing field is equal. Receipt: `state/home-from-working/operations/trust-copy-rollback-execution-receipt-20260907.json`.

### 2026-09-07 - Shop-level trust floor audited and exact change packet prepared

**By:** Codex

**Actions:** Captured a fresh read-only Etsy API snapshot, then inspected the signed-in Shop Manager without publishing. Verified 76 active listings; an existing icon and About story; a Printify production-partner profile used in 84 listings; the 30-day return/exchange policy and 3-5 day made-to-order processing profile on all 76 active listings; buyer-paid shipping; and the free-shipping guarantee off. Confirmed that the banner, announcement, cancellation policy, privacy policy, FAQ, and seller photo are missing. Prepared a revision-bound public-copy packet plus matching 500 x 500 icon and 1600 x 400 banner assets at `state/home-from-working/operations/trust-floor-20260907/`.

**Learnings:** The public trust floor is farther along than the original API-only audit showed. The returns and processing fields do not need a bulk listing rewrite. Remaining Etsy Save/Publish actions require action-time founder confirmation; the one-hour cancellation policy also requires verifying a matching Printify pre-production approval window.

### 2026-09-07 - Exact trust-floor revision approved

**By:** Founder / Codex

**Actions:** Recorded the founder's action-time approval of exact SHA-256 revision `639200185e1bad056ec05848224931ef4e5c69b6ebf46c2b77b0f46c501dd481` and reverified the manifest checksum. No broader listing, shipping, pricing, inventory, or publication permission was inferred. Public execution remains subject to the packet's Printify cancellation-window precondition.

**Learnings:** The signed-in Brave session is concurrently being used by the founder. Etsy execution must wait for a short idle window so automation does not redirect, overwrite, or submit the founder's active ChatGPT and Printify work.

### 2026-09-08 - Shop-level trust floor executed and 4K banner verified

**By:** Founder / Codex

**Actions:** Executed founder-approved revision `639200185e1bad056ec05848224931ef4e5c69b6ebf46c2b77b0f46c501dd481` after verifying Printify's 24-hour order-approval window. Published the approved icon, tagline, announcement, About copy, public production-partner wording, one-hour cancellation policy, privacy policy, and eight FAQs. Etsy required a real face photo before the shop-member card could be saved, so that item remains founder-only. The initial 1600 x 400 banner was subsequently replaced under separately approved revision `adfd11f5af5bb32ebe48d0470725fb3c72c5666404d9ff3240a87cfc5dd0f19d` with a true 4000 x 1000 vector-rendered asset. The public storefront was reloaded and the replacement persisted.

**Learnings:** A vector-rendered source provides visibly cleaner typography on a widescreen display than enlarging the original raster. Etsy still applies its own image delivery and compression, so the retained 4000 x 1000 source is the appropriate master for future banner revisions. No listing, price, shipping, inventory, or publication field was changed by this execution.

## Notes

AI lifestyle scenes must be identified as illustrative mockups and must not materially alter the offered product.
