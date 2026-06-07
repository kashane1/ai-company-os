---
status: pending
priority: p1
issue_id: "036"
tags: [code-review, agent-native, agency, fulfillment, custom-bundle]
dependencies: []
---

# Problem Statement

The whole promotion/scaffold/offer chain is bundle-keyed and will raise for a custom cart (`bundle="custom"`). `scaffold_client_workspace(bundle_id=...)` and `render_offer(bundle_id=...)` both call `catalog.quote_bundle(bundle_id)`, which raises `CatalogError` for `"custom"` (no catalog entry). So a paid custom-bundle order cannot be promoted, scaffolded, or given an OFFER.md by the existing code — a fulfillment dead-end the plan doesn't list.

## Findings (agent-native-reviewer Q4, pattern-recognition P2-5)

1. `promote_prospect_to_client` → `quote_bundle(bundle)` → `client.services = [s.service_id …]` (`promotion.py:69,111`); then `scaffold_client_workspace(bundle_id=…)` re-derives via `quote_bundle` (`templates.py:54,190`). No `bundle_id` exists for a custom cart.
2. `render_offer` is bundle-only (`templates.py:190`) → custom client gets no OFFER artifact.
3. `BillingLedger` has a `bundle` string but **no `service_ids`** (`billing.py:68-83`) — for a custom order, "what did they buy" is recoverable only from the registry `client.services`, so the order poller writing that record correctly is load-bearing.
4. Plan adds `promote_order_to_client` + ledger `service_ids` (good) but omits generalizing `scaffold_client_workspace`/`render_offer` to a `service_ids` list, and omits `templates.py` from the Phase 3 edit set.

## Proposed Solutions

### Option 1 (recommended): service_ids-driven scaffold + render
Add a `service_ids`-driven path: `quote_services(service_ids)` powers both `scaffold_client_workspace` and `render_offer` when no `bundle_id` is present. `promote_order_to_client` writes `bundle:"custom"` + explicit `services`. Fulfillment reads `client.services` (not `bundle`) when `bundle=="custom"`.
- Decide: does a custom cart need an OFFER.md? If yes, render off `service_ids`; if no, skip explicitly.

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected (add to Phase 3 edit set): `packages/agency/templates.py` (`scaffold_client_workspace`, `render_offer`), `packages/agency/promotion.py` (`promote_order_to_client`, `from_order` provenance, slug-collision + reconcile-to-existing-prospect guards), `packages/agency/billing.py` (`service_ids` on `BillingLedger`).
- Registry key stays `client.services` (not `client.service_ids`) to match `promote_prospect_to_client`.

## Acceptance Criteria

- [ ] A custom-bundle order promotes + scaffolds without raising (no `quote_bundle("custom")`).
- [ ] Fulfillment resolves work from `client.services` when `bundle=="custom"`.
- [ ] OFFER.md decision made and implemented (render from `service_ids` or explicitly skipped).
- [ ] `promote_order_to_client` is idempotent on `product_id` and carries `from_order` provenance.

## Work Log

(to be filled in)

## Resources

- /workflows:review round 2 (2026-06-06): agent-native-reviewer Q4, pattern-recognition P2-5
