# tcg-inventory — Pokémon singles inventory across TCGplayer and eBay

**TL;DR** — What you own, what you paid, where it physically is, and which
marketplace each card belongs on. Inventory is an append-only event ledger in
its own SQLite database; prices come from the sibling
[pokemon-tcg-search](../pokemon-tcg-search) catalog, attached read-only.
Run `make init && make status`.

---

## Why it is built this way

**The marketplaces are structurally asymmetric.** eBay has a full REST write
API. TCGplayer closed its API to new developers and has not reopened it, so the
only sanctioned write path is a CSV import in the Seller Portal — which is
gated to Level 4 sellers. eBay is the real-time leg; TCGplayer is a batch leg,
and at Level 1 it is a manual one. Every design decision below follows from
that.

**The two channels are capped in opposite ways.** TCGplayer Level 1 allows 100
items, $1,000 of listed value and $500 per item — a hard cap the marketplace
enforces, and a short-lived one, since Level 2 (500 items) is two delivered
orders away and Level 3 (50,000 items) is eleven. eBay is not meaningfully
capped at all: the account allows 5,000 items and $50,000 a month. What binds
on eBay is cost, not permission — only the first 250 listings each month are
free, and because Good 'Til Cancelled listings renew monthly and are charged
again on renewal, 250 is really a ceiling on *concurrent* listings before a
recurring bill starts. Both are modeled as data in `channels`, and the selector
plans to whichever ceiling is lower.

**Fees are not what separates the channels — labor is.** Both marketplaces take
about 13.25% plus a per-order fee. What differs is that TCGplayer lists against
a stock image in 30 seconds while eBay needs photos, a title and item specifics,
and that TCGplayer buyers fill a basket while eBay sales arrive one at a time
paying full postage each. `economics.py` computes the resulting breakeven
rather than hardcoding a threshold, so improving the listing flow lowers it.

## Layout

| Path | What |
|---|---|
| `inventory/schema.sql` | Tables, with the reasoning in comments |
| `inventory/seed.sql` | Conditions, states, event kinds, channel economics |
| `inventory/db.py` | Connections; attaches the catalog read-only |
| `inventory/ledger.py` | Append-only events and the state projection |
| `inventory/slots.py` | Binder slot allocation and the free list |
| `inventory/economics.py` | Net proceeds, breakevens, channel routing |
| `inventory/catalog.py` | Card search, condition pricing, price-quality checks |
| `inventory/selector.py` | Which cards to list, given the caps |
| `inventory/ebay_listing.py` | Titles, item specifics, descriptions |
| `inventory/photos.py` | Photo storage, HEIC handling, listing derivatives |
| `inventory/capture_app.py` | Phone-as-camera capture server |
| `inventory/tcgplayer_csv.py` | Seller Portal CSV round-trip |
| `inventory/pricing.py` | Repricing rules and the review queue |
| `inventory/ebay_email.py` | Reading sale notifications; the cross-delist trigger |
| `inventory/ebay_config.py` | Credential loading, sandbox and production kept apart |
| `inventory/views.sql` | Projections, dropped and recreated on every `init` |

## The two databases

`data/inventory.db` is **source of truth** and nothing can rebuild it.

`../pokemon-tcg-search/data/pokemon.db` is **derived** — 27,766 cards, 41,813
variants, ~36M daily price observations, refreshed by its own cron, and with a
`make clean-db` target that deletes it. It is attached as `catalog` with
`mode=ro` so an inventory bug cannot corrupt 971 days of price history. The
attach fails loudly rather than falling back to a writable one.

## Concepts worth knowing before reading the code

**A copy is one physical card, and holds identity only.** Where it is and
whether it is listed are projections of `events`, not columns. A mutable status
column is what silently goes wrong when a webhook fires twice.

**Being listed is not a state.** A card can be live on both marketplaces at
once, so listing status lives in `listings`, which is many-per-copy. The state
machine tracks only the physical container: collection, in_binder, outbound,
in_transit, sold, returned, lost. Every state maps to exactly one physical
container, so the ledger can be checked against the shelf.

**`events.idempotency_key` is the most important column here.** Order
notifications arrive as eBay webhooks and TCGplayer emails and both will be
delivered twice eventually. A `UNIQUE` key makes a replay a no-op instead of a
phantom second sale.

**A slot is a permanent address; cards move, numbers don't.** Page and pocket
are derived from `slot_number`, and freed slots are reused lowest-first so the
binder stays dense and visible gaps are real unsold capacity.

**Quoted prices are not always real.** TCGplayer pins market price when nothing
sells, so a vintage single can report the same number for months and then step
down hard. `catalog.price_health` reads the staleness, liquidity and
feed-artifact signals pokemon-tcg-search already computes, so a pricing
decision can refuse to act on a quote it shouldn't trust.

## Known gaps

These are the honest limits, in rough order of how much they matter.

