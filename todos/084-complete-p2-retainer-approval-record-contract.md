---
status: complete
priority: p2
issue_id: "084"
tags: [code-review, planning, approvals, architecture, agency]
dependencies: []
---

# Retainer Approval Record Contract

## Problem Statement

The updated plan correctly replaces the client-local approval inbox with canonical
`ApprovalRecord`s, but it only lists retainer action names. Current approval checks
do not authorize by action name alone: records carry `approval_type`, `subject_type`,
`subject_id`, `action`, and often a review artifact path. Policies such as
`is_approval_granted()` check expected approval type, and the token-audit path also
compares expected action and subject.

Without a complete retainer approval payload contract, implementers can create
approval records that are canonical but still ambiguous or incorrectly typed, making
policy checks brittle or easy to wire inconsistently across deploy, DNS, ads, billing,
and SMS gates.

## Findings

- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md` now says retainer approvals are canonical `ApprovalRecord`s.
- The plan lists action types such as `client_site_deploy`, `ad_campaign_go_live`, and `stripe_live_subscription`, but does not define matching `approval_type`, `subject_type`, `subject_id`, or required `review_artifact_path`.
- `apps/api/control_plane.py::request_approval` requires callers to provide `subject_type`, `subject_id`, `action`, and `approval_type`.
- `packages.policies.approvals.is_approval_granted()` validates `approval_type`, not the action string.
- `packages.policies.release_readiness` shows the higher-risk pattern: approval type, action, subject ID, and token audit need to agree.
- Known Pattern: `docs/solutions/architecture/agency-layer-reuse-and-repo-mechanism-footguns.md` warns that approval gates must be concrete policy functions, not loosely named markers.

## Proposed Solutions

### Option 1: Add A Retainer Approval Contract Table To The Plan

**Approach:** Extend the approval queue section with columns for `approval_type`,
`subject_type`, `subject_id`, `action`, required artifact, and policy gate function.

**Pros:**
- Keeps implementation unambiguous.
- Aligns with `ControlPlaneService.request_approval`.
- Makes tests easy to derive from the table.

**Cons:**
- Adds plan detail, but it is load-bearing detail.

**Effort:** 30-60 minutes

**Risk:** Low

---

### Option 2: Define Retainer Approval Constants In A Code Slice First

**Approach:** Leave the plan mostly as-is, but implement constants/dataclasses in
`packages/agency/approvals.py` or `packages/policies/agency_gates.py` and reference
those from the plan.

**Pros:**
- Lets code be the source of truth.
- Reduces future string drift.

**Cons:**
- The plan remains under-specified until the code lands.
- Harder for review to validate before implementation starts.

**Effort:** 2-4 hours

**Risk:** Low

---

### Option 3: Use One Approval Type For All Retainer Actions

**Approach:** Define `approval_type: retainer_action` for every retainer approval
and use `action` + `subject_id` for specificity.

**Pros:**
- Simple.
- Easier to list and filter all retainer approvals.

**Cons:**
- Less type-level protection for high-risk actions like live billing or DNS.
- Policy checks need to validate action and subject explicitly everywhere.

**Effort:** 1-2 hours

**Risk:** Medium

## Recommended Action

Resolved in the plan by adding a retainer approval record contract table with
`approval_type`, `action`, `subject_type`, `subject_id`, required artifact, and
policy validation expectations.

## Technical Details

**Affected files:**
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`
- Future `packages/policies/agency_gates.py`
- Future `packages/agency/approvals.py`
- Future `scripts/agency/list_retainer_approvals.py`
- Tests under `tests/python/unit/`

**Related components:**
- `apps.api.control_plane.ControlPlaneService.request_approval`
- `packages.schemas.approval.ApprovalRecord`
- `packages.policies.approvals.is_approval_granted`
- `packages.policies.approval_tokens`

**Database changes:**
- None expected.

## Resources

- Plan: `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`
- Known Pattern: `docs/solutions/architecture/agency-layer-reuse-and-repo-mechanism-footguns.md`
- Control plane approval API: `apps/api/control_plane.py`
- Approval schema: `packages/schemas/approval.py`

## Acceptance Criteria

- [ ] The plan or implementation defines `approval_type`, `subject_type`, `subject_id`, `action`, and required artifact path for every retainer approval.
- [ ] Policy gates validate both expected approval type and the specific action/subject when needed.
- [ ] High-risk retainer actions such as Stripe live subscription, DNS, and ad budget change cannot be approved with a generic or wrong-type approval.
- [ ] Tests cover at least one rejected wrong-type approval and one rejected wrong-subject approval.

## Work Log

### 2026-06-03 - Review Finding

**By:** Codex

**Actions:**
- Re-reviewed the updated plan against the approval schema and control-plane approval API.
- Confirmed the plan fixed the previous parallel-inbox problem, but still lacks the complete approval record contract.

**Learnings:**
- For this repo, "canonical approval" is necessary but not sufficient; the typed fields must line up with policy checks.

### 2026-06-03 - Plan Resolution

**By:** Codex

**Actions:**
- Added a typed retainer approval contract to the plan.
- Required policy gates to validate approval type, action, and subject ID.
- Required review artifacts for higher-risk retainer approvals.

**Learnings:**
- Approval action labels need to become a full payload contract before implementation starts.

## Notes

- This is a residual finding after todo 080. Todo 080 fixed authority; this one tightens the payload contract.
