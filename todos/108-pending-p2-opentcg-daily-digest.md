---
status: pending
priority: p2
issue_id: "108"
tags: [open-tcg, visibility]
dependencies: []
---

# OpenTCG: morning digest so the "when" signals are actually seen

## Problem Statement

The radar records "when" events, but the founder only sees them by running CLI commands. For example, on 2026-09-29 Southern Hobby moved the Mega Forces Tin release from Aug 28 to Dec 4, and 3 product news items arrived, but nothing surfaced them. Build-out 1 slice 5 also promised a daily digest.

## Proposed Solutions

1. **(Recommended)** At about 7 AM, after the 6 AM sign-in check, send one Mac notification with a short summary: new SKUs, date changes, new distributor listings, product news for watched sets, yesterday's episodes, today's announced drawings or queues, source health, and sign-in status. Also write `data/digests/YYYY-MM-DD.md` with the full detail.

## Acceptance Criteria

- [ ] Exactly one digest per day. It is skipped when there is nothing new, except for health problems.
- [ ] It includes everything from the last 24 h and today's announced events (todo 103).
- [ ] A test checks the digest content from fixture events.
