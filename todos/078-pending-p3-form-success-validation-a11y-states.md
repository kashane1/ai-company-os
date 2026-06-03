---
status: pending
priority: p3
issue_id: "078"
tags: [code-review, ux, accessibility, better-business-web]
dependencies: []
---

# Problem Statement

The form is the page's one interactive control, but the plan never specifies the
post-submit success state, the validation/error path, or the accessibility of
either. With the no-build file-digest upload there is no function intercepting
the POST, so a Netlify default success/error page renders — off-brand and, for
the page whose entire CTA is "request your free review," a blank conversion
moment.

## Findings

- No thank-you/success page specified; default Netlify redirect applies — [LANDING_PAGE_PLAN.md:149](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:149).
- §10 a11y attention is scoped only to "focus/contrast on themed cards" — [LANDING_PAGE_PLAN.md:198](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:198) — never reaching the form (labels, `aria-invalid`/`aria-describedby`, focus-on-error).
- No required-vs-optional fields, double-submit guard, or failure-page experience defined.

## Proposed Solutions

### Option 1: Author success + error states with a11y (recommended)
Add a `/thanks` (or inline) success page stating what happens next and the
expected response time; wire the form success redirect to it. Define required
fields + accessible inline error markup; disable the submit button on first
submit (double-submit guard); decide the failure-page experience.

Pros:
- Closes the conversion moment; form is accessible

Cons:
- A bit more copy + markup

Effort: small
Risk: low

### Option 2: Default Netlify pages for v1
Ship with Netlify's generic success/error.

Pros:
- Nothing to build

Cons:
- Off-brand; weak conversion; a11y gaps

Effort: none
Risk: low

## Recommended Action

Adopt Option 1; extend the a11y checklist to cover the form, not just cards.

## Acceptance Criteria

- [ ] A branded success state tells the requester what happens next + when.
- [ ] Required fields, accessible error states, and a double-submit guard are specified.
- [ ] The failure-page experience is defined.

## Work Log

### 2026-06-02 - Initial review capture
Surfaced by spec-flow-analyzer during `/review`.
