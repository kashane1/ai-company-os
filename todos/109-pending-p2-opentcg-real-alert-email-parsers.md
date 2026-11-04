---
status: pending
priority: p2
issue_id: "109"
tags: [open-tcg, inbox, parsing]
dependencies: ["100"]
---

# OpenTCG: build NowInStock and Keepa parsers from the first real alert emails

## Problem Statement

The email reader is generic, and its tests use synthetic NowInStock and Keepa emails written in an assumed format. No real alert has arrived yet, because none of the 12 tracked NowInStock items restocked between Sep 26 and 28. The real format, links, price fields and delivery delay are unknown.

## Recommended Action

When the first real alerts arrive:

1. Export them with `radar inbox-export`.
2. Sanitize them into `tests/fixtures/email/` (strip account links and tokens).
3. Replace the synthetic fixtures, and add sender-specific parsing for product, retailer, price, status (in stock, pre-order or out of stock) and the retailer link.
4. Measure the delay between NowInStock's event time and our receipt.

## Acceptance Criteria

- [ ] Real fixtures replace the synthetic ones, and parsing extracts retailer, product, status, price and link.
- [ ] NowInStock "out of stock" emails, if they exist, record a sold-out signal for todo 105.
- [ ] The scorecard reports email delivery delay.
