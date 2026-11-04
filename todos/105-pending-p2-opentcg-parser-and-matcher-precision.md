---
status: pending
priority: p2
issue_id: "105"
tags: [open-tcg, parsing, matching]
dependencies: []
---

# OpenTCG: tighten post classification and watchlist matching

## Problem Statement

Several classification and matching errors would produce wrong alerts, or miss real ones. These were found in the 2026-09-29 reliability review; the examples are synthetic unless a DB row is given.

## Findings

- **Cross-set false matches:** "Prismatic Evolutions ETB & Destined Rivals Booster Bundles restock at Target" matches 4 items, 2 of them wrong. Product words are not tied to their set (`radar/matching.py`).
- **No sold-out signal:** "Pre-Orders Sold Out" is classified as `preorder` and would alert.
- **"Drawing Goes Live Tomorrow"** is classified as `drawing_open`.
- **TCG check without Pokémon:** a Magic: The Gathering booster box passes the TCG check.
- **Stale classifications:** stored rows are never re-evaluated. Rows 14 and 26 are still `drawing_scheduled`, but the current parser says `drawing_open`.
- **Invites swallow restocks:** invites and drawings share the availability family with in-stock, so a real in-stock within 60 minutes of an invite post for the same item and retailer joins that episode, and no alert fires.

## Proposed Solutions

1. **(Recommended)** Require the product words to appear near their own set name. Add `sold_out`, `out_of_stock` and `ended` signals. Treat "tomorrow" or "goes live" plus a future time as scheduled. Require Pokémon context, or a known set name, for TCG. Give in-stock its own episode family, separate from invites and drawings. Add `radar reparse` to reclassify stored rows (episodes rebuilt, notifications never re-sent).

## Acceptance Criteria

- [ ] Each example above has a regression test and classifies correctly.
- [ ] `radar reparse` updates stored rows idempotently without sending notifications.
