---
status: pending
priority: p2
issue_id: "041"
tags: [code-review, security, stripe, go-live, agency]
dependencies: []
---

# Problem Statement

Live charges are now wired behind `BYO_LIVE_ENABLED`. The plan pins mode server-side (good) but doesn't close the accidental-live-charge gaps: a flag/key mismatch could take live money while believing it's test, and lenient flag parsing could flip live on a typo.

## Findings (security-sentinel H1)

1. **Key/flag mismatch:** if the single `STRIPE_SECRET_KEY` is `sk_live_…` while the flag is off, you take live money in "test." Assert the selected key's prefix matches the mode (`sk_live_` when live, `sk_test_` when test) or refuse (503).
2. **Fail-closed parsing:** treat ONLY the literal string `"true"` as on; any other/unset value (`1`, `True`, `yes`, empty) → test. A typo must never enable live.
3. **Separate secrets:** mirror the webhook's split — `STRIPE_SECRET_KEY_TEST` / `STRIPE_SECRET_KEY_LIVE`, selected by flag — instead of one ambiguous key whose mode you can't tell from its name.

## Proposed Solutions

### Option 1 (recommended)
Add `STRIPE_SECRET_KEY_TEST` / `_LIVE`; select by strict `BYO_LIVE_ENABLED === "true"`; assert prefix matches mode; 503 if the required key is missing/mismatched. Document the parsing rule and the go-live runbook ($1–5 live proof + refund, Stripe Radar on).

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected: `products/better-business-web/site/netlify/functions/create-checkout.mjs`; Netlify env config; go-live runbook doc. Mirrors `stripe-webhook.mjs` test/live secret split.

## Acceptance Criteria

- [ ] Mode never client-selectable; only `"true"` enables live.
- [ ] Selected key prefix asserted against mode; mismatch/missing → 503.
- [ ] Separate test/live secret env vars in use.

## Work Log

(to be filled in)

## Resources

- /workflows:review round 2 (2026-06-06): security-sentinel H1
