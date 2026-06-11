# Manual Prospect Verification SOP (browser-based, no paid APIs)

> **TL;DR** — We no longer pay for Brave/DataForSEO search. Instead an agent drives
> the operator's logged-in Chrome (`mcp__Claude_in_Chrome__*`) to check each prospect
> on Google Maps / Google / Facebook / Instagram, and records: (1) a **web-presence
> verdict**, (2) the **Google review count** (demand), and (3) the **best contact
> channel**. Work is split across N parallel chats by deterministic shard so no two
> chats ever touch the same record. Each chat loops:
> `verify-web-export` → browse → fill JSON → `verify-web-ingest`. Slower than an API,
> and that's fine — accuracy over throughput. A lighter **contacts-only pass** exists
> for already-verified targets (see below).

This is the canonical procedure. The tooling lives in
`packages/prospecting/manual_verify.py`; verdict logic is reused unchanged from
`packages/prospecting/web_presence.py` (`classify_web_presence`).

---

## Why this exists

Overture/FSQ source imports (the `S_source_candidate` cohort, ~12.6k unverified)
are a valid **source queue**, not verified prospects: they arrive with no Google
review count (`user_ratings_total = 0` = *unknown* demand) and an unverified web
presence. Browsing reveals **both** at once — whether the business has an owned
website, and how many reviews it has — which can promote a real one straight into
`A_gold`.

## Worker-chat runbook (you are chat #K of N)

