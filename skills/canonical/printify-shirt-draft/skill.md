---
id: printify-shirt-draft
name: Printify Shirt Draft
purpose: Create one owner-selected HomeFromWorking shirt as an unpublished Printify draft while preserving the verified shirt template settings.
owner_agent: engineering
target_runtimes: [codex]
stage: active
kind: agentic
inputs:
  - founder-selected validated artwork path and its provenance disclosure
  - title, introduction, and up to 13 Etsy tags
  - optional approved template ID, lead color, and artwork-placement instructions
outputs:
  - verified unpublished Printify draft, review artifact, approval request, and catalog snapshot
allowed_edit_boundaries:
  - state/home-from-working/drafts/**
  - state/home-from-working/catalog/**
forbidden_areas:
  - Etsy publication or listing mutations
  - existing Printify template or published product mutations
dependencies:
  - docs/founder/printify-shirt-workflow.md
  - scripts/pod_draft.py
  - skills/canonical/printify-shirt-draft/contract.yaml
validation_steps:
  - confirm the native duplicate is unlinked and unpublished
  - verify retained variants, prices, selected mockups, inner-neck layer, and artwork placement
  - require a shared, revision-bound approval before applying copy
handoff_contract:
  what_is_handed_off: verified unpublished draft ID, review revision, approval receipt, and catalog snapshot
  handed_to: founder for separate publication approval
---

# Printify Shirt Draft

## Purpose

Create a repeatable HomeFromWorking **shirt-only** Printify draft from an
owner-selected validated artwork master. This skill is for new products, not
for converting an existing Etsy listing into a Multi-Product Listing. Read
`docs/founder/printify-shirt-workflow.md` for the current shop template,
prices, placement defaults, and detailed recovery procedure.

## When to invoke

Invoke when the founder wants a new Gildan 5000 shirt draft and has selected
the artwork. The caller must provide an exact local PNG path, a truthful
artwork-provenance disclosure, and listing-copy inputs. If copy is not final,
prepare it for review before any account write beyond the native duplicate and
browser artwork placement.

Do not invoke for artwork ideation or generation (use `pod-artwork-generator`)
or for an existing Etsy-linked shirt's multi-product conversion (use
`printify-multi-product-workflow.md`).

## Contract

Read [contract.yaml](contract.yaml) before acting. Return its shaped state at
each stopping point: template/draft IDs, artwork evidence, exact copy review
revision, approval status, retained-settings verification, lead mockup pair,
catalog path, warnings, and publication state. The normal successful terminal
state is `verified_unpublished`, never `published`.

## Procedure

1. **Preflight.** Read the current canonical template through
   `scripts/pod_draft.py inspect`; do not trust a historical snapshot when
   current settings matter. Confirm the founder-selected master has real alpha,
   safe dimensions, and a provenance disclosure that matches how it was made.
   Keep the template's current price ladder; pricing changes require separate
   approval.
2. **Native duplicate once.** In the signed-in Printify browser, locate the
   exact template and use **Duplicate** once. Record the resulting product ID
   and confirm it is a new unlinked, unpublished product. Do not use `POST products` as a shortcut and never run the draft command against the template.
3. **Browser-only artwork placement.** Open the duplicate in Printify, upload
   the exact PNG, replace only the front artwork, apply the approved placement
   (the current large-placement standard is 305%, centered at 50% / 50% unless
   browser safe-area feedback requires a documented adjustment), and retain the
   inner-neck `text_layer.svg`. Follow the active browser confirmation policy:
   when replacement requires deleting the old front layer, obtain any required
   **action-time confirmation** immediately before that destructive click. Save
   as draft only after the old layer is removed. Removing the copied old front
   artwork is standing owner intent for every native duplicate, not a recurring
   design-choice approval; runtime action-time confirmation still applies when
   required. Do not submit print areas via the public API.
4. **Prepare, then approve.** Write `copy.json` in the run directory and run
   `pod_draft.py prepare-copy`. It must produce an exact review revision and a
   proposed platform approval request without modifying Printify. Register and
   obtain a real shared approval with `approval_type=pod_draft_update`,
   `action=update_printify_draft`, and the exact review revision. A founder's
   generic request for a draft does not substitute for this approval boundary.
5. **Apply copy only.** Run `pod_draft.py apply-copy` with the real shared
   approval ID. It may update only title, description, and tags. It must stop
   if artwork, print areas, variants, prices, provider, selected mockups, or
   unpublished state drifted.
6. **Select and verify mockups.** In the browser, retain the template mockups,
   choose the approved matching-color Front first and Folded 2 second, set only
   one default image, and save as draft. Rotate the lead color across a batch.
   Read the saved product through the public API and visually inspect the lead
   image and mockup grid.
7. **Record the handoff.** Verify the new product is unlinked and unpublished;
   record the template/draft IDs, enabled variants and prices, selected mockups,
   default image and variant, artwork name/transform, retained inner-neck layer,
   copy, provenance disclosure, approval, and warnings. Refresh the shirt
   catalog with `scripts/pod_catalog.py`.

## Approval and publication boundary

Native duplication, browser placement, and saving an unpublished draft are
reversible draft work. Applying copy is a separate **revision-bound** approval
gate. Etsy synchronization or publication is never implied by either approval:
it requires a separate explicit founder approval naming the exact draft or
publication revision. Do not click Publish, enable Etsy sync, or create/edit an
Etsy listing during this skill.

## Boundaries and failure modes

- If duplication or save status is uncertain, stop and reconcile the product
  list before any retry; never duplicate again based on a guessed result.
- If the duplicate is linked, published, missing the inner-neck layer, or has
  changed prices/variants/mockups, stop with `TEMPLATE_RETENTION_FAILED`.
- If browser placement cannot be confirmed, stop with
  `BROWSER_ARTWORK_PLACEMENT_UNVERIFIED`; do not replace print areas using the
  API.
- If the browser requires action-time confirmation before deleting the old
  front layer, stop with `BROWSER_DELETION_CONFIRMATION_REQUIRED` and preserve
  the in-progress tab until the founder answers. Do not treat earlier generic
  draft authorization as that confirmation when the active browser policy says
  confirmation is always required.
- If the shared approval is absent, mismatched, or expired, stop with
  `REVISION_BOUND_APPROVAL_REQUIRED`.
- If a request asks to publish, prepare a publication review packet instead;
  do not publish. Return `PUBLICATION_REQUIRES_SEPARATE_APPROVAL`.

## References

- [Founder workflow](../../../docs/founder/printify-shirt-workflow.md)
- [Draft command](../../../scripts/pod_draft.py)
- [Multi-product workflow](../../../docs/founder/printify-multi-product-workflow.md)
