# OpenTCG radar

A local radar for sealed Pokémon TCG: when products are coming, where they
land, and when they restock. It is a personal lab that runs on the always-on
Mac. The plans are
[the data-source plan](../../docs/plans/2026-09-25-open-tcg-data-sources-plan.md)
and [build-out 1](../../docs/plans/2026-09-25-open-tcg-build-1.md).

```
make setup      # create .venv and install httpx + pytest
make test
make sync       # run every enabled poll source once
make calendar   # upcoming sealed releases with exclusives and presale prices
make events     # what changed in the last 7 days
make sources    # per-source health
```

## Inputs

- **`watchlist.toml`:** the founder's only input. Claude keeps the NowInStock
  and Keepa subscriptions in sync with it.
- **`data/`** (git-ignored): `radar.db`, `config.toml` (ntfy topic, inbox
  address), and `secrets/` (mode 0700).

## Sources so far

| Source | Tier | Cadence | Gives |
|---|---|---|---|
| tcgcsv (TCGplayer catalog mirror) | S | daily | Sealed SKUs, presale release dates, retailer exclusives, daily market price |
| Southern Hobby release list | L | daily | Distributor release and order-due dates |
| PokeBeach front-page RSS | L | 15 min | Reveals and product announcements |
| pokemon.com news | S | — | Disabled: bot challenge for non-browser clients, not bypassed |

The first successful run of each source is a silent baseline. After that,
new SKUs, date changes, new distributor listings and new news items become
calendar events.
