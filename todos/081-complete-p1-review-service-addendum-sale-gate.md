---
status: complete
priority: p1
issue_id: "081"
tags: [code-review, planning, compliance, agency, catalog, reviews]
dependencies: []
---

# Review Service Needs Addendum Sale Gate

## Problem Statement

The plan says review SMS is blocked until a signed addendum exists and also says to sell `reviews` only after the addendum is signed. The catalog currently includes the `reviews` service in Package B and Package C, and promotion renders `OFFER.md` from the catalog before any per-client addendum is signed.

This creates a compliance and expectation mismatch: the signed offer can include "Post-service SMS review requests" while the plan says the service must not be sold or enabled yet.

## Findings

- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:110` locks review SMS as blocked until `COMPLIANCE.md` plus signed addendum.
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:217` says `assert_review_sms_allowed` is still to implement.
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:219` says to sell `reviews` only after the addendum is signed.
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:345` defers adding `assert_review_sms_allowed` until the Twilio path starts.
- `packages/agency/catalog.yaml` includes `reviews` in `package_b` and `package_c`.
- `packages/agency/templates.py` renders the signed offer from catalog bundle services, so Package B/C offers already sell the review service.

## Proposed Solutions

### Option 1: Split Review Drafting From Review SMS Sending

**Approach:** Revise catalog/offer language so the included service is "review system setup/drafts" until addendum signature gates the live SMS send capability.

**Pros:**
- Preserves Package B/C value.
- Aligns offer text with current draft-only automation.
- Avoids selling live SMS before compliance is complete.

**Cons:**
- Requires catalog wording and rendered docs updates.
- Still needs a later policy gate before live sends.

**Effort:** 2-4 hours

**Risk:** Low

---

### Option 2: Make `reviews` An Add-On Activated After Addendum

**Approach:** Remove `reviews` from default Package B/C bundles and add it only through a signed-offer override once addendum is complete.

**Pros:**
- Strongest compliance posture.
- Matches "sell reviews only after addendum signed" literally.

**Cons:**
- Reduces package value unless replaced with another deliverable.
- Requires add-on handling in promotion/offers.

**Effort:** 4-8 hours

**Risk:** Medium

---

### Option 3: Keep Catalog But Add A Pre-Twilio Policy Gate Now

**Approach:** Implement `assert_review_sms_allowed` immediately for any code path that drafts, schedules, imports customer numbers, or sends SMS; update the plan to say the catalog sells a blocked service pending addendum.

**Pros:**
- Gets policy enforcement in place early.
- Clarifies blocked status before automation exists.

**Cons:**
- Does not fully fix the offer-language expectation mismatch.
- May be premature if no SMS code path exists yet.

**Effort:** 3-6 hours

**Risk:** Medium

## Recommended Action

Resolved in the plan by redefining packaged `reviews` as review readiness and
making live review SMS a separate activated capability blocked by signed addendum,
approved template, canonical approval, and `assert_review_sms_allowed`.

## Technical Details

**Affected files:**
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`
- `packages/agency/catalog.yaml`
- `packages/agency/templates.py`
- `docs/agency/compliance/COMPLIANCE-template.md`
- `docs/agency/compliance/review-sms-consent-addendum.md`
- Future `packages/policies/agency_gates.py` review-SMS gate

**Related components:**
- Promotion and offer rendering.
- Review SMS/follow-up automation.
- RetainerOps blocked approval listing.

**Database changes:**
- None expected.

## Resources

- Plan: `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`
- Catalog: `packages/agency/catalog.yaml`
- Offer renderer: `packages/agency/templates.py`

## Acceptance Criteria

- [ ] The plan consistently distinguishes review setup/drafting from live SMS sends.
- [ ] Catalog and `OFFER.md` language no longer promise live review SMS before addendum signature, or the service is removed from default packages.
- [ ] `assert_review_sms_allowed` timing is explicit and not deferred past the first code path that can touch customer phone numbers.
- [ ] Tests cover the selected catalog/offer behavior for Package B/C.
- [ ] A Package B/C client can be promoted without implying unauthorized live SMS.

## Work Log

### 2026-06-03 - Review Finding

**By:** Codex

**Actions:**
- Compared plan compliance language against the current catalog and offer renderer.
- Created a P1 because the current bundle wording can create a signed commercial promise that the compliance gate says is not yet allowed.

**Learnings:**
- Compliance constraints need to be reflected at the service catalog/offer layer, not only in future send-time code.

### 2026-06-03 - Plan Resolution

**By:** Codex

**Actions:**
- Updated locked decisions so Package B/C include review readiness, not live SMS.
- Added catalog copy alignment to rewrite `reviews` away from live "Post-service SMS review requests".
- Moved `assert_review_sms_allowed` to the first review-SMS-adjacent code path, before customer-number import or sends.

**Learnings:**
- A packaged compliance-sensitive service needs a safe inactive definition before live activation.

## Notes

- This is not legal advice; it is an implementation risk finding about mismatched product terms and policy enforcement.
