# A_gold 196 — Demo Builds Tracker (RAISED BAR)

> **TL;DR.** Build the **196 DataForSEO A_gold** email-or-social no-website prospects
> (`state/prospects/batches/agold196-worklist.tsv`, round-robin by genre) as bespoke
> one-page demo sites — but at a **higher craft bar** than the social-300 batch. The
> elevation: keep every playbook integrity gate, AND add the **premium quality loop**
> (build → screenshot → Gemini-vision judge → revise → repeat until the visual gate
> passes; builder ≠ judge) plus stronger design distinctiveness. Batches of **25 with a
> PAUSE after each** (user monitors usage/progress). Separate from social-300 (0 overlap).
>
> **Progress: 196 of 196 built — ALL BATCHES COMPLETE (2026-06-21).** Rows 1-6 = the locked genre references; rows 7-196 = all built. **Batches 1-8 all DONE** (1: 7-31, 2: 32-56, 3: 57-81, 4: 82-106, 5: 107-131, 6: 132-156, 7: 157-181, 8: 182-196). Sequential 25-batch cadence (founder-chosen 2026-06-18), last build of each batch confirmed on localhost. All batches integrity-swept (0 iframes, 0 scaffold ghosts, 0 em-dashes after the title/meta rule tightening, healthy img counts). Gemini judge still PENDING on the 6 references (API 429/quota — re-run `design_loop.py judge --target <hub>` when quota resets).
>
> **REMAINING WORK (post-build):** (1) Founder calls on the operator flags below (rows 8, 109). (2) Deploy + promote pass to make builds outreach-ready (see NOTE). (3) Optional Gemini-judge pass on the 6 references when quota resets.
>
> **OPERATOR FLAGS (disqualify-or-proceed):** row 8 All Seasons Nail (sanitation/tip-pressure allegations) AND row 109 Yoni Beauty Salon (serious sanitation + chemical-burn allegations). Both built honestly around defensible strengths only, NOT auto-shipped, pending founder call.
>
> **NOTE — built != outreach-ready (2026-06-21).** All 190 builds (rows 7-196) are local-only `dist-v2/index.html` served on localhost; 0 are in the outreach lane ledger and 0 have a public `mockup_url`. They are NOT sendable until each is deployed to a public URL and that URL is wired back as `mockup_url` + the row promoted into the outreach lane. The dashboard's "Preview site" facet (`http://127.0.0.1:8765/dashboard/outreach?include=facet:preview-no-sends`) only matches the 32 already-published previews, none of which are agold196. Deploy/promote is a separate gated pass.

## Batch log

### Batch 1 — rows 7-31 (built 2026-06-18)
25 bespoke builds off the 6 locked references. Cadence: sequential batch of 25, last build shown on localhost. Notable:
- **Identity reconciliations (worklist slot != reality; built to place-details evidence):** row 12 Nail Envy = nail salon (slot said massage); row 20 B-Full = full-service salon + body massage; row 23 Goddess On The Rise = intuitive/tarot readings + handmade jewelry (slot said notary); row 26 Berg Healthy Feet = foot & nail studio, ZERO medical claims; row 29 Golding Royalties = a CLEANING company (slot said notary); row 30 Suvna = eyebrow-threading studio (slot said massage; also corrected city Minneapolis->Roseville MN); row 31 "Beauty-Salon" = Erika's Salon & Barber Shop (slot guessed barber; types show both).
- **Operator flag (disqualify-or-proceed):** row 8 All Seasons Nail & Spa (NYC) carries serious Google-review allegations (sanitation: one nail clipper reused back-to-back; tip-pressuring; one "corrupt"). Rating 3.0/53 was OMITTED; copy avoids every disputed claim. NOT auto-shipped pending founder call.
- **Photo-light / type-forward builds:** row 10 Bradley's (2 photos), row 17 Elyon (1, logo only), row 23 Goddess (3), row 24 Ruth's Zen (0 photos, fully type-forward), row 29 Golding (2).
- **Ratings handled honestly:** weak ratings omitted rather than shown (row 8 3.0, row 12 3.5); strong ones shown as-is.

