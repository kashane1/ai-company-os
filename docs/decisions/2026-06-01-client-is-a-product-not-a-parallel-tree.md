---
title: A client engagement is a managed product, not a parallel clients/ tree
date: 2026-06-01
status: accepted
related_brainstorm: docs/brainstorms/2026-06-01-agency-layer-brainstorm.md
related_plan: docs/plans/2026-06-01-feat-local-smb-agency-layer-plan.md
---

# ADR: A client engagement is a managed product, not a parallel `clients/` tree

## Context

The agency-layer angle turns `ai-company-os` into the operating system for a
local-SMB agency: each client gets a website plus recurring services. The initial
brainstorm notes proposed a parallel directory tree —
`docs/clients/<slug>/`, `products/client-sites/<slug>/`,
`state/artifacts/clients/<slug>/` — to hold client assets.

The repo already has a strong product convention: product artifacts in
`docs/products/<id>/`, source in `products/<id>/`, runtime in `state/`, all keyed
by a typed registry record in `infra/products.json` (`packages/config/products.py`
+ `packages/schemas/product.py`). A parallel tree would have forked the registry,
scaffold, deploy, audit, and report plumbing — two of everything to maintain.

## Decision

**A client engagement is modeled as a managed product of `type: client-site`,
reusing the existing product convention. The only genuinely new concept is
ownership.**

Specifically:

1. `ProductConfig` gains an additive, optional `type: ProductType`
   (`product` default | `client-site`) and an optional `client: ClientConfig`
   block (`ownership`, `bundle` FK to the service catalog, `services[]`,
   `from_prospect`, `billing_status`). All default so existing iOS/web records
   load unchanged.
2. Client sites live at the documented locations — `products/<slug>-site/`,
   `docs/products/<slug>-site/`, `state/...` — **not** a parallel `clients/` tree.
3. The ownership distinction (we *operate*, the client *owns* the asset) is the
   one new field: `ClientOwnership` = `client-owned` (default) | `agency-held`.
4. The commercial lifecycle uses `billing_status`; the build lifecycle reuses the
   existing `ProductPhase`. No new "client phase" enum was introduced — the two
   existing axes already cover it.
5. The product *type* discriminates behavior (e.g. client sites are not routed
   through the iOS-flavored `register_product` artifact builder); it does not
   justify a second storage location.

## What this changes relative to the brainstorm notes

The notes' parallel-tree proposal is rejected. Everything else in the notes (the
service stack, the prospect→client seam, the workspace doc set) is kept, but
rehomed onto the product model.

## Consequences

**Positive:**

- One registry, one scaffold/deploy/audit/report path. The web lane builds client
  sites with no forked tooling.
- Backward compatible: every additive field has a default; legacy records and
  their tests are untouched.
- The prospect→client promotion (`packages/agency/promotion.py`) just writes a
  `client-site` registry record — no new storage subsystem.

**Negative / accepted trade-offs:**

- `infra/products.json` now mixes owned products and client engagements. Consumers
  that assumed "every product is ours" must branch on `type` (audited:
  `apps/api/platform.py:register_product`,
  `packages/tools/product_artifacts/projection.py`).
- Owned-vs-client semantics now ride on a field rather than a directory boundary,
  so the distinction must be enforced in code/policy, not by path.

## Implementation reference

See the plan (`docs/plans/2026-06-01-feat-local-smb-agency-layer-plan.md`) and the
footgun writeup
(`docs/solutions/architecture/agency-layer-reuse-and-repo-mechanism-footguns.md`).
