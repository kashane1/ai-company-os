---
status: pending
priority: p2
issue_id: "113"
tags: [open-tcg, catalog]
dependencies: []
---

# OpenTCG: keep the release calendar complete and correct

## Problem Statement

These were found in the 2026-09-29 reliability review:

- **Presale sets go stale:** product lists are re-fetched only when the set's `modifiedOn` changes. Delta Reign (presale, releasing Nov 6) still shows 2026-09-03 and hasn't been re-fetched since Sep 26, so new SKUs added in presale may be missed. Whether TCGplayer bumps `modifiedOn` on product edits is unverified.
- **Singles stored as sealed:** 9 single cards are stored as sealed products, for example "Oshawott - 021/086 (Unova Poster Collection)". The sealed-name markers override the Number/Rarity check (`radar/catalog/classify.py`).

## Proposed Solutions

1. **(Recommended)** Re-fetch upcoming and presale sets daily regardless of `modifiedOn`; it's cheap, one request per set. Treat a product with a card number pattern such as `NNN/NNN` as a single, even if the name has a sealed marker in brackets. Add a cleanup that removes misclassified rows.

## Acceptance Criteria

- [ ] Upcoming sets are re-fetched every day, and a test shows a new presale SKU detected without a `modifiedOn` change.
- [ ] The 9 misclassified singles are gone, with a regression test.
