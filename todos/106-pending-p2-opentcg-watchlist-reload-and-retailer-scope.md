---
status: pending
priority: p2
issue_id: "106"
tags: [open-tcg, watchlist, founder-decision]
dependencies: []
---

# OpenTCG: hot-reload the watchlist, and decide what per-item retailers mean

## Problem Statement

Watch items load once per daemon, so an edited `watchlist.toml` needs a daemon restart, which isn't documented. Rules and exclusions, by contrast, are re-read on every alert, so a half-saved file raises mid-alert. Separately, the per-item `retailers` field (for example "30th Celebration Booster Bundle" → Target only) is never read, so every item alerts at every retailer.

## Proposed Solutions

1. **(Recommended)** Reload everything when the file's mtime changes, validate it, and keep the last good copy if parsing fails. Notify once on an invalid file.
2. **Founder decision:** should `retailers` restrict alerts, or only guide which subscriptions to create? Recommendation: keep alerting everywhere, because a Walmart drawing for a Target-tagged item is still useful, but label out-of-list retailers in the banner. Rename the field to `subscribe_at` to make that clear.

## Acceptance Criteria

- [ ] Editing `watchlist.toml` takes effect within a minute, with no restart.
- [ ] A broken file keeps the last good policy and produces one warning notification.
- [ ] `retailers` semantics are documented and tested per the founder's decision.
