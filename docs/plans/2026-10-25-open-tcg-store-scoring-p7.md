---
status: open
change_id: open-tcg-store-scoring-p7
owner: founder
last_reviewed: 2026-10-25
---

# OpenTCG store monitoring P7: store scoring, hot tier and drop windows

**Parent plan:** [independent store monitoring](2026-10-23-open-tcg-indie-store-monitoring.md), phase P7 (design in its §8).
**Status:** Built 2026-10-25.

## Why

The founder wants to be at the store when a drop happens. The 15-minute sync is too slow for stores that list MSRP stock often, or for any store on a release day. P7 lets each store's own history and the release calendar set how often it is read.

## Design

### Score (`radar/stores/scoring.py`, table `store_scores`)

The sync refreshes scores hourly. Each polled store is scored over 14 days on:

- matched listings and how many are in stock
- **MSRP offers now:** in-stock offers at or below an evidence MSRP
- **MSRP hits:** alert-eligible store observations (P6's `store_offer_details`)
- new listings outside the baseline sweep
- the median time matched stock stayed in stock
- the read failure rate, from the new per-day `store_run_days` counts

### Tier and cadence

| Rule (first match wins) | Tier | Discovery |
|---|---|---|
| 8+ reads and half or more failed | registry tier | registry cadence × 4, at most 4 h |
| 2+ MSRP hits in 14 days | hot | 5 min |
| 3+ MSRP offers in stock now | hot | 5 min |
| otherwise | registry tier | registry cadence (15 or 60 min) |

- **Promotions only.** A store's registry tier is its floor; scoring never slows a healthy store.
- **Sweeps stay as before.** Full sweeps stay daily for every tier; the parent plan's "weekly for explore" is not adopted, because daily sweeps are what catch restocks of older listings.

### Drop windows

Hot and first-pass stores (not failing ones) are read every **2 minutes** while a drop window is open:

- **Release day:** from 05:00 local on the release day of any product in a watched set.
- **Fresh signal:** for an hour after a Bluesky, alert-email or store-email availability observation (in stock, pre-order, drop, queue, invites, drawing) names a watched set.

Watched sets come from the watchlist, the same way P4 resolves them, minus `[exclude]` terms. Chaos Rising and Pitch Black never open a window.

### Two readers, no overlap

- **`radar stores-fast`** is a new KeepAlive LaunchAgent (`com.ai-company-os.open-tcg.stores-fast`).
  - Every 30 seconds it computes each store's cadence and reads the newest page of the stores due under 15 minutes.
  - It skips any store whose robots.txt hasn't been checked and allowed.
  - It runs the P4 alert pass when anything changed.
- **The 15-minute sync** does everything else: other stores' discovery, every store's sweeps, robots checks, collection checks, the hourly score refresh, the MSRP sync and its own alert pass.
- **`radar store-scores`** (and `make store-scores`) prints each store's tier, cadence, metrics and reason, plus whether a drop window is open.

## As built (2026-10-25)

- The first scoring run promoted **CARDHAVEN TCG** to hot: 8 offers at or below MSRP in stock. It is unvetted, so its alerts carry the check-before-paying warning.
- The fast agent is installed and running. The sync's next run writes the live scores.
- Request load:
  - Each 5-minute store adds 12 requests an hour.
  - In a drop window, each hot or first-pass store makes 30 requests an hour, still one request at a time per store.
  - With today's 20 first-pass stores, a release day costs about 600 requests an hour across 20 hosts.
