---
status: pending
priority: p2
issue_id: "115"
tags: [open-tcg, watchlist, founder-decision]
dependencies: []
---

# OpenTCG: founder watchlist review (new candidates, subscription follow-up)

## Problem Statement

The most valuable upcoming products in the watched sets are not on the watchlist. NowInStock tracker suggestions went out on 2026-09-27, and nobody follows up on them.

## Findings

Upcoming products in watched sets, with TCGplayer presale market prices as of 2026-09-29:

- **Nov 6:**
  - 30th Celebration Ultra-Premium Collection: Day $567, Night $724
  - Ditto Premium Collection: $194
  - Figure Collections (Mew, Mewtwo): about $120 each
  - Classic Collection Pack: $308
- **Oct 2:** 10 30th Celebration Mini Tins (about $50 each) and the Mini Tin Display ($355).
- **Dec 4:** 30th Celebration ex Tins ($55–69) and the Binder Collection ($93).
- **Not a watched set:** Delta Reign, releasing Nov 6 (ETB $136, booster box $263 presale).

## Recommended Action

1. The founder picks the items to add and sets an `alert_at` for each.
2. Claude adds them to `watchlist.toml` and syncs NowInStock and Keepa through the Brave extension.
3. Once a week, check whether NowInStock added the 16 suggested trackers, and subscribe if so.
4. Renew NowInStock subscriptions before 2027-03-24.

## Acceptance Criteria

- [ ] The founder's decisions are applied, and the subscriptions match the watchlist.
- [ ] The NowInStock suggestion follow-up result is recorded.
