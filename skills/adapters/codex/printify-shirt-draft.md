# Printify Shirt Draft — Codex adapter

Source of truth: [canonical skill](../../canonical/printify-shirt-draft/skill.md).
Read its [contract](../../canonical/printify-shirt-draft/contract.yaml) and
`docs/founder/printify-shirt-workflow.md` before operating any account state.
This adapter owns runtime translation only; it does not alter the canonical
approval boundary.

## Route work by capability

- Use the signed-in **browser** for Printify native Duplicate, front-art upload
  and placement, mockup selection/order, and Save as draft. Treat any ambiguous
  UI outcome as a stop-and-reconcile event.
- Use `scripts/pod_draft.py inspect` for fresh read-only template or draft
  evidence. Use `prepare-copy` only after browser placement. Use `apply-copy`
  only after a real shared approval matches the exact review revision.
- Do not call Printify's product-creation API as a substitute for native
  duplicate. Do not resubmit print areas: preserve the inner-neck layer that
  the public API cannot safely round-trip.

## Operating constraints

1. Resolve the selected local artwork path and verify it is a validated master;
   use listing copy whose provenance disclosure describes that artwork.
2. Duplicate the designated Printify template exactly once in the browser.
   Confirm a new unlinked product ID before any retry.
3. Replace front artwork in the browser and preserve the inner-neck layer. If
   replacing it requires deleting the old front layer, follow the active
   browser policy and obtain any required **action-time confirmation** before
   clicking Delete. Treat removal of the copied old front layer as standing
   owner intent for every native duplicate, not a recurring design-choice
   approval. Save an unpublished draft only after the replacement is complete,
   then run `prepare-copy` to obtain its review revision.
4. Register the pending request through the platform's approval store; never
   create an approval by editing local JSON. Pass the returned approval ID to
   `apply-copy`.
5. Verify the saved draft after browser mockup selection and refresh the local
   catalog. Return the review/receipt paths and clearly state it is unpublished.

## Publication gate

Never publish or synchronize to Etsy; do not click Publish as part of this skill.
Preparing or approving a Printify draft does not authorize a listing change.
Require separate explicit publication approval naming the exact product/revision;
without it, prepare a review packet and stop.
