---
status: active
owner: founder
last_reviewed: 2026-10-25
---

# OpenTCG: founder handoff

Everything the radar needs from you, in priority order. Claude has built everything it can do on its own. Each step below needs a human: your accounts, your money, or your judgment. Tick the boxes as you go, and tell Claude in a new session which ones you finished. The "Tell Claude" lines are the exact words to use.

**Where things stand (2026-10-25):**
- **Stores:** 89 polled, scored hourly. Hot stores are read every 5 minutes, and every 2 minutes on drop days.
- **MSRPs:** evidence-backed MSRPs for 148 of the 178 ETBs, bundles and displays released since 2020.
- **Alerts:** Mac alerts fire on MSRP hits from stores and sets you watch. A `radar deals` digest lists the rest, and OpenFlip receives each store offer with its MSRP.
- **Email:** 66 store email lists are subscribed, but their mail doesn't reach the radar yet (step 1).
- **Discord:** 28 servers send drop pings to your phone.

---

## 1. Turn on store email forwarding (about 10 minutes). Do this first.

Store drop emails, like TCG Moonblast's Friday 4pm release, go to **ksakhakorn@gmail.com**. The radar only reads the project inbox, **jimsimons01102000@gmail.com**. Until this filter exists, the radar never sees store email.

- [ ] **1a. Add the forwarding address.**
  1. In ksakhakorn@gmail.com, open Gmail **Settings** (the gear), then **See all settings**, then the **Forwarding and POP/IMAP** tab.
  2. Click **Add a forwarding address**, enter `jimsimons01102000@gmail.com`, then **Next** and **Proceed**.
  3. Gmail emails a confirmation code to the project inbox. Tell Claude: *"I added the forwarding address; read the Gmail confirmation code from the project inbox."* Claude can read it but won't click anything.
  4. Back in Settings, enter the code and click **Verify**.
  5. **Leave "Disable forwarding" selected.** Only the filter below should forward, not all of your mail.
- [ ] **1b. Create the filter.**
  1. In Terminal, in `products/open-tcg`, run `.venv/bin/python -m radar store-mail-filter`, or ask Claude for its output. It prints one line starting with `from:(…)` that lists about 60 store domains.
  2. In Gmail's search bar, open the search options (the sliders icon). Paste everything inside the parentheses into the **From** field.
  3. Click **Create filter**, tick **Forward it to:** `jimsimons01102000@gmail.com`, and click **Create filter**.
- [ ] **1c. Check it.** The next store email you receive should show up in `radar store-mail` (log: `products/open-tcg/data/logs/store-mail.log`). Some stores send through shared services (Shopify Email, Klaviyo). If a store's mail isn't being forwarded, tell Claude the sender address and it will add it.

## 2. Send the Moonblast example (2 minutes)

- [x] Forward TCG Moonblast's release email from last Friday to `jimsimons01102000@gmail.com`.
- [x] Tell Claude: *"I forwarded the Moonblast email; make it a test case."* A hand-forwarded email shows your address as the sender, so Claude will attribute it by its links and save it as a fixture. That proves the "email arrives → you're alerted in a minute" path on a real example.

Done 2026-10-25. The radar matched the forward to TCG Moonblast by its links and sent a Mac alert. It's now the test case `tests/fixtures/email/moonblast_forwarded.eml`, with addresses replaced and the unsubscribe token removed. The alert came 32 minutes late: the store-mail job was still running code from before the P5 store-reader update and failed on every poll until it restarted. The forward also showed that a forwarded email taught the radar your address as Moonblast's sender. That's fixed: senders are now learned only from the sender's own domain or name.

## 3. Confirm pending email signups (5 minutes)

- [ ] Open the confirmation emails in ksakhakorn@gmail.com from **Thirdspace TCG**, **Wulf Gaming**, **Common Lands** and, if one arrived, **Level Up Games**, and click each confirmation link. Until then those stores don't send you anything.
- [ ] Unsubscribe from **GoodStash TCG**'s emails. It's marked as a scam and the radar ignores it.

## 4. Vet CARDHAVEN TCG and PokéZone (judgment calls)

**PokéZone** (poke-zone.com) lists a Pitch Black booster box at $139.99, against a $161.64 MSRP, and runs pre-orders with unlimited stock. It has the same "too good" look, so look at it the same way.

**CARDHAVEN** (cardhaventcg.com) lists recent sets at about 90% of MSRP. Examples: a Perfect Order booster box at $143.10 (MSRP $161.64), and a Chaos Rising ETB at $43.49 (MSRP $49.99). The product matches are correct. It is the only "hot" store right now, so it's read every 5 minutes, and its alerts carry an "unvetted, check before paying" warning. It could be a real discounter, or the same pattern as GoodStash.

- [ ] For each store, look at its reviews and policies, then tell Claude one of:
  - *"Mark <store> avoid"*: it's never read again, like GoodStash.
  - *"Mark <store> checked"*: the store looks legitimate, and the warning drops from its alerts.
  - Nothing: it stays unvetted, with warnings.

## 5. Your first purchase turns on one-click opening

Store links only open in Brave automatically for stores whose trust is `purchased_ok`. Today no store has that.

- [ ] After your first good order from a store (it arrived, as described, at the right price), tell Claude: *"Mark <store> purchased_ok."* From then on, its MSRP alerts open the product page in Brave for you to check out.

