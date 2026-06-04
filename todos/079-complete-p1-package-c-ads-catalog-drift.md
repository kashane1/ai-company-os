---
status: complete
priority: p1
issue_id: "079"
tags: [code-review, planning, agency, catalog, billing, ads]
dependencies: []
---

# Package C Ads Catalog Drift

## Problem Statement

The retainer ops plan locks "Package C includes ads", but the agency catalog source of truth does not include any ads service in `package_c`. Because promotion writes `client.services[]` from the catalog and the plan says packages drive automation, downstream RetainerOps and billing would treat ads as out of scope even though the plan and operator decision say they are included.

This can ship the wrong offer, wrong registry state, wrong retainer price, and no ads approval workflow for Package C clients.

## Findings

- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:53` says Package C includes ads.
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:91` says packages drive automation through `client.services[]`.
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:105` repeats the locked Package C ads decision.
- `packages/agency/catalog.yaml` defines `google_ads` and `meta_ads`, but `package_c.service_ids` ends at `monthly_reporting` and does not include either ads service.
- `packages/agency/promotion.py` persists `client.services` from `catalog.quote_bundle(bundle)`, so this is not a docs-only mismatch.
- Known Pattern: `docs/solutions/architecture/agency-layer-reuse-and-repo-mechanism-footguns.md` warns that agency plans must verify registry, catalog, and policy claims against source before implementation.

## Proposed Solutions

### Option 1: Add Explicit Ads Service To Package C

**Approach:** Update `packages/agency/catalog.yaml` so `package_c` includes the intended ads service, regenerate catalog mirrors, and update tests/pricing expectations.

**Pros:**
- Aligns the source of truth with the locked plan.
- Keeps `client.services[]` and RetainerOps behavior deterministic.
- Ensures OFFER rendering includes the ads retainer price.

**Cons:**
- Raises Package C monthly pricing unless existing package economics are revised.
- Requires a clear choice between `google_ads`, `meta_ads`, or a combined service.

**Effort:** 1-2 hours

**Risk:** Medium

---

### Option 2: Split Ads Into A Package C Add-On

**Approach:** Revise the plan to say Package C can include ads only when the signed offer adds `google_ads` or `meta_ads` explicitly, and keep the catalog unchanged.

**Pros:**
- Avoids silently increasing Package C price.
- Keeps ads opt-in per client and easier to refuse.

**Cons:**
- Contradicts the currently locked decision.
- Requires RetainerOps to handle package add-ons or service overrides.

**Effort:** 2-4 hours

**Risk:** Medium

---

### Option 3: Introduce A New Package C With Ads

**Approach:** Add a new bundle, such as `package_c_ads`, and leave existing `package_c` unchanged.

**Pros:**
- Preserves existing Package C semantics.
- Makes ads inclusion unambiguous at promotion time.

**Cons:**
- Adds bundle complexity and more landing/catalog rendering work.
- The plan must be rewritten to name the new bundle.

**Effort:** 3-5 hours

**Risk:** Medium

## Recommended Action

Resolved in the plan by choosing Google Search ads as the Package C default,
keeping Meta ads as quote/add-on, and adding required catalog alignment before
Phase 6/7/9 implementation.

## Technical Details

**Affected files:**
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`
- `packages/agency/catalog.yaml`
- `docs/agency/service-catalog.md`
- `products/better-business-web/site/src/data/packages.json`
- `tests/python/unit/test_agency_catalog.py`
- `tests/python/unit/test_agency_service_catalog_render.py`
- `tests/python/unit/test_agency_catalog_json.py`

**Related components:**
- Prospect promotion writes `client.services[]`.
- RetainerOps is planned to run services from `client.services[]`.
- Stripe billing will map bundles to Price IDs.

**Database changes:**
- No database migration expected.

## Resources

- Plan: `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`
- Catalog: `packages/agency/catalog.yaml`
- Known Pattern: `docs/solutions/architecture/agency-layer-reuse-and-repo-mechanism-footguns.md`

## Acceptance Criteria

- [ ] Package C ads decision is represented in the catalog or explicitly revised in the plan.
- [ ] Rendered service catalog and site package JSON are regenerated if catalog changes.
- [ ] Promotion of a Package C client produces `client.services[]` that matches the signed offer.
- [ ] Tests cover the intended Package C ads/add-on behavior.
- [ ] Billing/RetainerOps implementation can branch on a single unambiguous ads service signal.

## Work Log

### 2026-06-03 - Review Finding

**By:** Codex

**Actions:**
- Reviewed the retainer ops plan against the agency catalog and promotion code.
- Confirmed plan-level Package C ads lock does not appear in `package_c.service_ids`.
- Created this todo as a P1 because the mismatch can produce wrong external commercial terms and skipped ads gates.

**Learnings:**
- In this repo, catalog-driven services are load-bearing for both docs and automation.

### 2026-06-03 - Plan Resolution

**By:** Codex

**Actions:**
- Updated the retainer ops plan so Package C explicitly means `google_ads`.
- Added a required catalog-alignment slice to add `google_ads` to `package_c.service_ids`.
- Documented that `meta_ads` stays quote/add-on.

**Learnings:**
- The safest plan-level fix is to make the default ad channel singular and catalog-backed.

## Notes

- Do not treat this as a generated-doc cleanup. The source-of-truth decision must happen in `packages/agency/catalog.yaml` or in a plan revision.
