---
status: pending
priority: p2
issue_id: "103"
tags: [open-tcg, alerts, drawings]
dependencies: ["098"]
---

# OpenTCG: remind the founder when an announced drawing, queue or drop opens

## Problem Statement

Most TCG posts so far are announcements with a time: 13 of 28 are `drawing_scheduled`, for example "Walmart Drawings Confirmed for September 30th at 2PM PT / 5PM ET" or "Costco … Queue up … Drops at 8AM PT". The radar records them, but never reminds the founder at that time, even for watched sets.

## Proposed Solutions

1. **(Recommended)** Parse the announced date and time in the formats seen: "2PM PT / 5PM ET", "Wednesday, September 23rd", "10/3 from 12pm-2pm local time", "Opens Today at 2PM PT", "Tomorrow". Store the time on the episode. The sync job sends a reminder 5 minutes before it: "Walmart 30th Celebration drawing opens in 5 min", which opens the page under the retailer rules. Deduplicate by retailer, set and time.
2. Include tomorrow's announced events in the daily digest (todo 110).

## Acceptance Criteria

- [ ] The real announcement posts in the DB (e.g. 333) parse to the correct Pacific time. Ambiguous ones are skipped, not guessed.
- [ ] A reminder fires once, 5 minutes before the time, for watched sets or items only, and never for excluded terms.
- [ ] A later "cancelled" post for the same retailer and set cancels the pending reminder.