### Batch 2 — rows 32-56 (built 2026-06-18/19)
25 bespoke builds. Tightened the em-dash rule to ban them everywhere incl. `<title>`/meta (result: 0 em-dashes across all 25, no post-cleanup needed). Notable:
- **Identity reconciliations (built to place-details evidence, not the worklist slot):** row 35 LA Primera = taxes + insurance + computers, NO notary (no evidence; correctly not invented); row 41 Rounsavall = a real-estate TITLE/closing company (not a generic notary), not-a-law-firm disclaimer; row 46 Translation Services = document translation + tax + notary, bilingual, not-a-law-firm disclaimer; row 49 Grace Braids = braiding studio; row 52 D'Matrixx = hair salon (slot said nail).
- **Location corrections (Google address beat the worklist city):** row 38 CB Hair&Nails -> La Mesa CA; row 39 Gilded -> Clovis CA; row 40 Frank's -> Camden NJ; row 47 Brandon Hill's -> Jeffersonville IN; row 54 (n/a); row 56 Dazzling Nail -> Haddon Township/Westmont NJ (FB handle dazzlingnailswestmont). Worklist TSV cities are approximate; trust place-details.
- **Co-located-business guard:** row 50 HB Tires shares its lot with a separate shop ("Near Me Car Care"); the build used only HB-attributable services + reviews, scrubbed the other brand.
- **Photo-light / type-forward:** row 35 (6), 36 (5), 41 ok, 46 (2), 47 (3); row 42 Benny's Corte De Pelo = 0 photos, fully type-forward (bilingual EN/ES).
- **Ratings shown honestly incl. weak ones:** row 34 Double Jays 3.4, row 48 Classic Nails 3.8, row 53 Hair Forte 3.9 all shown as-is with guardrailed copy (no superlatives, complaints turned into honest framing); row 34 also rejected an AI/stock crash photo.
- **Operational note:** big concurrent waves (12-13 agents) tripped the account session limit; switched to waves of ~6, which held. If resuming under a fresh limit, gather is idempotent on disk and only missing dist-v2 rows need rebuilding.

### Batch 3 — rows 57-81 (built 2026-06-19/21)
25 bespoke builds, waves of ~6. 0 em-dashes (one CSS-comment dash in row 60 stripped), 0 iframes, healthy img counts. Notable:
- **Identity built to evidence:** row 66 LLS Kustomz = custom auto + upholstery; row 67 Clipper1 = genuinely trilingual barber+beauty (EN/ES/Chinese); row 71 Conscious Heads = barbershop AND natural-hair salon (+ small bookstore), built to the dual identity.
- **Location corrections (place-details beat the worklist city):** row 73 Laura's -> Sunnyvale (not San Jose); row 75 Cuts Stop -> Malden MA (not Boston); row 76 Dreamy Nights -> St Paul (not Minneapolis); row 81 Permanent Beauty Spa -> Scottsdale (not Mesa); row 80 Fine Nail -> East Point/Atlanta.
- **Honest weak ratings shown as-is with guardrailed copy:** row 60 Diamond Nails 4.2, row 74 Peraltas 4.1, row 80 Fine Nail 4.0/805 (review-heavy but skews negative -> led on defensible assets, no speed/superlative claims).
- **Conflicting-brand / stale-signage guards:** row 79 Dapper Deluxe in-shop price sign carries a PRIOR brand ("Tip Top") -> no prices shown, that photo dropped; row 80 Fine Nail blurred a counter "cash only" sign that contradicts Google's cards-accepted data; row 58 Integrity A/C rejected a third-party HVAC van (different phone) in a photo.
- **Photo-light / type-forward:** row 57 (3), 61 (4), 69 (7 ok), 71 (3-on-page), 78 Rams #1 (4, type-forward, bilingual, "#1" shown as name only with NO superlative marketing claim).
- **PMU compliance:** row 81 Permanent Beauty Spa = cosmetic-only language, no medical claims, honest handling of a touch-up-dispute review.