- **`evaluate_channels` compares one price across both channels.** The real
  comparison needs a per-channel expected sale price: TCGplayer compresses
  toward the low because buyers sort ascending, while eBay often clears higher
  on desirable cards. That needs eBay sold comps, which are not wired up, and
  it is the single biggest thing missing.
- **The eBay title priority order is a hypothesis.** The defensible version
  ranks tokens by how much more often they appear in *sold* listings than in
  active ones. Same blocker: sold comps.
- **Velocity is a proxy, not a measurement.** TCGCSV publishes no sales counts,
  so selection ranks on price movement. Replace it with your own sell-through
  once there is enough.
- **The TCGplayer CSV path cannot be used yet, and is not close.** Pricing
  import and export in the Seller Portal is a **Level 4** feature, which takes
  51 delivered orders. `tcgplayer_csv.py` round-trips an export rather than
  generating a header, so it is ready when the account gets there, but it
  cannot be verified against a real file until then and TCGplayer stays a
  hand-listed channel in the meantime. `generate_blank` is for inspection
  only — do not upload it.
- **Quantity semantics are the least certain part of that format.** Whether
  delisting through CSV means a negative `Add to Quantity` or a zero
  `Total Quantity` has not been confirmed against a real export.
- **No eBay API client yet.** Sandbox credentials are in place; production is a
  separate application. Sandbox cannot see the real shelf, so a working sandbox
  client proves only that the requests are well formed.
- **Sale emails are parsed but not yet ingested.** `ebay_email.py` reads a real
  notification and matches it to a live listing, and `end_listing` already
  takes the idempotency key the replay protection needs. What is missing is the
  piece that watches the mailbox. The TCGplayer side has no sample yet.
- **Matching a sale to a listing is by title prefix**, because the eBay
  notification carries no item number. An ambiguous prefix deliberately matches
  nothing rather than guessing, so near-identical listings need distinct
  titles — otherwise the sale lands in a queue for you instead of delisting.
- **Condition multipliers are convention, not measured.** Re-fit from real
  sales and set `is_fitted`.
- **eBay aspect names are best-effort** and must be checked against
  `getItemAspectsForCategory` for category 183454 before publishing.

## Credentials

`.ebay.env` at the project root, gitignored, read only by `ebay_config.py` —
not from the process environment and not from the keychain, so there is one
place to look and one place to revoke. Sandbox and production are separate
keysets and asking for production when it is absent raises rather than falling
back, because a silent fallback means a delist that reports success and changes
nothing.

## Commands

```
make init                  # create and seed data/inventory.db
make status                # counts, slot usage, channel capacity, breakevens
make test                  # 28 tests, no dependency on the real catalog

python -m inventory find "Umbreon" --set "Evolving Skies"
python -m inventory intake                      # interactive batch session
python -m inventory intake --lot 1              # ...attached to an acquisition
python -m inventory add --variant 32055 --condition LP --cost 5.00
python -m inventory add --variant 32055 --no-slot    # keeper, not for sale

python -m inventory lot new --cost 400 --date 2026-11-01 --source "collection buy"
python -m inventory lot allocate 1              # pro-rata by market value
python -m inventory lot list

python -m inventory shelf                       # binder contents in slot order
python -m inventory pull 1                      # pull a sold card, free its slot

python -m inventory plan                        # what to list where, under the caps
python -m inventory reprice                     # what the pricing rules want to change
python -m inventory reprice --apply             # commit only the small, unblocked moves
python -m inventory tcgplayer-csv --template export.csv --out import.csv

make capture                                    # phone-as-camera server; open the printed URL
```

## Trying it without cataloguing 500 cards first

`scripts/make_demo_inventory.py` builds a realistic inventory in `data/demo.db`
— real catalog cards at a realistic price mix — and never touches
`data/inventory.db`.

```
python scripts/make_demo_inventory.py --copies 500
INVENTORY_DB=data/demo.db python -m inventory plan
```

## A session, end to end

```
$ python -m inventory lot new --cost 400 --date 2026-11-01 --source "collection buy"
lot 1: $400.00 on 2026-11-01

$ python -m inventory intake --lot 1
card: iono
   1. Iono - 269/193   269/193  Holofoil   $  47.05  Paldea Evolved
   2. Iono - 254/193   254/193  Holofoil   $  10.28  Paldea Evolved
   3. Iono - 185/193   185/193  Normal     $   0.30  Paldea Evolved
  pick # [1]:
  condition [NM]:
  cost, blank if from a lot []:
  → copy 1: Iono (Holofoil) NM @ $47.05
     put it in Binder 1, Page 1, Pocket 1
     tcgplayer  list — nets $40.10 after labor
     ebay       list — nets $35.78 after labor

$ python -m inventory lot allocate 1
Allocated $400.00 across 4 copies:
     $206.75  Iono - 269/193 (Holofoil)
     $129.58  Umbreon VMAX (Holofoil)
      $38.40  Iono - 254/193 (Holofoil)
      $25.27  Umbreon V (Holofoil)
```
