# OpenTCG radar

A local radar for sealed Pokémon TCG: when products are coming, where they
land, and when they restock. It is a personal lab that runs on the always-on
Mac. The plans are
[the data-source plan](../../docs/plans/2026-09-25-open-tcg-data-sources-plan.md)
and [build-out 1](../../docs/plans/2026-09-25-open-tcg-build-1.md).

```
make setup      # create .venv and install httpx, websockets, pytest
make test
make sync       # run every enabled poll source once
make calendar   # upcoming sealed releases with exclusives and presale prices
make events     # what changed in the last 7 days
make sources    # per-source health
make backfill   # recent posts from the Bluesky restock accounts
make stream     # follow Bluesky live (runs until Ctrl-C)
make feed       # restock observations from the last 72 h (TCG only)
make episodes   # restocks grouped across sources, with each source's lag
make scorecard  # per source: episodes, times first, median lag, accuracy
.venv/bin/python -m radar mark 12 real|false          # judge an episode (feeds accuracy)
.venv/bin/python -m radar log guppy "30th Celebration ETB at Target" --at "2026-09-26 04:51"
.venv/bin/python -m radar notify-test
```

**Episodes and alerts.** Reports of one watched product at one retailer
within 60 minutes form one episode, however many sources post it. Each
source's lag is measured from the first report. Each Bluesky account is
scored separately, and Guppy alerts logged with `radar log guppy` are scored
the same way. A native Mac notification fires once per episode when it is
for a watched item, is an availability signal (in stock, pre-order, drop,
queue, invites, open drawing), is under 15 minutes old, and has no known
price above the item's `alert_at`.

**Rules in `watchlist.toml`.**
- `[exclude] terms` never alert. Today these are "Pitch Black" and "Chaos Rising", newer sets that are still easy to find.
- `[[retailer_rule]]` alerts on any Costco drop that names a watched item or a watched set: 30th Celebration, Ascended Heroes, Prismatic Evolutions, Destined Rivals.
- **Assisted checkout:** with `open_in_browser`, the radar follows the post's short link. If the final URL is really on costco.com, it opens the page in Brave, where the founder is signed in, and the founder clicks Buy. Links landing anywhere else are never opened.

## Background service

Three per-user LaunchAgents run the radar without a Terminal window:

- `com.ai-company-os.open-tcg.stream` follows Bluesky live. KeepAlive restarts it, and it starts at login.
- `com.ai-company-os.open-tcg.inbox` reads the project Gmail read-only every 30 s (KeepAlive).
- `com.ai-company-os.open-tcg.sync` runs every 15 minutes and polls only the sources that are due: PokeBeach every 15 min, Southern Hobby daily, and tcgcsv once after its nightly rebuild.

A scheduled Claude task, "OpenTCG 6 AM retailer sign-in check", checks sign-in at Costco, Pokémon Center, Walmart, Target and Amazon in Brave. It writes `data/login-status.json` and notifies only when a store needs signing in.

```
scripts/launchd.sh install | uninstall | status
tail -f data/logs/stream.log        # live posts as they arrive
tail -f data/logs/sync.log
tail -f data/logs/inbox.log
```

The jobs only run while the Mac is awake and logged in.

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
| Bluesky (@pokemonrestocks, @nowinstockus) | S | live stream | Drawings, invites, queues, drops, in-stock and pre-order posts, matched to the watchlist |
| Project Gmail (NowInStock, Keepa, any Pokémon mail) | L | 30 s | Alert emails, read-only over IMAP, scored per sender |
| Guppy / sightings (manual log) | L | manual | Founder-logged benchmark entries (`radar log guppy …`) |
| pokemon.com news | S | — | Disabled: bot challenge for non-browser clients, not bypassed |

The first successful run of each source is a silent baseline. After that,
new SKUs, date changes, new distributor listings and new news items become
calendar events.