You will be told "you are chat #K of N" (e.g. chat #2 of 4 → `K=2`, `N=4`). Your
shard index is `K-1`. Loop until your shard is empty:

1. **Export your shard:**
   ```
   python scripts/prospect_scan.py verify-web-export \
     --cohort S_source_candidate --shard <K-1> --shard-count <N> \
     --limit 25 --out state/prospects/manual/chat<K>-batch.json
   ```
2. **Browse** each row per the procedure below, editing the JSON in place.
3. **Ingest:**
   ```
   python scripts/prospect_scan.py verify-web-ingest \
     --in state/prospects/manual/chat<K>-batch.json
   ```
4. Repeat. When step 1 prints `rows=0`, your shard is done.

> Only ever pass **your own** `--shard <K-1>`. Never touch another chat's shard or
> batch file. Sharding is `sha1(place_id) % N`, so shards are disjoint and
> exhaustive — each record JSON is written by exactly one chat, no locks needed.

## Per-business procedure

**Maps-first, decide directly.** Most verdicts are fully determinable from the
Google Maps listing alone — set the verdict yourself via `verdict_override` + a
short `note`. The `results`/classifier path is a *fallback* for when you genuinely
can't tell. For each worklist row, stop as soon as the verdict is clear:

1. **Google Maps** (`maps_url`) — your primary source. Confirm name + address match,
   then read:
   - **"Permanently closed" / "Temporarily closed"** banner → drop (see rulings).
   - **review count** → `review_count` (this is the demand signal Overture lacked).
   - the **Website** field → an owned domain / builder page (`*.square.site`, Wix,
     Squarespace, Google/GoDaddy Sites) means `owned_site` (drop); *Add website* with
     no link is a strong no-site signal.
   - **phone** and any Instagram / Facebook / booking links.
   Set `verdict_override` directly from what you see, with a `note` saying why.
2. **Contacts** — capture the best reachable channel into `contacts` (priority:
   email → instagram → facebook → booking_url; phone is already on the record).
   Skip this for `owned_site` drops — don't waste time.
3. **Google web search** (`search_query`) — only when Maps is inconclusive (ambiguous
   web presence, possible parasite-SEO domain, name collision). Either judge it and
   set `verdict_override`, or paste the top hits into `results: [{title, url,
   description}]` and let the classifier decide. (Note: web search may be
   CAPTCHA-blocked under heavy concurrency — see the shared-IP ruling; lean on Maps.)
4. **Facebook / Instagram** — only to confirm an ambiguous case or grab a contact
   Maps didn't show.
5. **Integrity check** (see flags below): chains, lead-gen/SEO fronts, parasite-SEO
   pages, service-area-only operators → drop or `ambiguous` with a clear `note`.

### Verdict reference

| Situation | Verdict |
|---|---|
| Owned domain / builder page (incl. `*.square.site`, Wix, Google Sites) that is their real site | `owned_site` → **drop** |
| Only Yelp / Booksy / Vagaro / Square-booking / BBB / menu-host / directory | `marketplace_only` → **primary target** |
| Only Facebook / Instagram / Linktree | `social_only` → social-specific pitch |
| No real web presence anywhere | `none_found` → target if a channel is reachable |
| Name collision / parasite-SEO / multi-brand / genuinely unclear | `ambiguous` → hand-review |

Prefer setting `verdict_override` directly. Only fall back to leaving `results` for
the classifier when you can't judge it yourself. The `verdict_url` field should hold
the URL backing your verdict (the owned site for a drop, or the real Yelp/social/
marketplace page for a target).

### Integrity flags (drop / escalate — do not build)

Cross-check Google + Yelp for: chains/franchises, **lead-gen / SEO operations**
(one phone across many "brands", stock photos, no real address), service-area-only
operators (no storefront, not owner-operated), and scam/fraud reports. See the
lead-gen network pattern in `docs/demo-site-build-playbook.md`. Flag with
`verdict_override: "ambiguous"` (or `owned_site` to drop) + a clear `note`.

## JSON result schema (what you fill per row)

The export pre-fills each row with blank slots. The normal path fills
`verdict_override` + `note` + `review_count` + `contacts`; `results` is only for the
fallback classifier path. Edit only these fields:

```json
{
  "place_id": "source/overture:...",        // do not change
  "verdict_override": "marketplace_only",    // PRIMARY: your direct verdict
  "verdict_url": "https://yelp.com/biz/...", // the URL backing your verdict
  "note": "GBP Add website; Yelp 4.2/180",   // why — what you saw on Maps
  "review_count": 180,                        // integer from Google Maps, or null
  "contacts": {
    "email": "hi@biz.com",
    "instagram": "@biz",
    "facebook": "https://facebook.com/biz",
    "booking_url": "https://booksy.com/..."
  },
  "results": []                              // FALLBACK only: paste hits here and
                                             // leave verdict_override "" to let the
                                             // classifier decide when you can't judge
}
```

`verify-web-ingest` then writes, per record: `web_verify_verdict` (+ url,
confidence, note, `web_verify_method = manual_browser`), `user_ratings_total` (when
`review_count` given, which recomputes the cohort), and the `contact_*` fields. A row
with an empty `verdict_override` **and** empty `results` classifies as `none_found` —
so only leave both empty when that's genuinely the answer.

After a successful ingest, **delete your batch file** so a token-limit stop never
leaves un-ingested browse work stranded in `state/prospects/manual/`.

## Contacts-only pass (for already-verified targets)

Some businesses are already verified as no-site targets but lack a digital contact
channel (e.g. the ~700 sample-site businesses). They do **not** need the full verify
process — re-running it would redo verdict work and could overwrite a good verdict.
Use the lighter contacts-only path, which writes **only** the contact fields and
never touches the verdict/cohort:

```
# export (optionally restrict to a place_id list, e.g. the sample-site businesses):
python scripts/prospect_scan.py verify-web-export --contacts-only \
  --ids state/prospects/manual/sample921.ids --shard <K-1> --shard-count <N> \
  --limit 25 --out state/prospects/manual/contacts-chat<K>.json
# ...browse each row, fill contacts...
python scripts/prospect_scan.py verify-web-ingest --contacts-only \
  --in state/prospects/manual/contacts-chat<K>.json
```

Per row: open `known_url` (their Yelp/marketplace/social page — already on file) and
the `maps_url`, and grab the single best digital channel into `contacts` (priority
email → instagram → facebook → booking_url). Phone is already on the record, so a
phone-only business needs nothing. Don't gather a verdict, reviews, or anything else.
`none_found` businesses have no web presence by definition — skip them; phone is
their contact.

## Edge-case rulings

Refined during trial runs — append new rulings here so all chats stay consistent:

- **Shared-IP Google CAPTCHA (2026-06-10, many concurrent chats).** With ~20 chats
  hammering Google from one IP, `google.com/search` starts returning the
  "unusual traffic" / `/sorry/index` CAPTCHA page. **Do NOT solve it** (prohibited).
  Google **Maps** stays usable far longer — lean on the Maps listing as the primary
  signal: open/closed, review count, the **Website field** (owned domain → drop;
  `m.facebook.com` → social_only; `*.square.site`/`order.toasttab.com`/`order.online`
  → marketplace/owned), and phone. Most verdicts are fully determinable from Maps
  alone. When the GBP shows *Add website* and you can't web-search to find the
  social handle, still record the verdict from Maps (review count = demand) and note
  "web-search contact discovery CAPTCHA-blocked"; leave contacts to the phone. Retry
  web search occasionally — the block is intermittent and clears after a pause.
- **Check "Permanently closed" FIRST.** Open Google Maps before anything else. If
  the listing shows *Permanently closed* (or Yelp/Tripadvisor say CLOSED and a
  different business now sits at the address), it's a **drop** — set
  `verdict_override: "owned_site"` (or `ambiguous`) with a note like
  `"PERMANENTLY CLOSED; ..."` and move on. Don't waste time gathering contacts.
  Closed listings still carry their old review count — record it for accuracy, but
  the verdict is what gates them out downstream (a high review count would
  otherwise recompute the cohort into A_gold/A2).
- **`*.square.site` / `*.squarespace.com` / Wix / Weebly builder pages with a real
  menu, hours, or ordering = a site → `owned_site` (drop).** These are functional
  branded sites even without a custom domain. (The classifier treats `square` as a
  marketplace host and would say `social_only`/`marketplace_only` — override to
  `owned_site` when the page is clearly their primary site.)
- **Registered LLC + scraper directories + bare unclaimed GBP, no owned
  site/social/Yelp = `none_found`,** not `ambiguous`. A `.gov` business
  registration or a maptons/menupages/menu-world scraper page is not a real web
  presence. The classifier may return `ambiguous` off these — override to
  `none_found`. A FL/out-of-state phone on a local address + ≤1 review usually
  means a dormant or mobile/home operator.
- **Owned custom domain matching the name (e.g. `150sunset.com`) = `owned_site`
  (drop),** even if the classifier missed it because the host tokens didn't line
  up. Put the domain in `verdict_url`.
- **Parasite-SEO domain matching the name is NOT an owned site — do NOT drop.**
  Tells: GBP itself shows *Add website* (owner claims none); the page uses
  templated AI copy ("Discover X in <City>, known for…" / "a true hidden gem");
  Google reviews are scraped verbatim (same reviewer names as the GBP); contact
  is a generic `<name>.shop@gmail.com` / `<name>.online` with no real social
  links; footer reads `© <year> <domain>`. Common hosts: `*.shop`, `*.online`,
  `restaurants-world.net`, `goto-where.com`, `*.weeblyte.com`,
  `restaurantmenu.us.com`. Because the host token-matches the name the classifier
  will wrongly say `owned_site` — **override to the real directory verdict**
  (`marketplace_only` if Yelp/Apple/MapQuest exist, else `none_found`), put the
  Yelp/marketplace URL (not the parasite) in `verdict_url`, and DON'T use the
  parasite gmail as a contact. These are high-value no-website targets, not drops.
- **Competitor design-studio-hosted marketing page = `owned_site` (drop,
  contested).** A *complete, polished* marketing site for the business hosted on
  another studio's domain as a subpage (e.g. `cadizstudio.com/<biz-name>/`, with
  the biz's real menu/hours/contact form/gallery and a `© <year> <Biz> · STUDIO
  NAME` footer) means a rival agency has already built or is pitching them a site.
  Even though it's not a custom owned domain, a functional site exists, so it's not
  a clean no-website target — set `verdict_override: "owned_site"`, put the studio
  page in `verdict_url`, and note it's a competitor build (not self-owned). Tell:
  the footer credits a studio/agency, the URL path is `<studio-domain>/<business>`,
  and the business's own GBP may still show *Add website* (they haven't adopted it).
- **Mismatched phone/address on a name-matching `.com` = parasite/lead-gen, NOT
  owned (extra tell, 2026-06-10).** If a custom `.com` token-matches the name but
  the phone and/or street number on the page DIFFER from the GBP (seen on
  `baymeadowscafeandgrill.com`: site showed `7979 Baymeadows Way` + `(904)
  923-0646` while GBP showed `7910` + `(904) 423-1064`), it's a scraped lead-gen
  capture page that inserted a tracking number — treat as parasite. Corroborating
  tells: GBP shows *Add website*, templated About copy, and `*.menu-world.com` /
  `*.weeblyte.com` siblings exist for the same business. Override to
  `marketplace_only` (or `none_found`), and use the REAL GBP phone as the contact,
  never the parasite's tracking number. These are high-value no-website targets.
- **Multi-location brand: a host-matching website that serves a DIFFERENT branch
  is NOT this prospect's owned site (2026-06-10).** When the prospect's GBP shows
  *Add website* but a name-matching `.com` exists, open it and check the
  address/phone. If it lists a *different* branch (seen on
  `antojitosaminta.com`: only a San Mateo location w/ its own phone/email, while
  the prospect is the SF Mission 24th-St branch the site never mentions), the
  prospect itself has no owned site — override to the real verdict
  (`marketplace_only` if Yelp/marketplace exist, else `social_only`/`none_found`),
  put the prospect's own channel (its IG/Yelp) in `verdict_url`, and note "confirm
  same owner before outreach." Don't let the classifier drop it off the shared
  brand domain.
- **Custom branded Toast/Square ordering domain = `owned_site` (drop), even with
  GBP *Add website* (2026-06-10).** Restaurants often run a Toast/Square site on a
  custom domain (`<name>.com` + a sister `order<name>.com`) and never link it on
  GBP. If the main `<name>.com` shows their real menu/prices/address, it's a
  functional owned site → drop. Check the non-`order` domain — the `order`
  subdomain alone may 404 while the main site is live (seen on
  `aromasdemipueblo.com` live, `orderaromasdemipueblo.com` erroring).
- **Airport-concession kiosks / food counters inside a parent venue = drop
  (2026-06-10).** An airport-terminal coffee/food kiosk (Hartsfield, Newark, etc.)
  or a food "canteena" inside a bar is a concession or sub-brand of the parent,
  not an owner-operated local target. Set `verdict_override: "owned_site"` + note.
- **Roving pop-ups (no fixed storefront) = CAVEAT target, not clean (2026-06-10).**
  A real, popular chef-driven pop-up (big IG, press) with no storefront — its GBP
  address is just the host venue, which may now show a different business — and
  which already runs commerce via Hotplate/Square is `social_only` at best. Record
  it, flag the no-storefront + existing-platform caveat, leave to operator
  judgment.
- **Explicit "not the official website" footer = definitive parasite tell
  (2026-06-10).** Some parasite pages literally disclaim in the footer: *"This is
  not the official website. Content is from public information. If you are the
  owner, please contact us."* Seen with a `*.top` domain using auto per-location
  subdomains (`restaurant1.<name>.top`, `restaurant2.<name>.top`), copy mismatched
  to the cuisine ("The Real Deal on Asian Food" on a Mexican spot), repeated
  template testimonials, and a footer listing 100s of unrelated restaurants.
  Handle per the parasite-SEO ruling: NOT owned — override to the real directory
  verdict (`marketplace_only`/`none_found`), `verdict_url` = the Yelp/marketplace
  page, exclude the parasite email.
- **Overture "business" that is really a building/development name = drop
  (2026-06-10).** Some rows are a commercial-building or apartment-complex name
  miscast as an SMB (e.g. "Bakery Block" = a historic 83k-SF building housing a
  comic shop + consignment + offices → Maps returns the heritage-building entry,
  not a bakery; "Atlanta - 8 West" = the apartment complex a Costa Coffee kiosk
  sits in). Tell: Maps returns the building/heritage entry or unrelated tenants,
  and the only "social" is a sub-10-like auto location page. Data artifact, not a
  target — `verdict_override: "owned_site"` (firm drop) + a note that it's a
  building, not a business.
- **Same phone across multiple brand names = multi-brand/lead-gen flag
  (2026-06-10).** If your bare-GBP (no-review) target's phone also appears on a
  *different* business name that has real reviews (e.g. "AriasPhillips Cleaning"
  GBP shares 832-923-5474 with "AAM Painting" Yelp 3.7/63), it's one operator
  running multiple DBAs — your listing is a thin alternate of an already-presenced
  business, not a clean independent no-site lead. Flag
  `verdict_override: "ambiguous"` + note; don't promote.
- **Host-matching builder subdomain that serves a DIFFERENT branch is NOT this
  prospect's site (2026-06-10).** Same spirit as the multi-location `.com` ruling,
  but for builder hosts: a `<name>.blismo.com` (or square.site, etc.) that lists a
  *different* location's address/phone than the prospect's GBP is that other
  branch's page, not this one's. Keep the prospect as `social_only`/`marketplace_only`
  if its own GBP shows *Add website* (seen: Andy's Paws 5720 S Pulaski is no-site
  with IG @andyspaws, while `andyspaws.blismo.com` is the 6050 "store #3" branch).
- **Free site-builder page (Google Sites / GoDaddy Sites) linked on GBP = `owned_site`
  (drop), same as square.site/Wix/Weebly (2026-06-10).** Extends the builder-page
  rule to `sites.google.com` and `godaddysites.com`. When GBP links one as the
  website (seen: Arlington General Contractors → `sites.google.com`; Birrieria No Te
  Rajes Jalisco → `godaddysites.com`), a functional builder site exists → drop. The
  classifier treats these generic hosts as non-owned, so override to `owned_site`,
  put the builder URL in `verdict_url`. (These are thin DIY sites — a potential
  WaaS-*upgrade* lead, but per current rules they already "have a site," so drop.)
- **Out-of-scope foreign business = drop (2026-06-10).** Cross-border `city_id`s
  (e.g. `el_paso` → Ciudad Juárez MX, `detroit` → Windsor ON) and `country`/state =
  `None` rows can surface non-US listings (seen: "Barbacoa El Güero Pilo", Av. de los
  Insurgentes, Ciudad Juárez, Chihuahua, Mexico, 4.6/373). These are not US WaaS
  targets regardless of web presence. Set `verdict_override: "owned_site"` (firm drop
  so a high review count doesn't recompute it into A_gold) + a note "OUT OF SCOPE:
  <country>". Record `review_count` for accuracy.
- **Ordering/booking PORTAL ≠ a website — don't drop on it (2026-06-10).**
  Distinguish a full builder *homepage* (square.site/Wix/Weebly/Google/GoDaddy Sites
  with about/hours/menu → owned_site drop, per the builder rule) from a bare
  *ordering/booking portal* that is only a menu+cart or a request-a-quote form.
  Portal hosts that are NOT a site: `*.toast.site` and `order.toasttab.com`,
  `order.online`, `spotapps.co`, `getjobber.com` (Jobber client hub / quote portal),
  `app.<chain>.com`, `*.olo.com`. If a portal is the ONLY web home (GBP shows
  *Add website* and links only the portal), classify by the rest of the presence
  (usually `social_only`/`marketplace_only`) — it's still a no-real-site target.
  Seen: `banhmipholounge.toast.site` (Toast ordering only, business just rebranded
  from "Paris Banh Mi", active IG/FB → social_only target). CAUTION: this is the
  inverse of the custom-domain Toast/Square ruling above — a custom `<name>.com`
  Toast site with full menu IS owned; a bare `*.toast.site` subdomain is not.
- **Jobber split (2026-06-10):** `<name>.jobbersites.com` is Jobber's site-BUILDER
  product (real branded homepage: about/services/contact) → treat as a builder site
  = `owned_site` drop (borderline thin DIY site, but "has a site" per current rules).
  `getjobber.com` is the client-hub booking PORTAL → not a site (see portal ruling).
  A field-service biz whose GBP links only `getjobber.com` is still a no-site target.
- **"Best <Service> <Neighborhood>" keyword-stuffed multi-listing = SEO/service-area
  flag, hand-review (2026-06-10).** A GBP whose NAME is a search phrase ("Best Dog
  Groomers Hudson Kitchen") and which has sibling clones across other neighborhoods
  ("Best Dog Groomers Murray Hill", same brand, different addresses) is a service-area
  / GBP-keyword-spam pattern, not a clean owner-operated storefront. Corroborating
  tells: "Open 24 hours", an apartment-building address, "website" = `instagram.com`
  + a `bit.ly`, ≤2 reviews, and the only listings are aggregator directories
  (animalfriendspc, furvisor). Set `verdict_override: "ambiguous"` + note; don't promote.
- **Stale name / rebrand at the address — verify same-business before dropping
  (2026-06-10).** When the GBP at the prospect's exact address shows a DIFFERENT name,
  don't auto-drop as "closed/replaced": check whether it's the SAME open business
  under a new/dual brand vs. a true replacement. Tell of a rebrand (still a target):
  directory aggregators (Yelp/Nextdoor/Overlook) still list BOTH names at the same
  address with the same menu/phone (seen: "Blanc New York Bakery & Cafe" 7911
  Bergenline still on Yelp/Nextdoor while its Google GBP now reads "Birria house
  taqueria & Bakery", 4.3/180, no site → it's the same business, dual-branded →
  `marketplace_only` TARGET, not a drop). Only drop when a genuinely unrelated
  business occupies the address (different cuisine/owner, old name gone everywhere).
- **Dormant / "Temporarily closed" / dead-phone listing = drop, same as permanently
  closed (2026-06-10).** A GBP that is NOT flagged *Permanently closed* can still be
  effectively defunct — gate it out. Tells: GBP shows *Temporarily closed* AND every
  review is years old (seen: "American Pooch Grooming" OKC, Temporarily closed, all
  14 reviews 5–7 yrs old, unclaimed, no site); OR multiple recent reviews state the
  phone is disconnected / the business is unreachable (seen: "Affordable Roofing &
  Contracting" Philadelphia, 1.7★, 2024 reviews report the number disconnected). The
  goal is currently-OPEN, reachable businesses, so set `verdict_override: "owned_site"`
  (firm drop) + a note ("DORMANT/likely defunct: …" or "phone disconnected per reviews").
  Record `review_count`. A claimed/active GBP ("Updated by this business N weeks ago")
  or reviews within the last few months is the opposite signal — that's a live target.
- **No GBP at all (Maps returns a competitor list or a bare "partial match" address
  pin) + only scraper aggregators = `none_found` (2026-06-10).** When Maps shows no
  matching business — just a list of *other* nearby businesses, or a "Partial match"
  address with no reviews — and web search surfaces only auto-scraper aggregators
  (`hub.biz`, `nears.me`, `menutuff`, etc.) with no GBP/site/social/Yelp, treat it as
  `none_found` (empty `results`, no override). These are usually stale source rows or
  never-launched/defunct businesses with no reachable channel — low value. Don't
  invent a verdict; leave `results` empty so the classifier returns `none_found`.
- **Bare third-party menu-host subdomain (no custom domain) = portal, not a site
  (2026-06-10).** Add `*.menu11.com` (and similar `<name>.menu*` menu-display hosts)
  to the ordering-PORTAL list. A GBP that shows *Add website* and links only a
  `<name>.menu11.com` page is NOT an owned site — classify by the rest of the
  presence (`marketplace_only`/`social_only`), still a no-real-site target. Contrast
  the custom-domain Toast/Square ruling: a bare menu-host subdomain ≠ a custom
  `<name>.com` (seen: "Asiana Kitchen Tofu & Grill" food-court stall, 126 reviews,
  only `asianakitchen.menu11.com` → `marketplace_only` TARGET).
- **Government license revocation / city-ordered shutdown = drop, even if GBP shows
  *Open* (2026-06-10).** If local news reports the city/county revoked the business's
  operating/liquor/entertainment licenses (often tied to a police or federal case),
  it is effectively closed regardless of GBP status. Set `verdict_override:
  "owned_site"` (firm drop) + a note citing the source (seen: "Blaque Bar & Bites"
  West Allis WI — licenses revoked 9-0 by Common Council May 2026 per CBS58/JSOnline/
  Hoodline; GBP still showed "Closed · Opens 7 PM"). Record `review_count`.
- **A class/event/series hosted AT a venue is not a standalone business = drop
  (2026-06-10).** When the prospect name reads like a recurring class held at a venue
  ("Buti Yoga at Play Louisville") and the address resolves to the VENUE's own GBP
  (its own name + owned site), there is no separate business to sell to. Set
  `verdict_override: "owned_site"`, put the venue site in `verdict_url`, note it's an
  event at <venue>, not a standalone (seen: address → "Play Louisville" dance club,
  playdancebar.com, 456 reviews).
- **In-hotel restaurant (OpenTable-only, no owned site) = hand-review, lower fit
  (2026-06-10).** A named F&B outlet inside a branded hotel (e.g. "Brickstones
  Kitchen + Bar" in Embassy Suites) with the GBP "website" = OpenTable and no owned
  site is technically no-site, but the decision-maker is the hotel, not an
  independent owner. Set `verdict_override: "ambiguous"` + note the hotel context;
  don't promote as a primary target.

### Trial-run #1 yield note (2026-06-10, 3 × S_source_candidate)

First live sample was low-yield: 2/3 permanently closed (one with an owned domain,
one with a Square site + 5.5K IG), 1/3 a 1-review mobile baker → `none_found`. **0/3
were viable no-site targets.** Treat this as a signal that the Overture
`S_source_candidate` pool skews stale/closed; confirm over a larger (10–25)
calibration batch before committing 4 chats to it, and consider de-prioritizing
high-review S_source rows (they correlate with closed-but-popular restaurants).

### Calibration update (2026-06-10, chat #12, 50 × S_source_candidate, shard 11/20)

Larger sample is **much** higher yield than trial #1 implied: ~10 viable no-site
targets out of 50 (~20%) — a healthy mix of `social_only` (active IG/FB with no
owned site: e.g. Anko Sushi 7.6K IG, Aroma Bakery 4.4K, Bibi Pastry 44.9K) and
`marketplace_only` (Yelp/menu-host only). ~⅔ still drop (owned site/chain/closed),
and ~4–6% are genuinely closed/shut-down. Takeaway: the pool is worth working at
scale — the no-site needles are real and reachable. The single best target tell:
GBP shows *Add website* (or "website" = an instagram.com/social/portal link) **and**
the listing is live (recent reviews or "Updated by this business N weeks ago").
