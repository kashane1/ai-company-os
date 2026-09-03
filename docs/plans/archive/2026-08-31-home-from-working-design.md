---
status: superseded
summary: Historical research-first HomeFromWorking design, replaced by the approved-design-to-listing direction on 2026-09-02.
superseded_by: docs/plans/2026-09-02-home-from-working-pod-design.md
last_reviewed: 2026-09-02
---

# HomeFromWorking Commerce Spine Design

> Superseded by the founder's September 2 direction. Follow the
> [approved-design-to-listing design](../2026-09-02-home-from-working-pod-design.md).
> The original proposal below is retained for history, not current execution.

**Original status:** Approved for implementation (historical; now superseded)
**Original approval claim:** Founder handoff marked “Ready for implementation” and “Begin implementation”
**Business:** `home-from-working`
**Scope:** First safe vertical slice; no live marketplace, fulfillment, spend, or publishing actions

## Goal

Add the smallest coherent HomeFromWorking foundation that can move one evidence-backed
print-on-demand opportunity through research, concept, artwork, product/listing draft, and
publication-readiness while enforcing four founder gates and preserving complete lineage.

## Chosen architecture

HomeFromWorking is a business operated by `ai-company-os`, not a managed software product and
not a new orchestrator. Reusable commerce contracts and workflow logic live in
`packages/commerce/`. HomeFromWorking-owned defaults, brand constraints, and trust policy live
under `businesses/home-from-working/`. Runtime records and generated assets remain under
`state/` through the existing runtime-path conventions.

The workflow composes, rather than expands, the generic discovery model. A commerce opportunity
references its originating `OpportunityRecord`; it adds POD-specific trend analysis, qualitative
commercial assessment, product candidates, creative directions, and zoom-in/zoom-out/sideways
research. The existing generic opportunity schema remains suitable for software and other
businesses.

This avoids two rejected approaches:

1. A single HomeFromWorking mega-worker would mix research, creative work, commerce execution,
   policy, and orchestration.
2. Adding all POD fields to `packages/schemas/opportunity.py` would make a reusable discovery
   record business-specific and couple unrelated discovery users to Etsy/Printify concepts.

## Components

### Typed commerce artifacts

`packages/schemas/commerce.py` defines frozen, serializable records for:

- classified market evidence (`fact`, `observation`, `inference`, `hypothesis`);
- a POD opportunity that references the discovery opportunity;
- creative concepts;
- generated design assets and production requirements;
- a provider-neutral product draft;
- a marketplace-neutral listing draft;
- a publication package;
- one aggregate commerce run with stage, selected artifacts, approval ids, and timestamps.

Product and design formats are strings or open candidate collections, not T-shirt, profession,
text, or illustration enums. The schema therefore preserves the founder’s open product scope.

### Capability-specific trust and approval policy

`packages/policies/commerce_gates.py` owns the four selection/execution gates:

1. opportunity selection;
2. concept selection;
3. artwork selection;
4. public publication.

Each gate loads a founder-owned mode: `required`, `optional`, or
`auto_approve_within_policy`. Initial HomeFromWorking config marks all four as `required`.
Auto-approval only opens a gate when the caller supplies a separately evaluated
`within_policy=True`; otherwise it falls back to a human approval. Agents cannot mutate or raise
their own trust configuration.

Gate checks validate the approval status, type, action, subject type, and subject id. A random or
mis-scoped approved record cannot unlock a stage. Rejections use canonical `PolicyViolationCode`
values.

### Persistent workflow and lineage

`packages/commerce/storage.py` stores one aggregate run as atomic JSON beneath the runtime state
tree. Every downstream artifact stores its direct parent id, while the run stores the approval id
used at each gate. The repository exposes a reverse-lineage query so the system can answer “Why
does this listing/publication package exist?” without reconstructing agent prompts.

The JSON seam is intentionally local-first and zero-setup. It can later be implemented by a
control-plane database store without changing the workflow contract.

### Workflow service

`packages/commerce/workflow.py` is a deterministic state machine. It permits research without
approval and refuses each subsequent mutation until its corresponding gate opens:

```text
research complete
  -> opportunity approval
  -> concepts generated
  -> concept approval
  -> design generated
  -> artwork approval
  -> product + listing drafts prepared
  -> publication approval
  -> publication-ready package
```

The service creates pending records in the existing `ApprovalStore`; the founder continues to
approve or reject through the existing control-plane approval surface. Publication-ready means a
fully prepared internal artifact only. No Etsy, Printify, payment, or public API call is included
in this slice.

### Replaceable external boundaries

`packages/commerce/adapters.py` defines protocols for research enrichment, concept generation,
design generation, and product/listing drafting. Deterministic fixture adapters provide the first
offline demonstration. Real Etsy, Printify, trend-source, and image-generation integrations can
replace one protocol at a time later.

The deterministic design adapter emits a representative local mock asset with explicit print
dimensions and placement metadata. It proves the artwork boundary without pretending the mock is
production creative quality.

### Business domain

`businesses/home-from-working/config/business.yaml` is the founder-owned source for business id,
initial marketplace/fulfillment choices, unrestricted product scope, and initial capability trust.
The business directory also documents what is configuration versus runtime output.

### Operator demonstration

An offline script exercises one profession-seeded opportunity. By default it stops at the first
pending approval. An explicit demo-only founder flag may approve all four internal gates to prove
the complete lineage and publication-ready output. It never performs an external action.

## Error handling

- Invalid stage transitions raise a commerce workflow error before writing state.
- Missing, pending, rejected, mismatched, or wrongly scoped approvals fail closed with a typed
  policy violation.
- Adapter output is validated before persistence; incomplete evidence or missing parents is
  rejected.
- Writes use the repository’s existing atomic JSON store so a crash cannot truncate a prior run.
- External adapter failures leave the last persisted stage intact and can be retried.

## Testing

Unit tests cover schema round trips, open product-format behavior, trust-mode behavior, approval
scope checks, stage ordering, persistence, reverse lineage, and the safe end-to-end fixture run.
The full Python lane is run before completion. No tests use live network services or real
marketplace credentials.

## Deferred work

- live research connectors specific to marketplace/fashion signals;
- image-generation providers and production preflight;
- Printify catalog/draft APIs;
- Etsy draft/publication APIs;
- performance ingestion and learned ranking;
- dedicated research, creative, or commerce workers;
- control-plane dashboard panels and database tables for commerce records;
- fulfillment monitoring and exception handling.

These are intentionally deferred until the contracts and approval spine see real operator use.
