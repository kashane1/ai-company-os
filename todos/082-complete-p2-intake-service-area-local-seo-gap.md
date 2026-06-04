---
status: complete
priority: p2
issue_id: "082"
tags: [code-review, planning, agency, local-seo, intake, quality]
dependencies: []
---

# Intake Service Area Local SEO Gap

## Problem Statement

The plan says each client's service area is captured during intake and then used by `LOCAL_SEO.md`/`generate_matrix`. Current intake captures a single `city` and optional `region`, while `LOCAL_SEO.md` remains a generic stub after `apply_client_intake`.

If Phase 6 ships directly against the current intake surface, local SEO generation will either use empty TBD values, infer cities without a durable approval trail, or require manual edits that the plan does not sequence.

## Findings

- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:123` says `CLIENT_BRIEF.md` stores primary city, region, and how far the client travels.
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:124` says `LOCAL_SEO.md` stores `primary_city`, `service_area_cities[]`, and `services[]`.
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:127` says local SEO uses cities listed by the client/agent and the operator approves inferred suburbs.
- `packages/agency/intake.py` only has `city`, `region`, and `services`; no `service_area_cities`, travel radius, or operator-approved inferred matrix.
- `packages/agency/client_lifecycle.py` rewrites `CLIENT_BRIEF.md`, `COPY.md`, and `SITE_MAP.md` during intake, but does not materialize the `LOCAL_SEO.md` matrix.
- `packages/agency/templates.py` seeds `LOCAL_SEO.md` with TBD placeholders.

## Proposed Solutions

### Option 1: Extend ClientIntake With Service Area Fields

**Approach:** Add structured service-area fields to `ClientIntake`, render them into `CLIENT_BRIEF.md` and `LOCAL_SEO.md`, and test the intake-to-local-SEO artifact flow.

**Pros:**
- Makes the plan's intake claim true.
- Gives Phase 6 deterministic inputs.
- Keeps operator approvals attached to durable artifacts.

**Cons:**
- Touches schema, CLI args, renderers, and tests.
- Requires deciding minimum required fields.

**Effort:** 4-8 hours

**Risk:** Low

---

### Option 2: Add A Separate Local SEO Matrix Approval Step Before Generation

**Approach:** Keep `ClientIntake` small, but require `scripts/agency/run_local_seo.py` to fail unless `LOCAL_SEO.md` contains a non-empty approved matrix.

**Pros:**
- Smaller intake change.
- Makes the matrix approval explicit at the point of generation.

**Cons:**
- Adds an extra manual step.
- Leaves "captured at intake" inaccurate unless the plan is revised.

**Effort:** 3-6 hours

**Risk:** Low

---

### Option 3: Infer From Primary City With Mandatory Approval Record

**Approach:** Let agents propose suburbs from primary city, but write a pending approval record before generation and require approval before pages are emitted.

**Pros:**
- Keeps operator work low.
- Matches the plan's "agent may propose suburbs" path.

**Cons:**
- Requires approval integration from todo 080.
- City inference can still be low quality without client-provided service area.

**Effort:** 1-2 days

**Risk:** Medium

## Recommended Action

Resolved in the plan by adding a required service-area intake slice before Phase 6:
structured service-area fields, `LOCAL_SEO.md` rendering, canonical matrix approval,
and fail-closed local SEO generation.

## Technical Details

**Affected files:**
- `packages/agency/intake.py`
- `scripts/agency/client_intake.py`
- `packages/agency/client_lifecycle.py`
- `packages/agency/templates.py`
- Future `packages/agency/local_seo.py` parser and CLI
- `tests/python/unit/test_client_lifecycle.py`
- `tests/python/unit/test_client_intake_scaffold.py`

**Related components:**
- Client workspace docs.
- Local SEO page generator.
- RetainerOps service execution.

**Database changes:**
- No database migration expected.

## Resources

- Plan local SEO section: `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`
- Intake schema: `packages/agency/intake.py`
- Workspace templates: `packages/agency/templates.py`
- Local SEO generator: `packages/agency/local_seo.py`

## Acceptance Criteria

- [ ] Client service area is captured in a structured place before local SEO generation.
- [ ] `LOCAL_SEO.md` is populated from intake or explicitly validated as manually approved.
- [ ] Local SEO CLI refuses to generate pages from TBD/empty service-area data.
- [ ] Tests cover generated `LOCAL_SEO.md` content and fail-closed behavior for empty matrices.
- [ ] The plan sequencing includes the service-area capture/approval step before Phase 6 generation.

## Work Log

### 2026-06-03 - Review Finding

**By:** Codex

**Actions:**
- Compared the plan's local SEO data-flow claims against current intake, lifecycle, and template code.
- Created this todo as P2 because it is likely to break Phase 6 implementation quality but does not by itself move money or send messages.

**Learnings:**
- Local SEO generation should not depend on implicit city inference without a durable client/operator approval artifact.

### 2026-06-03 - Plan Resolution

**By:** Codex

**Actions:**
- Added `service_area` YAML to the plan.
- Specified new `ClientIntake` fields and `apply_client_intake()` rendering into `LOCAL_SEO.md`.
- Required the local SEO CLI to refuse TBD/empty/unapproved matrices.

**Learnings:**
- The cleanest first slice is structured intake plus fail-closed generation, not hidden suburb inference.

## Notes

- This can be solved as a plan update plus implementation task; the review does not require changing the plan file immediately.
