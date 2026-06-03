---
status: pending
priority: p2
issue_id: "077"
tags: [code-review, reliability, sequencing, better-business-web, agency]
dependencies: ["067", "070"]
---

# Problem Statement

§12 step 1 bundles "halve `catalog.yaml` + build the mirror generator +
regenerate the mirror + drift test" as one step — but the generator doesn't
exist yet (§2). If the YAML edit lands before the generator + drift test, the
committed mirror desyncs with nothing catching it (exactly the failure §2 is
trying to prevent), and signed OFFERs re-quote (070) before any policy guards
them. Step 4 also requires a test-deploy that the unrelaxed gate (066) can block.

## Findings

- §12 step 1 bundles the YAML edit with not-yet-existing tooling — [LANDING_PAGE_PLAN.md:210](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:210).
- The generator `render_service_catalog` does not exist (grep confirms; see 076).
- Step 4 test-deploy precedes step 5 gate relaxation — [LANDING_PAGE_PLAN.md:216](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:216) — but the gate (066) can block the deploy step 4 needs.

## Proposed Solutions

### Option 1: Re-order step 1 and provide a non-gated test-deploy path (recommended)
1a. Build generator + drift test against the *current* catalog (if generator is
kept per 076). 1b. Resolve the OFFER snapshot policy (070). 1c. *Then* halve and
regenerate. Ensure a draft/branch (non-gated) deploy exists so the step-4 form
test can run before the production gate.

Pros:
- No window where the mirror can silently desync or signed offers re-quote unguarded
- Form detection test isn't blocked by the launch gate

Cons:
- Slightly more sequencing detail

Effort: small
Risk: low

### Option 2: Keep order, accept transient desync
Halve first, fix mirror after.

Pros:
- Fewer steps

Cons:
- Reintroduces the exact drift §2 wants to prevent

Effort: none
Risk: medium

## Recommended Action

Adopt Option 1: split step 1 (tooling/policy before mutation) and guarantee a
non-gated test-deploy path.

## Acceptance Criteria

- [ ] Mirror tooling/policy lands before the catalog is mutated (or §2 mirror is simplified per 076).
- [ ] A non-gated draft deploy supports the form-detection test before production.

## Work Log

### 2026-06-02 - Initial review capture
Surfaced by spec-flow-analyzer during `/review`.