## 6. Watch the first real drop: Delta Reign, Nov 6

On a watched set's release day, the radar opens a drop window: hot and first-pass stores are read every 2 minutes from 05:00.

- [ ] On Nov 6, note any store drop you see (on Discord, by email, or by visiting a store), and whether the radar alerted you and how fast.
- [ ] Tell Claude what you saw. Its first job after that day is a check-in: run `radar store-scores` and `radar deals`, measure how long MSRP stock lasted, and adjust cadence if stock sells out in seconds.

## 7. Discord: small cleanups (5 minutes)

- [ ] **Omni Collectibles:** in **#grab-roles**, open the dropdown and pick **Pokemon (Restocks, Drops and Pre-Orders)**. The role bot was timing out when Claude tried.
- [ ] Optional: finish **Fabricator's Forge**'s membership application (in Discord's "Pending Applications" folder). It asks questions only you should answer.

## 8. Decisions only you can make

Each has a default that Claude has already applied. Change any of them by telling Claude.

| # | Decision | Default now | The alternative |
|---|---|---|---|
| 8a | **Push to GitHub.** `main` has 36 local commits (all OpenTCG work, from the radar skeleton to today) that aren't on `origin`. | Not pushed | Tell Claude *"push main"*. |
| 8b | **Weekly MSRP refresh.** New presale products need an MSRP added as they appear (`radar msrp missing` lists them). | Manual: ask Claude now and then | A scheduled weekly Claude task does it. It costs a research run each week. |
| 8c | **Shipping in price classes.** Classes use the item price, so "at MSRP" means sticker price. Alerts show shipping and the total, e.g. "$49.99 + $9.99 ship = $59.98". | Item price | Class on the total. Few online offers would ever count as "at MSRP". |
| 8d | **Reading Discord on this Mac.** The radar can't read Discord servers; automated reading breaks Discord's rules. It could read Discord's notifications from macOS's notification database, but that needs **Full Disk Access** for the radar's Python, which also lets it read everything else on the disk. | Off | Grant Full Disk Access (System Settings → Privacy & Security → Full Disk Access) to `products/open-tcg/.venv/bin/python`, then tell Claude to build the reader. |
| 8e | **The rest of the OpenFlip app.** `packages/openflip` (60+ modules) and `apps/openflip-*` are another session's uncommitted work from early October. The bridge and export are committed; the service that imports store offers into OpenFlip isn't. | Left uncommitted | Tell Claude to test and commit it as-is, or to pick up where that work stopped. |
| 8f | **MSRPs for tins, collections and blisters.** About 640 in-stock offers have no MSRP because they're one-off products, not ETBs, bundles or displays. | Not researched | A research pass for the in-stock ones costs one research run. |
| 8g | **Rawmon** (La Mirada, CA) is local pickup only, no shipping. Its alerts only help if you're nearby. | Still polled | Tell Claude to park it. |

## 9. Optional: shipping rates still missing

Store shipping comes from each store's published policy: 12 stores have a flat rate and 35 a free-shipping threshold. Alerts and the digest show shipping when it's known.

- **Not verified (13 stores):** Shopify rate-limited the research partway through, so these weren't checked: Collector Store, Delightful TCG, Fox and Fable Games, Jaro Cards, JeffThrowCards, PokeMall TCG, Rolling Hills Collectibles, Sweets and Geeks, The Platypus Party, ThePokeHive, Omni Collectibles, TCG Hub and Hobbies, and PokéZone.
- **Calculated at checkout (about 20 stores):** these have no flat rate at all.

- [ ] Nothing needed. If you notice a store's shipping while shopping, tell Claude (*"<store> ships for $X, free over $Y"*). Or ask Claude to rerun the research for the 13 later.

## 10. Optional: stores still not covered

These stores aren't read by script. Each has its reason in `products/open-tcg/stores.toml`, and `radar stores` lists them.

- **Behind Cloudflare checks:** Game Nerdz, Out of the Box Cards, TCG Jackpot (plus Beckett Castle and Forge and Fire, which are covered by email). If you want any of them, sign up for their email list in your browser and tell Claude to mark them subscribed.
- **Closed or locked:** Decal Depo TF, PrCards, Prestige Collectibles, RareTCG and OneStopTCG (password-protected). Nothing to do.
- **Not shipping right now:** Larry's Game Store, parked. Tell Claude if it starts shipping again.
- **No readable product feed:** Collector's Cache (its robots.txt blocks crawlers), Hypno Comics, Level Up Games (covered by email and Discord), Thirdspace (covered by email), RNG-GAMEZ, CoreTCG and TCG Card Depot. Nothing to do unless one of them matters to you.

---

## Quick reference

| What | Command (in `products/open-tcg`) |
|---|---|
| Today's best offers by MSRP class | `make deals` |
| Store health, matches, MSRP classes | `make stores` |
| Store tiers, cadence and why | `make store-scores` |
| Products still missing an MSRP | `make msrp VIEW=missing` |
| Gmail filter search for store mail | `.venv/bin/python -m radar store-mail-filter` |
| Background jobs | `scripts/launchd.sh status` |
| Logs | `data/logs/` (sync, stores-fast, store-mail, inbox, stream) |

Details: [store email signups](store-email-signups.md), [store monitoring plan](../../plans/2026-10-23-open-tcg-indie-store-monitoring.md) and its phase plans P1–P7.
