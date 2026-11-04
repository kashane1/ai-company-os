---
status: pending
priority: p2
issue_id: "107"
tags: [open-tcg, alerts, founder-decision]
dependencies: []
---

# OpenTCG: decide the price-guard policy so real retail restocks are never hidden

## Problem Statement

An alert is suppressed when any report in the episode shows a price above the item's `alert_at` (`radar/notify.py`). The thresholds came from Guppy and may sit below real retail. For example, Keepa shows Amazon's own price for the 30th Celebration ETB at $89.99 (lowest ever $71.96), against an `alert_at` of $60. If a first-party retailer restocks at retail with the price in the post or email, the radar would stay silent.

## Proposed Solutions

1. **(Recommended)** Only suppress on price when the seller is a marketplace or reseller (Amazon third-party, Walmart Marketplace, eBay, TCGplayer). For first-party restocks, alert with the price and a tag such as "$89.99 · above your $60 max".
2. Keep today's strict behavior, but run a one-time threshold check that compares each `alert_at` with known retail from Keepa, NowInStock and presale data, and flags items whose threshold can never fire.

## Recommended Action

The founder picks a policy. Either way, run the threshold sanity check and review the flagged items with the founder.

## Acceptance Criteria

- [ ] The founder's decision is recorded in `watchlist.toml` comments and the README.
- [ ] Tests cover a first-party restock above `alert_at` and a marketplace listing above `alert_at` under the chosen policy.
- [ ] A threshold report lists items whose `alert_at` is below known retail.
