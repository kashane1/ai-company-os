---
status: pending
priority: p3
issue_id: "044"
tags: [code-review, conventions, agency, polish]
dependencies: []
---

# Problem Statement

A cluster of small convention/consistency fixes that keep the new code aligned with existing repo patterns. Individually minor; grouped here for one pass.

## Findings (pattern-recognition P2-2/P3-1/P3-2/P3-4, architecture-strategist P3)

1. **`source` semantics:** `website-review.mjs` persists `source:"netlify-function"` (channel). The plan uses `source:"byo"` (product-line) on both Blob + metadata, conflating axes. Keep `source` = channel; carry product-line in the existing `bundle` field. Use one meaning identically across the `.mjs` Blob, Stripe metadata, and ledger.
2. **`ClientIntake.service_category` required but uncollected:** the minimal pre-pay form drops it (`intake.py:21-23` has no default). Make it optional/defaulted, or map a placeholder, so `process_inbound_order.py` can hand off without translation.
3. **Poller pair contract:** `process_inbound_order.py` should mirror `process_inbound_review.py` exactly (argparse + `__doc__`, `REPO=parents[2]` + `sys.path.insert`, delegate to `packages/agency/`, catch `FileNotFoundError`/`ValueError`→stderr+1, `raise SystemExit(main())`). `pull-orders.mjs` mirrors `pull-inbound.mjs` (`token()`, `sanitize()`, `BBW_SITE_ID`, delete-after-pull). Make OUT path explicit: `state/agency/inbound-orders/` (parallel to `stripe-events/`), not under `state/prospects/`.
4. **Registry key name:** keep `client.services` (not `client.service_ids`) to match `promote_prospect_to_client` (`promotion.py:111`).
5. **`create-checkout.mjs` is the first `.mjs` that mutates Stripe state + computes money** — call this deviation out explicitly; reuse `esc()`/honeypot/persist-first/`getStore` from `website-review.mjs` verbatim; keep `success_url`/`cancel_url` = the same `/welcome/` constant from `payments.py:158`.

## Proposed Solutions

### Option 1 (recommended)
Apply all five as a consistency pass during implementation; no design change needed.

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected: `create-checkout.mjs`, `scripts/web/pull-orders.mjs`, `scripts/agency/process_inbound_order.py`, `packages/agency/intake.py`, `packages/agency/promotion.py`.

## Acceptance Criteria

- [ ] `source` = channel everywhere; product-line in `bundle`.
- [ ] `ClientIntake` accepts the minimal intake without a required-field error.
- [ ] New poller/processor match the review-pair structure; OUT path under `state/agency/inbound-orders/`.
- [ ] Registry uses `client.services`; redirect URLs are the shared `/welcome/` constant.

## Work Log

(to be filled in)

## Resources

- /workflows:review round 2 (2026-06-06): pattern-recognition P2-2/P3-1/P3-2/P3-4, architecture-strategist P3
