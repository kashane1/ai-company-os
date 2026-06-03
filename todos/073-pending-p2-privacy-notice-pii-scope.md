---
status: pending
priority: p2
issue_id: "073"
tags: [code-review, security, privacy, compliance, better-business-web]
dependencies: []
---

# Problem Statement

The public form collects PII (name, business, contact, current site) and routes
it to email/Slack and onward into a workflow, but the v1 scope (§3) contains no
privacy notice or data-handling statement. A production public form collecting
PII carries a baseline notice obligation (GDPR/UK-GDPR for EU/UK visitors,
CCPA/CPRA for California, CAN-SPAM/CASL if the operator emails an audit back).

## Findings

- Form fields collect PII — [LANDING_PAGE_PLAN.md:156](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:156).
- v1 scope list has no privacy item — [LANDING_PAGE_PLAN.md:83](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:83).
- §8 explicitly calls this a "production" site — [LANDING_PAGE_PLAN.md:165](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:165).

## Proposed Solutions

### Option 1: Add a short privacy line + one-page policy to v1 scope (recommended)
A sentence by the submit button (what's collected, that it goes to the operator
for a review, no resale, how to request deletion) plus a linked static privacy
page. No build impact.

Pros:
- Cheap, static; closes the baseline obligation

Cons:
- Minor copy/legal review

Effort: small
Risk: low

### Option 2: Defer to post-launch
Ship without it.

Pros:
- Nothing now

Cons:
- Launch-blocking compliance gap on a production site

Effort: none
Risk: medium

## Recommended Action

Add the privacy notice + policy as a v1 scope item (Option 1).

## Acceptance Criteria

- [ ] A data-use line appears adjacent to the form.
- [ ] A one-page privacy/data-handling policy is linked and in v1 scope.

## Work Log

### 2026-06-02 - Initial review capture
Surfaced by security-sentinel during `/review`.