### Batch 4 — rows 82-106 (built 2026-06-21)
25 bespoke builds, waves of 6 (held cleanly, no session-limit trips this time). 0 iframes, 0 em-dashes, 0 ghost vocab on the central sweep; `.claude/` stayed clean. Notable:
- **Identity reconciliations (built to place-details evidence, not the worklist slot):** row 89 El Sitio "Beauty Salon" = actually a BARBERSHOP (logo/chairs/fade reviews); row 101 Estetica Nuevo Estilo Jahyver's = Latino UNISEX salon (women's color + men's cuts), not a pure barber; row 106 VIS = genuine dual barber + beauty salon, built as one unified house (not a split page), bilingual service tags.
- **Location corrections (place-details beat the worklist city):** row 82 T.W Auto -> Jeffersonville IN (not Louisville); row 90 Icon Nails -> Tigard OR (not Portland); row 94 Sister Beauty -> Dearborn MI (not Detroit); row 97 Speak Natural -> East Point GA (not Atlanta); row 98 Erbil -> Alexandria VA (not DC); row 103 Ury Dominican -> Independence MO (not Kansas City); row 104 Fernandez -> Sunnyside/Queens NY; row 105 Kevin Nails -> Clovis CA (not Fresno).
- **Honest weak ratings handled:** row 82 T.W Auto 3.4 OMITTED (+ reputation-risk flag: loose-lug safety + warranty-dispute complaints); row 87 Happy Nails 3.7 omitted; row 89 El Sitio 3.9 omitted; row 101 Estetica 4.0 shown plainly with no-wait/guarantee claims avoided; row 96 Image Nails 4.3, row 99 Jolly 4.3/647, row 105 Kevin 4.3 all shown as-is with guardrailed copy.
- **Plate/PII + brand guards:** row 88 Sabs storefront plate baked-blurred (original to _orig/); row 89 rejected a plates-visible lot photo; row 100 Slayed House excluded lash-certificate photos with readable personal names (PII); row 105 Kevin Nails scrubbed prior brand "Nailology" (rebrand at same address/phone), no old name in copy.
- **Phone/identity flags for founder:** row 91 Salon Rue 52 (place-details vs storefront number differ); row 92 Elijah operates inside Hair Vice Barber Shop (personal brand, not shop owner); row 95 Empire Cutz door-number vs place-details differ; row 106 VIS signage shows a second phone. All built to the place-details number; worth confirming live number before send.
- **Bilingual EN/ES where evidenced:** rows 86 El Don, 89 El Sitio, 101 Estetica, 103 Ury, 104 Fernandez (light, not forced).
- **Photo-light / type-forward:** row 89 El Sitio (5 photos), row 85 Prism (4), row 88 Sabs (4), row 97 Speak Natural (5), row 98 Erbil (5), row 100 Slayed House (4).

