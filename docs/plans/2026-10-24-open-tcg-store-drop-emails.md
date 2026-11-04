---
status: open
change_id: open-tcg-store-drop-emails
owner: founder
last_reviewed: 2026-10-24
---

# OpenTCG: store drop emails

**Parent plan:** [independent store monitoring](2026-10-23-open-tcg-indie-store-monitoring.md). This is the inbox lane from that plan's §6, moved ahead of P3 at the founder's request: "I want to get there right at the time of the drop."

**Status:** Built 2026-10-24. 14 stores are subscribed, 52 Shopify-form stores are on the founder's checklist ([store-email-signups.md](../products/open-tcg/store-email-signups.md)), and `radar store-mail` runs under launchd. The founder's Gmail forwarding filter is still to do.

**Goal:** know which stores email their subscribers about drops, restocks and preorder openings, and subscribe to all of them. When one of those emails arrives, the founder should know within a minute which store it's from, whether it's a Pokémon drop, and what the store has listed right now and at what price.

## What exists to build on

- **The radar already reads a Gmail inbox.** `radar/inbox/` polls the project inbox (`jimsimons01102000@gmail.com`) every 30 seconds, read-only, under a KeepAlive LaunchAgent. Today it only looks at NowInStock, Keepa and Pokémon-related mail.
- **The store collector can read any polled store on demand.** `radar/stores/` holds every polled store's listings, matched to the reference catalog with market prices.
- **What's missing:** store signups, knowing which store sent an email, separating drop emails from promotions, and acting on a drop email right away.

## Survey (2026-10-24)

One homepage read per store looked for signup forms, email tools, restock apps and Discord links. The drop-specific stores were then confirmed by reading their page text. Full results: [`2026-10-24-store-email-signup-survey.json`](../products/open-tcg/research/2026-10-24-store-email-signup-survey.json).

| Kind | Stores | Notes |
|---|---|---|
| **Drop-specific email** | 10 | VGMX (per-category alerts, Pokémon included), TCG Slayer (drops newsletter), PokeMall (drop dates, restock alerts, preorder windows), Indy Card Shop (early access to drops), TCG Moonblast (drops signup), Thirdspace (early preorder news), Omni Collectibles ("MSRP drops"), Sweets and Geeks, Galactic Toys, Over the Brick |
| Generic newsletter | 64 | Shopify customer form (56), Klaviyo (20), Omnisend, Mailchimp, Shopify Forms, MailerLite |
| Restock button only | 7 | A per-product "notify me" app but no newsletter: 1st Capital, Black Vault, Geekery, Retro Gaming of Denver, RNG-GAMEZ, ThePokeHive, Underhill |
| None found | 19 | Includes CARDHAVEN, Cardtopia, Shippin Texas, Mantis, PunkOuter, TCG Card Depot. Some show a popup only through scripts, so the browser pass rechecks them. |
| Unreachable by script | 9 | Cloudflare (Beckett Castle, Forge and Fire, Game Nerdz, Out of the Box, TCG Jackpot). HTTP 402, likely closed (Decal Depo TF, PrCards, Prestige Collectibles). HTTP 423 (RareTCG). |
| Discord server | 30 | Common Lands and Croma say Discord is where drops are announced first |

## Decisions

- **Signup address:** `ksakhakorn@gmail.com`, plain, as the founder chose. It isn't the radar's inbox, so the radar sees store mail only after the founder adds a Gmail filter that forwards it. The filter's sender list grows as welcome emails reveal each store's sender. Until then, drop emails reach the founder's own inbox and phone as normal.
- **Signups happen in the browser, one store at a time.** Any interactive CAPTCHA is left for the founder, never solved. Cookie banners get the most private option. Double opt-in confirmation emails land in the founder's inbox, and only the founder can click them.
- **Discord isn't automated.** The radar doesn't read Discord. The 30 servers are listed for the founder to join by hand.

## Build

1. **Registry fields** in `stores.toml`: `email_signup` (`drop` | `newsletter` | `restock_button` | `none` | `unreachable`), `signup_url`, `discord`, and `subscribed_on` once signed up.
2. **Store mail reader** (`radar/stores/mail.py`, a new `store_email` source):
   - It reads the same project inbox read-only, reusing the existing IMAP client and parser.
   - It keeps its own cursor and query, so the radar's existing inbox code is untouched.
   - It runs every 30 seconds as a new `radar store-mail` command under its own LaunchAgent.
3. **Attribution.** Which store sent this, in order:
   - a sender address seen before (`store_mail_senders`)
   - the sender's domain matching the store's
   - the sender's display name matching the store's name
   - the email body linking mostly to one store's domain
4. **Classification:**
   - `drop`: drop, live, restock, back in stock, preorders open, release, just landed, new arrivals, available now
   - `subscription`: welcome or confirm, which also records that the signup worked
   - `promo`: sale or discount wording
   - `other`
   - A separate Pokémon flag comes from Pokémon wording or a known set name.
5. **On a Pokémon drop email:**
   - If the store is polled, read its newest page immediately.
   - Send a Mac notification naming the store and the email subject, plus any in-stock matched listings from the last two hours with price and market price.
   - For an unpolled store (Moonblast, Thirdspace), the notification carries the email's main link instead.
   - One notification per store per 30 minutes.
6. **Lead time.** Record the email's send time against when the store's new listings first appeared. This shows whether each store emails before or after listing, which decides which stores are worth the subscription.

## Done when

- Every reachable store with a signup is subscribed, or listed with the reason it isn't (CAPTCHA, no form, closed).
- Synthetic store emails in tests cover attribution, classification, the throttle and the immediate store check.
- `radar store-mail` runs under launchd against the project inbox, and the founder has a forwarding filter recipe.

## As built (2026-10-24)

- **Signups.** 14 subscribed in the browser:
  - Drop-specific: Moonblast, TCG Slayer, Thirdspace, Wulf, Flipside (Pokémon feed), Stonebrook, Poke-Collect, Kollect Korner, TCG Stadium.
  - Newsletters: Loose Packs, Common Lands, Level Up, Beckett Castle, and Forge and Fire (already subscribed).
  - Shopify's built-in customer form showed an hCaptcha challenge on every store tried (VGMX, PokeMall), so the 52 stores using only that form went to the founder. The browser pass also found 15 more stores with no signup. Omni's "MSRP drops" are a spend-based loyalty program, not an email list.
- **Registry.** `stores.toml` gains `email_signup`, `email_status`, `email_subscribed_on` and `discord`.
- **Reader.** `radar/stores/mail.py`:
  - It subclasses the existing read-only IMAP client with its own query and cursor (`store_email` source).
  - Unrelated personal mail isn't stored.
  - Sender addresses are learned once a store is attributed.
  - Drop emails older than 60 minutes are recorded but don't notify.
  - `collect.check_store_now` does the immediate newest-page read, using the store's existing robots decision.
- **Verified:** 13 tests with synthetic store emails, and a live `--once` run against the project inbox (0 store emails, as expected before forwarding). The LaunchAgent is installed and running.
