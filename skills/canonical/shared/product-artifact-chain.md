---
id: product-artifact-chain
name: Product Artifact Chain
purpose: Validate and extend the founder-to-spec artifact chain for a managed product.
owner_agent: supervisor
target_runtimes: [claude, codex]
stage: active
inputs:
  - product_id from infra/products.json
  - the specific artifact to create or validate (e.g. product-brief, mvp-spec, backlog)
outputs:
  - a validated or newly created artifact file under docs/products/<product-id>/
  - a gap report listing missing or incomplete artifacts in the chain
allowed_edit_boundaries:
  - docs/products/
forbidden_areas:
  - apps/
  - packages/
  - infra/
  - state/
  - products/
dependencies: []
validation_steps:
  - product exists in infra/products.json
  - docs_root directory exists for the product
  - each artifact in the chain is present and non-empty
  - new artifacts reference upstream artifacts correctly
handoff_contract:
  what_is_handed_off: completed artifact file path and gap report
  handed_to: supervisor for prioritization of remaining gaps
claude_adaptation_notes: |
  Claude can run this skill interactively by reading the product registry,
  inspecting the docs folder, and prompting the user for missing content.
codex_adaptation_notes: |
  Codex receives a task packet specifying which artifact to draft, with the
  upstream artifacts included as context files.
---

## Instructions

### 1. Load the product registry

Read `infra/products.json` and locate the entry matching the given `product_id`.
Extract `docs_root` to find the artifact directory.

### 2. Assess the artifact chain

The expected chain for any product is:

1. `founder-brief.md` — customer problem and founder intent
2. `product-brief.md` — product thesis, rules, and MVP boundaries
3. `mvp-spec.md` — features in/out, acceptance criteria, success definition
4. `backlog.md` — prioritized work items derived from the spec
5. Platform-specific artifacts (e.g. `ios-architecture.md`, `app-store-positioning.md`)
6. Domain-specific artifacts (e.g. `insight-rules.md`, `insight-acceptance-cases.md`)

For each artifact:

- Check existence
- Check that it is non-empty
- Check that it references its upstream artifact where relevant

### 3. Report gaps

Produce a gap report listing:

- missing artifacts
- empty artifacts
- artifacts that appear disconnected from the chain

### 4. Create or extend an artifact (if requested)

When asked to create a specific artifact:

- Read all upstream artifacts for context
- Draft the new artifact following the conventions visible in existing artifacts
- Place it at `<docs_root>/<artifact-name>.md`
- Do not invent product decisions — flag uncertainties for founder review

### 5. Validate

- Confirm the artifact file exists and is non-empty
- Confirm no files were modified outside `docs/products/`
