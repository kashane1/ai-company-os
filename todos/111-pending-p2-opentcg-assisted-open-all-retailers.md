---
status: pending
priority: p2
issue_id: "111"
tags: [open-tcg, assisted-checkout]
dependencies: ["102", "104"]
---

# OpenTCG: assisted open for every retailer the founder is signed in to

## Problem Statement

The founder wants assisted checkout at Costco, Pokémon Center, Walmart, Target and Amazon. Today only the Costco rule opens a page in Brave. The 6 AM sign-in check already reports sign-in state per store; on Sep 28 Pokémon Center showed signed out.

## Proposed Solutions

1. **(Recommended)** Add a per-retailer `open_in_browser` option in `watchlist.toml` for watched-item and watched-set availability episodes.
   - Open only after the hardened link resolution in todo 102 confirms the retailer's own domain.
   - Skip the open, and note it in the banner, when `login-status.json` says that store is signed out.
   - For Pokémon Center and Walmart queues, open the queue page and let the founder wait in line. Never bypass queues, CAPTCHAs or bot checks.

## Acceptance Criteria

- [ ] For each enabled retailer, a verified watched availability alert opens exactly one tab (todo 104).
- [ ] Signed-out stores are skipped with a note.
- [ ] Nothing is added to a cart or submitted automatically.
