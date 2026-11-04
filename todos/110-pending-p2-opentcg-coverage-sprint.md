---
status: pending
priority: p2
issue_id: "110"
tags: [open-tcg, sources, coverage]
dependencies: []
---

# OpenTCG: add free, permitted sources where live restock coverage is missing

## Problem Statement

Over 3 weeks the radar's free sources produced 28 TCG posts, mostly Walmart drawings. There were no live in-stock posts for Target or Pokémon Center, the retailers where Guppy competes hardest, and @nowinstockus posted no Pokémon content. No episode has yet been reported by two sources, so the scorecard can't compare anything.

## Proposed Solutions

1. **(Recommended)** More Bluesky restock accounts: search for them, follow the ones with real Pokémon restock posts in the last 30 days, and let the scorecard judge them. There is no code change beyond the account list in `radar/config.py`.
2. Reddit RSS, one fetch per minute or slower, for the subreddits that actually carry restock posts. Pick them by measuring post volume first.
3. Discord Channel Following. The founder joins the restock servers that offer announcement channels and creates a private server, then a bot reads the followed channels. This needs founder steps; it's the only legitimate way to ingest Discord.

## Acceptance Criteria

- [ ] Each new source is registered in `radar/sources.py` with its tier, cadence and health, and has fixtures and tests.
- [ ] After 2 weeks, the scorecard shows at least one multi-source episode, and a per-source volume, lead and accuracy table.
