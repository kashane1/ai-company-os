---
status: pending
priority: p2
issue_id: "042"
tags: [code-review, security, abuse, netlify, agency]
dependencies: []
---

# Problem Statement

`create-checkout.mjs` is a public, unauthenticated endpoint that mints real Stripe Checkout Sessions (and once live, enables real-money flows). No rate-limit pattern exists in any current function to copy, so these controls are net-new and the items most likely to be skipped under time pressure.

## Findings (security-sentinel H2)

1. **Session-creation rate limit** is the real lever (no money moves until checkout completes): per-IP cap (e.g. 5–10/hr via `x-nf-client-connection-ip` in a Blobs counter — do NOT trust `x-forwarded-for`) + a global circuit breaker so a botnet can't fan out across IPs to spam Stripe/Radar/Blobs.
2. **Tight per-cart ceiling:** bundles are $599–$1,799; a $50k single-line backstop is far too loose — cap total due-today low (e.g. ~$5k) and reject implausible sets.
3. **Honeypot** (`bot-field`, silent accept-drop) reused from `website-review.mjs`.
4. **Idempotency ≠ abuse control:** the key (sorted service_ids + server amounts + nonce) only collapses double-clicks; the rate limit is the abuse control.
5. **Stripe Radar** on for the live account — note in the go-live runbook.

## Proposed Solutions

### Option 1 (recommended)
Implement per-IP + global session rate limits in a Blobs counter store; honeypot; tight per-cart/$ ceiling; document Radar in runbook. Defer CAPTCHA (Turnstile) unless abuse appears.

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected: `products/better-business-web/site/netlify/functions/create-checkout.mjs` (+ a `bot-field` in the builder form). New Blobs counter store for rate limiting.

## Acceptance Criteria

- [ ] Per-IP + global session rate limits enforced; honeypot present.
- [ ] Per-cart $ ceiling proportionate to real bundle prices.
- [ ] Go-live runbook notes Stripe Radar.

## Work Log

(to be filled in)

## Resources

- /workflows:review round 2 (2026-06-06): security-sentinel H2
