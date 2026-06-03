---
status: pending
priority: p2
issue_id: "074"
tags: [code-review, security, abuse, denial-of-wallet, better-business-web]
dependencies: ["065"]
---

# Problem Statement

The CTA's only anti-abuse control is a honeypot, yet each genuine-looking
submission can trigger a "free website audit" — an outbound, compute- and
operator-consuming action (and the SSRF surface of 065). The form is an
amplification lever: cheap to submit, expensive to fulfill — undermining the very
build-credit discipline §4 is proud of. Separately, §11's "nothing auto-sends"
guardrail flatly contradicts §10's routing into an automated audit loop; an
honesty guardrail that's contradicted elsewhere can't be trusted to bound
behavior.

## Findings

- Honeypot is the sole control — [LANDING_PAGE_PLAN.md:155](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:155).
- Each submission can kick off a live audit (compute + operator time) — [LANDING_PAGE_PLAN.md:194](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:194).
- §11 "Nothing auto-sends; the form only collects inbound" — [LANDING_PAGE_PLAN.md:206](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:206) — vs §10 automated routing. Contradiction.

## Proposed Solutions

### Option 1: Decouple submission from audit + add a real anti-abuse control (recommended)
Never auto-trigger an audit on submit; require an explicit operator action per
submission and a daily audit cap. Add Netlify's spam filter / reCAPTCHA
(`data-netlify-recaptcha`) or hCaptcha. Reconcile §11 wording: "submission
triggers no outbound *to the prospect*; it enqueues an internal, operator-gated
audit."

Pros:
- Removes denial-of-wallet amplification; restores guardrail integrity

Cons:
- Adds a captcha + an explicit gate step

Effort: small-medium
Risk: low

### Option 2: Honeypot only, manual triage
Rely on the operator to ignore junk.

Pros:
- Nothing now

Cons:
- Operator-time exhaustion; guardrail contradiction remains

Effort: none
Risk: medium

## Recommended Action

Adopt Option 1: decouple submit→audit behind an explicit operator gate + daily
cap, add a captcha, and rewrite §11 to match actual behavior.

## Acceptance Criteria

- [ ] Submission never auto-runs an audit; an explicit operator gate + daily cap exist.
- [ ] A spam/captcha control beyond the honeypot is configured.
- [ ] §11 wording reconciled with §10 (no contradiction).

## Work Log

### 2026-06-02 - Initial review capture
Surfaced by security-sentinel during `/review`.