### Batch 5 — rows 107-131 (built 2026-06-21)
25 bespoke builds, waves of 6 (held cleanly). 0 iframes, 0 em-dashes, 0 ghost vocab on the central sweep; `.claude/` reverted clean. Notable:
- **⛔ OPERATOR FLAG (disqualify-or-proceed):** row 109 Yoni Beauty Salon (Washington DC) has two 1-star reviews alleging serious sanitation problems AND chemical treatments that burned hair/scalp. Built honestly (leads on Yoni's curl/color craft + 7-day availability, makes NO cleanliness/safety/chemical-service claim), but should NOT be sent without founder review. Joins row 8.
- **Identity reconciliations (built to place-details, not the worklist slot):** row 110 Forever Chic "Hair Salon" (slot said barber) = full women-led hair/beauty salon; row 114 Hector The Barber = a solo barber cutting inside a custom-converted BUS near USC (built to the shop-on-wheels hook, Tue/Wed/Thu only); row 120 Invictus = dual Dominican barbershop + women's hair studio; row 126 jasmine = dual hair salon + barber shop (unified one-house build); row 128 Kings & Queens = all-ages/all-genders shop.
- **Location corrections (place-details beat the worklist city):** row 111 LA Nails -> St Paul (not Minneapolis); row 116 Ideal Style -> Clarksville IN (not Louisville); row 127 M2 Nail -> Alhambra (not LA); row 129 Madison Nails -> Madison/Nashville TN; row 131 Michelle Fifth Ave Nail -> Bay Ridge BROOKLYN (not Manhattan 5th Ave; the 5th-Ave identity is genuine Bay Ridge 5th Ave).
- **Honest weak ratings:** row 112 Headliners 4.2 OMITTED (polarized reviews); rows 113/117/119/121/123/124/125/126/129/131 in the 3.9-4.6 band shown plainly with guardrailed copy (no superlatives/speed/durability claims where a complaint exists). Row 131 3.9 shown once, plainly.
- **Plate/PII + brand guards:** row 107 Flip N Styles baked-blurred a WI plate AND a child's face; row 122 J Klips baked-blurred a MN plate; row 124 Jaacs cropped a child's face out (photo-light, 3 photos); row 126 jasmine baked-blurred 3 faces + a storefront decal phone; row 111 rejected a "BusinessRate Top 3" directory plaque; row 117 rejected an AI/graphic "CLOSED Memorial Day" flyer; row 118 Integrity SD rejected wrong-brand "Integrity Barber Club" photos that also carried a $25 price list; row 127 M2 rejected a readable-plate photo.
- **Phone/identity flags for founder (built to place-details number; confirm live before send):** rows 116, 120, 126 (second phone on signage); row 117 Leslie's Nails new-ownership note; row 124 Jaacs websiteUri is an X/Twitter handle (not a real site); row 130 Kutz has no publicly-confirmed phone/hours/booking.
- **Type-forward / photo-light:** row 130 Kutz Unlimited = fully TYPE-FORWARD (both source photos were car selfies, rejected; no fake imagery); row 124 Jaacs = 3 usable photos.

### Batch 6 — rows 132-156 (built 2026-06-21)
25 bespoke builds, waves of 6. 0 iframes, 0 ghost vocab; one em-dash slipped into row 149's `<title>`/og:title (stripped to middots centrally). `.claude/` reverted clean. Notable:
- **Identity reconciliations / dual houses (built unified, not split):** row 138 Lineage Studios = design-led barber shop in a converted bungalow (not booth-rental); row 143 Nails & Hair Expo = genuine nails+hair (nails led, hair kept general/no invented services); row 152 My "T" Sharp = dual barber+beauty (dual mural on the building); row 156 Official Barbershop & Salon = dual barber+salon, EST 2025/new mgmt, no staff roster published.
- **Location corrections (place-details beat the worklist city):** row 134 La Rotonda -> Dorchester/Boston; row 145 Nails by Anastasia -> Brooklyn (Midwood); row 147 Nails L'amour -> Milpitas (not San Jose); row 148 Mendez -> West Roxbury MA; row 150 Miguel's -> Highlandtown/Baltimore; row 151 Neo's -> Santa Clara (not San Jose); row 155 OMNI -> the listed FB handle is the old "5 Star Nails" brand (rebuilt to current OMNI name).
- **Honest weak ratings:** row 140 Major League 4.1, row 153 Nikki 4.4, plus 4.1-4.6 nail builds shown plainly with guardrailed copy. row 143 Nails & Hair Expo 3.6 OMITTED (serious ingrown-pedicure injury + dirty-tool allegations; built honestly around defensible strengths only — worth a founder glance before send, not auto-shipped).
- **Plate/PII + brand/competitor guards:** row 132 La Capital scrubbed a stale prior brand ("Henry's Barber Parlor") + cropped a TikTok watermark; row 134 cropped a child's face + rejected a readable-plate photo; row 139 Nail Station REJECTED 5 watermarked COMPETITOR photos (Coco Nails/Janea Nails reposts); row 141 Nail Talk baked-blurred a technician's business-card phone in 4 photos + stripped the "(10% off)" promo from the name; row 150 Miguel's rejected delivery-sticker + help-wanted-PII photos; row 153 Nikki rejected a receipt-PII photo.
- **Profile-flag override:** row 142 Manayunk dropped kids-cuts because a review explicitly contradicts Google's goodForChildren flag (on-the-ground review wins).
- **Phone/identity flags (built to place-details number; confirm live before send):** rows 136 LG's (multi-location pens), 138 Lineage (Linktree, not a real site), 142 Manayunk (booking exists but no URL), 144 Mellow Blendz (solo suite, Dominick/Dominik spelling), 155 OMNI (rebrand).
- **OPERATIONAL — weekly account limit hit:** wave 4 (rows 150-156) first attempt died with 0 tokens on the WEEKLY limit (resets 5pm America/Los_Angeles), no files written. Recovered after reset: single-agent probe (row 150) confirmed the window reopened, then dispatched the remaining 6. This is distinct from the per-window session limit seen in earlier batches.

### Batch 7 — rows 157-181 (built 2026-06-21)
25 bespoke builds, waves of 6. 0 iframes, 0 ghost vocab; one CSS-comment em-dash slipped into the row 181 showcase (stripped centrally). `.claude/` reverted clean. Notable:
- **Identity reconciliations / dual houses (built unified):** row 158 Oohs & Ahs = full-service barber-led Black hair shop (men + women, not barber-only); row 170 RD Barbershop Salon = dual barber+salon; row 177 Second Chance Hair Clinic = dual barber+salon, "Clinic" is name-only (NO medical claims).
- **Location corrections (place-details beat the worklist city):** row 158 Oohs & Ahs precise to Columbus East Side; row 163 Premier Nails -> Mercer Island WA; row 164 Polo's -> Scottsdale (not Mesa); row 169 Shiny Nails -> Bay Ridge Brooklyn; row 170 RD -> West New York NJ (not NYC); row 174 Richardson's -> Obetz OH (not Columbus); row 177 Second Chance -> Hyattsville MD (not DC).
- **Name correction:** row 177 worklist typo "Cliinic" -> "Second Chance Hair Clinic".
- **Weak ratings OMITTED + flagged (built honestly, not auto-shipped):** row 163 Premier Nails 3.3 (gel-peeling + tip-pressure complaints); plus 4.1-4.6 builds shown plainly with guardrails. row 172 Reds 007 4.7 SHOWN but flagged for founder (two recent 1-star reviews allege smoking inside near a child / price dispute) -- built around defensible strengths only.
- **Plate/PII guards:** row 158 baked 3 plates + a child's face; row 161 Polished Nails baked 2 TX plates + rejected a price-slip photo; rejected-photo guards on rows 167 (promo/watermark), 171 (artist watermarks + PII card), 173, 180 (faces).
- **No-phone / phone-conflict flags (confirm live before send):** row 162 Perfeksion (no phone on record; storefront number is the adjacent dentist's -> CTA Directions only); row 166 Power Barber (no phone; storefront number is adjacent dentist -> Directions only); row 171 TT Nails (card phone vs place-details conflict); row 176 Royal Shave (banner phone vs place-details); row 179 Straight Blade (painted window phone vs place-details); row 180 Style Design N Fades (older sign address/phone).
- **Heritage / differentiated angles:** row 168 Raymond's = 3rd-gen since 1978; row 174 Richardson's = est. 1935 country shop; row 178 Stay Gold = 5.0/93, NM Zia identity; row 180 Style Design N Fades = freehand hair-art (crowns/script shaved into fades).
- **Owner-published prices allowed:** row 176 Royal Shave showed a real owner-published service menu (prices were on the owner's own profile graphic, so permitted under the playbook).
- **Type-forward / photo-light:** row 177 Second Chance = fully TYPE-FORWARD (3 photos, all rejected: reflective storefront, hours sign, minor's face); row 164 Polo's (3 photos), row 176 Royal Shave (2 interiors + owner graphics).
- **Two same-named distinct businesses handled separately:** Omni Nail Spa appears as row 155 (Fort Worth) AND row 157 (San Jose) -- different place_ids, built to each one's own place-details.

### Batch 8 — rows 182-196 (built 2026-06-21) — FINAL BATCH
15 bespoke builds (the batch is 15 rows, not 25, since 196 is the last row), waves of 6/6/3. 0 iframes, 0 em-dashes, 0 ghost vocab on the central sweep; `.claude/` reverted clean. Mostly barbershops (the worklist tail is barber-heavy). Notable:
- **Identity reconciliations:** row 183 The A List ATL = grooming house that doubles as a curated fragrance boutique (third-party designer scents; added an "independent retailer, not affiliated" disclaimer, no brand claimed as a house product); row 185 The G.O.A.T = unisex hair studio AND barbershop; row 190 TZE = barbershop + SMP (scalp micropigmentation, built COSMETIC-only, explicit "not a medical treatment for hair loss" disclaimer, zero medical/cure language); row 194 Watson's = dual barber+beauty; row 196 Yessenia's = color-led HAIR SALON (worklist slot said barber) that also does men's/kids' barbering.
- **Location corrections (place-details beat the worklist city):** row 186 The Goat -> Dundalk MD (not Baltimore); row 187 Great Commission -> Brooklyn/Bed-Stuy (not "New York"); row 188 Thrones -> Richland Hills TX (not Fort Worth); row 191 V.I.P -> Medford MA (not Boston; full name "VIP Men's Hairstyling"); row 193 VIP Saysu -> Bayonne NJ (not NYC); row 196 Yessenia's -> Hyattsville MD (not DC).
- **Weak/honest ratings + reputation guardrails:** row 182 Texas Fadez 4.1 shown plainly (a no-show complaint -> led on walk-ins, no appointment-hold guarantee); row 184 Barbers Garage ignored a non-service DoorDash-tip troll 1-star; row 186/192 honored single negative reviews with no perfection/guarantee claims. No new disqualify-level flags this batch.
- **PII / wrong-business / price-leak guards:** row 182 cropped a child + a handwritten note; row 190 cropped a child's face + rejected an AI-render fake-barbershop photo; row 194 rejected a wrong-business seafood-house photo + excluded a price-board photo; row 195 rejected a "Best in Town"+QR+PII promo flyer; row 188 excluded a $25 promo + complimentary-alcohol framing; row 189 OMITTED a restroom claim (storefront "no public restroom" sign contradicts Google's restroom=true flag) + suppressed a walk-in price.
- **Phone-conflict flags (built to place-details number; confirm live before send):** row 183 (toll-free 888 number), row 190 (646 NYC area code on a Miami shop), row 191 (card hours vary).
- **Photo-light:** row 185 G.O.A.T (4 used), row 191 V.I.P (2 photos: storefront + interior).

---

## STATUS: BUILD PHASE COMPLETE (190/190 demo sites, rows 7-196)

All agold196 demo sites are built and integrity-swept. The three open threads are tracked in the TL;DR "REMAINING WORK" line: founder calls on rows 8 & 109, the gated deploy+promote pass to make sites outreach-ready, and an optional Gemini-judge pass on the references. Per-genre palette ledger entries from batches 4-8 are not all back-filled below (the ledger lists the original 6 references); the per-build palette names live in each site's `source/03-design-direction.md`.

## What "raise the bar" means here (elevations over social-300)

The base process is `docs/demo-site-build-playbook.md` (evidence-traced copy, no
invented content, real photos w/ plate/PII blur, per-business voice, mobile padding,
integrity gates). On top of that, for this batch:

1. **One Gemini-judge REFERENCE per genre (cost-controlled cadence — founder-chosen 2026-06-16).**
   Run the full build → screenshot → Gemini-vision judge → revise loop on the FIRST
   build of each genre only, until it clears the visual gate; that becomes the locked
   **genre reference**. Build the rest of that genre to the reference (same craft +
   integrity bar) WITHOUT per-build Gemini judging — just the human eyeball + integrity
   gates. Re-judge a genre only if its reference materially changes. (Judge: builder
   Claude ≠ judge Gemini. Judge currently 429-rate-limited; run when quota resets.)
2. **Design distinctiveness is a first-class gate.** No template reskin. Each build
   gets its own art direction (palette, type pairing, layout rhythm, hero treatment,
   motion/detail) appropriate to the specific business — and visibly distinct from its
   genre siblings (track palettes in the ledger below). Apply the
   `compound-engineering:frontend-design` principles (production-grade, non-generic,
   avoids AI-aesthetic defaults).
3. **Hero + photography treatment.** Lead with the strongest real photo, art-directed
   (crop/duotone/overlay as fits the brand), not a raw dump. Read EVERY source photo at
   full res first (montage thumbs mislead — wrong-business / AI-stock / plates).
   **LESSON (Abiel #1): do not bury the hero photo under a heavy full-cover dark overlay**
   — it reads as "broken/missing images." For a left-aligned headline use a HORIZONTAL
   gradient (dark ~.85 on the text side → ~.25 on the photo side) + a light bottom
   vignette, so the real photo is clearly visible. Prefer higher-res source crops for
   gallery tiles (low-res crops like 408px look soft).

## Per-build SOP

1. `python scripts/agency/gather_place.py --place-id <PID> --max-photos 10`.
2. Read every photo at full res individually; reject AI-stock, wrong-business, faces; blur plates/PII (`blur_plates.py`).
3. Write `source/content-brief.md` (each fact sourced; paraphrased reviews; lead-with strengths; honest guardrails) + `source/03-design-direction.md` (distinct palette named vs siblings; type; hero/photo plan; section flow; craft pass).
4. Dispatch a high-craft build subagent (inputs = the 2 source files + a craft reference + frontend-design principles) → self-contained `dist-v2/index.html`, Maps QUERY LINK (not iframe), no invented data.
5. **Premium loop:** screenshot (`screenshot_demo.py`) → Gemini judge → revise lowest dimensions → re-judge until the gate passes.
6. Integrity verify: `git checkout -- .claude/ && git clean -fdq .claude/`; ghost/scaffold-vocab grep; img counts; em-dash + price-leak scan; mobile-padding check.
7. Eyeball final screenshot; record here (bump count, advance row, 1-line done-entry).

Do NOT deploy. Edit only inside each prospect's own `dist-v2/`.

## Craft references
- Photo build: `state/prospects/sites/ChIJ38YgNSF91YcR0_bY0X_Mplg/dist-v2/index.html`
- Type-forward / photo-free: `state/prospects/sites/ChIJCW5S7-wMIocRioUBbJ25sx0/dist-v2/index.html`
- Playbook worked example: Skyline Nails — `state/prospects/sites/ChIJIYKyBuFzToYRpKQSc6Yf9ks/`

## Palette ledger (keep genre siblings distinct — grow forward)
- barber_shop: espresso-ink + warm-cream + honey-oak amber + barber-pole crimson, Barlow Condensed/Inter ("Warm Chair Classic" — Abiel #1)
- nail_salon: hunter-green + antique-gold + black, Fraunces serif/Inter ("Emerald Atelier" — A-list #2; palette sourced from a review naming "hunter green, gold, and black")
- nail_salon (sibling, distinct): oxblood/crimson + warm porcelain ivory + soft-gold, Playfair Display/Inter ("Crimson Howell" — Nail Talk row 141; palette sourced from the red "NAIL TALK" storefront lettering + recurring red/emerald work; promo "10% off" dropped from clean name; 4.7/269 shown as-is)
- beauty_salon: midnight-aubergine/plum + saffron-gold + coral, Bricolage Grotesque/Outfit ("Midnight Saffron" — Fama #3; 3.5★ shown honestly, complaints → "before you come in")
- auto_repair: graphite + signal-red industrial, Archivo/Inter ("Midnight Garage" — Auto Accessory King #4; lead-with 24/7)
- notary: greige paper + ink-navy + brass, Spectral/Inter, bilingual EN/ES ("Ledger Trust" — Confianza #5; not-an-attorney/notario disclaimer ×3)
- massage_therapy: dark indigo-slate + warm amber + sage, Newsreader/Inter ("Quiet Hour" — Alex's Mobile #6; mobile/service-area, no medical claims)
