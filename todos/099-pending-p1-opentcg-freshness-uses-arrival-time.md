---
status: pending
priority: p1
issue_id: "099"
tags: [open-tcg, alerts, reliability]
dependencies: []
---

# OpenTCG: gate alert freshness on arrival time, not the poster's timestamp

## Problem Statement

The 15-minute freshness gate (`radar/notify.py`, `MAX_AGE`) and episode timing use the post's own `createdAt`. Some posts reach the radar long after that timestamp, so a real watched restock can be dropped as "stale" the moment it arrives. The scorecard would also credit that source with a lead nobody could act on.

## Findings

- Verified in `data/radar.db`: @nowinstockus observations 393, 396 and 398 arrived 35, 25 and 22 minutes after `createdAt`. The Jetstream cursor matches the arrival time, so the delay happened before Jetstream, not in our process.
- Email `Date` headers can lag the same way.

## Proposed Solutions

1. **(Recommended)** Store an `arrived_at` per observation: Jetstream `time_us`, the author-feed `indexedAt`, or the IMAP receive time. Gate freshness on it.
2. Also record the delivery delay (`arrived_at - source_time`) per source, and show it in the scorecard.

## Recommended Action

Add the column with a schema migration and backfill it from `received_at`. Gate freshness on arrival time, and use arrival time for the "reported first" lag. Keep `source_time` for display.

## Acceptance Criteria

- [ ] A watched in-stock post that arrives 30 minutes after its `createdAt` still notifies.
- [ ] Old posts replayed by a backfill still stay silent.
- [ ] The scorecard shows median delivery delay per source.
- [ ] A test covers late delivery for both stream and email.
