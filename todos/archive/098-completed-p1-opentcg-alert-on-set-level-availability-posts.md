---
status: completed
priority: p1
issue_id: "098"
tags: [open-tcg, alerts, matching]
dependencies: []
---

# OpenTCG: alert on availability posts that name only a watched set

## Problem Statement

Live posts often name only the set, for example "All 30th Celebration Drawings LIVE Now at Walmart!". The matcher needs an item name, so these posts get `watch_matches = []` and never alert. The earlier scheduled posts did name items, but announcements never notify. Result: neither 30th Celebration Walmart drawing (Sep 16 and Sep 23) would have alerted. The next one is confirmed for **Sep 30, 2 PM PT** (observation 333, 30th Celebration Booster Bundles) and will likely be missed the same way.

## Findings

- Verified in `data/radar.db`: observations 2, 14 and 15 are set-only LIVE posts with no watch matches. Observation 333 is the Sep 30 announcement and matched "30th Celebration Booster Bundle".
- The Costco `retailer_rule` already alerts on set names, but only for Costco (`radar/notify.py`, the `watch_items_or_sets` branch).

## Proposed Solutions

1. **(Recommended)** Generalize the set fallback to all retailers. An availability-family post that names a watched set (derived from the watchlist) but no item alerts as "<Retailer> · <Set> drawing/queue/drop". Exclusions still apply.
2. Also inherit the items named by a same-retailer, same-set announcement from the previous 72 h. The alert then says which products, for example "Booster Bundles, Mini Tin Display".

## Recommended Action

Implement option 1 now. Add option 2 as an enrichment, test-first, using real observations 2, 14, 15 and 333 as fixtures.

## Acceptance Criteria

- [x] A set-only LIVE drawing post for a watched set produces one notification that names the set and retailer.
- [x] If an announcement from the past 72 h named items, the notification lists them.
- [x] Posts for sets not on the watchlist, or with excluded terms, stay silent.
- [x] The existing Costco rule behavior is unchanged, and all tests pass.

## ✓ Completed 2026-09-30
Landed in the commit "feat(open-tcg): alert on set-level availability posts". Set-only availability posts for watched sets now alert at every retailer and list the items that retailer announced in the last 72 h. A rehearsal on a copy of the real database produced "30th Celebration · Walmart / Drawing open / Announced: 30th Celebration Booster Bundle" for the Sep 30 drawing.
