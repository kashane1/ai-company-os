---
status: complete
priority: p1
issue_id: "080"
tags: [code-review, planning, architecture, approvals, security, agency]
dependencies: []
---

# Retainer Approvals Must Use Control Plane

## Problem Statement

The plan introduces a new per-client approval inbox under `state/clients/<product_id>/approvals-pending.json` plus `approve.py`. That duplicates the repo's existing approval model instead of adapting to `ApprovalStore`, approval tokens, control-plane events, and policy gates.

For retainer ops, approvals cover deploys, DNS, review SMS, ad spend, budget changes, Stripe live charges, and pass-through overage discussions. A parallel JSON inbox risks becoming a less-audited path that bypasses the existing approval security model.

## Findings

- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:271` proposes "Approval inbox (minimal HITL UI = markdown + state)".
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:273` stores approvals in `state/clients/<product_id>/approvals-pending.json`.
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:279` proposes new `list_pending_approvals.py` and `approve.py` CLIs.
- `docs/architecture.md` says approvals are a platform/control-plane concept and that approval rules should be encoded in shared policy modules.
- Existing code already has `packages.db.approval_store.ApprovalStore`, `packages.policies.approval_tokens`, `apps.api.control_plane.ControlPlaneService`, `apps/api/approval_endpoint.py`, and `packages/tools/primitives/approvals.py`.
- Known Pattern: `docs/solutions/architecture/agency-layer-reuse-and-repo-mechanism-footguns.md` says approval gates are dedicated policy functions, not ad hoc markers.

## Proposed Solutions

### Option 1: Make Retainer Approvals First-Class Control-Plane Approvals

**Approach:** Revise the plan so RetainerOps creates `ApprovalRecord`s through `ControlPlaneService` or `packages.tools.primitives.approvals`, with subject/action types for retainer tasks.

**Pros:**
- Reuses the audited approval path.
- Keeps dashboard, events, tokens, and policies coherent.
- Avoids parallel approval semantics.

**Cons:**
- Requires defining retainer approval action names.
- Slightly more code than a simple JSON file.

**Effort:** 4-8 hours

**Risk:** Low

---

### Option 2: Treat `state/clients` As A Read-Only Projection

**Approach:** Keep client-local markdown/state files only as projections of canonical approval records, never as the approval source of truth.

**Pros:**
- Preserves convenient per-client visibility.
- Keeps the security boundary in the existing stores.

**Cons:**
- Needs projection sync and drift checks.
- More moving parts than simply listing canonical approvals.

**Effort:** 1-2 days

**Risk:** Medium

---

### Option 3: Drop The Client Approval Inbox For V1

**Approach:** Remove this plan section and list pending retainer approvals through the existing approval reviewer/dashboard until there is evidence a client-local projection is needed.

**Pros:**
- Simplest v1.
- Avoids YAGNI and duplicate state.

**Cons:**
- Less client-specific ergonomics in the first implementation.

**Effort:** 1 hour

**Risk:** Low

## Recommended Action

Resolved in the plan by replacing the client-local approval inbox with canonical
`ApprovalRecord`s through `ControlPlaneService` / approval primitives. Client-local
approval files are allowed only as read-only projections.

## Technical Details

**Affected files:**
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`
- Future `packages/agency/retainer_ops.py`
- Future approval CLIs, if any
- `packages/policies/agency_gates.py`

**Related components:**
- `ApprovalStore`
- `ApprovalTokenStore`
- `ControlPlaneService`
- `packages.tools.primitives.approvals`
- Operator dashboard approvals panel

**Database changes:**
- No migration expected; likely uses existing file-backed control-plane stores.

## Resources

- Architecture approval model: `docs/architecture.md`
- Agency approval pattern: `packages/policies/agency_gates.py`
- Approval primitive: `packages/tools/primitives/approvals.py`
- Known Pattern: `docs/solutions/architecture/agency-layer-reuse-and-repo-mechanism-footguns.md`

## Acceptance Criteria

- [ ] The plan names the canonical approval source of truth for retainer actions.
- [ ] Retainer approval actions use existing `ApprovalRecord`/token/event primitives or explicitly read from them.
- [ ] Any `state/clients` approval files are documented as projections, not approval authority.
- [ ] Policy gates fail closed when the canonical approval is missing, rejected, expired, or wrong action type.
- [ ] Tests cover at least one retainer approval-required action refusing without canonical approval.

## Work Log

### 2026-06-03 - Review Finding

**By:** Codex

**Actions:**
- Compared the plan's approval inbox proposal against the documented control-plane approval model and existing approval code.
- Flagged the new JSON inbox as P1 because it can become a bypass for spend, billing, deploy, DNS, and outbound-contact gates.

**Learnings:**
- RetainerOps needs convenience surfaces, but approval authority should stay in the platform layer.

### 2026-06-03 - Plan Resolution

**By:** Codex

**Actions:**
- Replaced the plan's approval inbox section with a control-plane-first approval queue.
- Added retainer approval action types.
- Specified that `scripts/agency/list_retainer_approvals.py` reads canonical approvals and that `approve.py` is not a new authority.

**Learnings:**
- Convenience projections are fine; authorization must remain in the existing approval system.

## Notes

- This does not block client-local run logs. It specifically blocks client-local approval state from becoming authoritative.
