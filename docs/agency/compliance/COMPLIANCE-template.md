# Compliance — {{CLIENT_NAME}}

> Per-client compliance record for Better Business Web. Agents and operators
> consult this before any outbound SMS/email to **this business’s customers**.
> Do not enable automated review or follow-up sends until the gates below are satisfied.

## Services that touch end customers

| Service | Status | Gate |
|---------|--------|------|
| Review request SMS (`reviews`) | **blocked** until addendum signed | Signed addendum on file |
| Follow-up automation (`follow_up_automation`) | **blocked** until Phase 8-E | Consent + sequence approval |
| Marketing email to customer's list | **not offered** in v1 | — |

## On file (check before first send)

- [ ] Signed [`review-sms-consent-addendum.md`](compliance/review-sms-consent-addendum.md) (or PDF scan)
- [ ] Owner confirmed **business phone** used as SMS sender is theirs to use
- [ ] Sample SMS template approved by owner (see `REVIEWS.md`)
- [ ] Opt-out language included in every template (“Reply STOP to opt out”)

## Review SMS rules (binding)

1. **Opt-in only** — messages go to customers who completed a paid service or
   gave explicit permission documented by the business.
2. **No purchased lists** — never import third-party numbers.
3. **Quiet hours** — default 9:00–20:00 in the business’s local timezone.
4. **Frequency cap** — default max 1 review request per customer per 90 days unless
   owner approves otherwise in writing.
5. **Human approval** — first template and any material change requires operator
   approval (`REVIEW_SMS_NOT_APPROVED` policy gate when implemented).

## Ads (client spend)

- Ad spend is billed on the **client’s** Google/Meta account, not ours.
- Pass-through tool costs (e.g. analytics over agency pool) require owner discussion
  before invoicing (see `OFFER.md`).

## Data retention

- Form leads: stored for reporting; do not sell or share.
- Delete on request within 30 days of a verified owner request (operator-handled).

## Notes

_Add operator notes, dates, and links to signed PDFs here._
