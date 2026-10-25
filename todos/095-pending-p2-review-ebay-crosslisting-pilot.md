---
status: pending
priority: p2
issue_id: "095"
tags: [home-from-working, printify, ebay, planning]
dependencies: []
---

# Review the eBay cross-listing process and approve one pilot

## Problem Statement

The founder wants all already-published Printify products considered for eBay, with varied main images. They explicitly requested a process overview before authorizing exactly one listing as a test. No live execution is authorized yet.

## Findings

- Printify documents its native Multi-Product Listing feature for Etsy; eBay color/size variations do not establish support for transferring mixed-product groups.
- The recommended queue uses separate listings per design/product type and accurate provider lead photos.
- Existing saved inventory is historical and incomplete for gallery/SKU planning; a fresh read-only reconciliation is required when the workflow starts.
- Copy preservation, gallery sync, shipping/returns, stock updates, SKU linkage, and duplicate recovery need verification in the pilot.

## Proposed Solutions

1. Operated native Printify workflow with a persisted manifest and one-listing gate (recommended): reuses fulfillment and limits initial engineering.
2. Custom eBay API publisher/order mapping: more control but much greater implementation and verification scope.
3. Manual mixed-product variation listings: unsupported native mapping and category uncertainty; not recommended.

## Recommended Action

Review `docs/plans/2026-09-11-printify-ebay-crosslisting-plan.md`. Obtain the founder's actual pilot authorization, prepare one exact product's review packet, and publish only if that concrete packet is approved. Do not run the catalog process, create account drafts, connect shops, or schedule work merely because this todo exists.

## Acceptance Criteria

- [x] Inspect repository context and official platform documentation.
- [x] Ask the optional image-rotation clarification and state the working assumption.
- [x] Compare alternatives and document the recommended workflow.
- [x] Save algorithm, identity/duplicate rules, gallery rules, approval scope, verification, and recovery steps.
- [ ] Founder reviews the overview and authorizes the one-listing pilot scope.
- [ ] Exact product/variant/gallery/price/shipping packet prepared and publication approved.
- [ ] Exactly one eBay listing published and verified; remaining catalog stays pending.
- [ ] Real-order verification tracked separately; no fabricated test transaction.

## Work Log

### 2026-09-11 — Process preparation

Read local workflow/snapshot interfaces and official Printify/eBay documentation; obtained independent repository investigation and policy research. Wrote and indexed the process specification. No source inventory refresh, credentials read, browser account operations, product copies, listings, or automation runs performed. Executable automation remains future work after the operated pilot establishes supported behavior.

## Resources

- `docs/plans/2026-09-11-printify-ebay-crosslisting-plan.md`
- `docs/founder/printify-shirt-workflow.md`
- `docs/founder/printify-multi-product-workflow.md`
