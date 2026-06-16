# Handoff — BBW Batch B bespoke demo builds (2026-06-15)

> **TL;DR** — Build a genuinely-good, bespoke one-page demo website for each prospect in
> Batch B. **85 of 101 done** (9 "email" prospects + 76 "IG/FB"). **15 IG/FB** (+2 skipped/flagged: Grupo Francie, Rodelas)
> remain**, listed in `state/prospects/batches/IGFB-remaining-worklist.tsv` (work from row 78 down;
> rows 1–77 done (rows 64 + 69 SKIPPED/flagged)). **Chrome extension WORKS for Instagram (operator restarted it 2026-06-15);
> Facebook still wedges it (300s hangs) — avoid FB. IG PHOTO HARVEST is now solved (see box below).**
> Per prospect,
>
> **🆕 IG photo harvest (works — use it to personalize photo-thin builds):** standalone `navigate` to
> the IG profile → `javascript_tool`: scroll once + `fetch()` each grid `<img>`'s largest `srcset`
> URL in-page → base64 into `window.__H` (lean: no big scroll loop, ≤9 imgs, or CDP times out at 45s).
> Do NOT return the IG CDN URLs (the tool BLOCKS cookie/query-string data); keep them in-page. Then
> draw all base64 images stacked into ONE `<canvas>` (width 1080), `toDataURL('jpeg')`, and trigger a
> SINGLE `<a download>` (batch/multi downloads hit Chrome's "allow multiple downloads" block + flip the
> site to download-blocked — ONE combined file always auto-saves to ~/Downloads). Return the row
> y-offset manifest, then PIL-split the strip + montage + eyeball + stage. Yields clean ~1080–1440px
> photos. Esme (1→8 hair-result photos) + Basement Cutz (+3 action shots) were upgraded this way.
> Revelry had 0 IG posts (highlights only); Corporate Mind Body is FB-only (wedged) — neither upgradable.
>
> **Order beyond this worklist (operator-confirmed 2026-06-15):** the IGFB worklist is a slice of
> the ~381 social_only prospects without a bespoke demo. After it: finish the rest of the
> **social_only cohort-A** pool → then the **81 marketplace_only that have an IG/FB contact** →
> then the **341 listing-only marketplace_only** as photo-light builds. (Audit: 2,428 total
> prospects; social_only 440 = the "better" group, only ~13% bespoke-done; all 422 marketplace_only
> already have a basic ~9KB auto-mockup, only ~7% bespoke.)
> run the loop: **gather (Google API + web search + the business's own IG/FB/Square via the Chrome
> extension) → integrity check → write a sourced brief + design direction → dispatch a build
> subagent → verify gate → screenshot into the
> review gallery.** Each site must be visually DISTINCT, every claim must trace to evidence,
> no invented prices/hours, no stock/fake photos. Do NOT deploy (separate gated step). The
> reference quality bar is the Mrs. Jasmine build. Read this whole file before starting.

## Mission

Better Business Web (BBW) sells local businesses a bespoke website. Batch B = reachable,
unbuilt, unsent prospects that have a digital contact channel. We hand-build each a premium
one-page demo as the conversion artifact. This is Phase-0/1 work from
[the v2 plan](../plans/2026-06-11-bbw-v2-strategic-build-list-plan.md); broader context in
[the pipeline doc](../agency/prospect-to-client-pipeline.md) and the build procedure in
[the demo-site playbook](../demo-site-build-playbook.md).

## Current state (2026-06-15)

> **⚠️ 2026-06-15 session note — Chrome extension wedged.** The IG/FB/Square browser pulls hung
> (300s timeouts on FB, IG, even example.com) and stayed stuck the whole session, so builds 11–15
> used **Google API + WebSearch + WebFetch** only. WebFetch on a Booksy URL DID work (pulled a real
> service list for Esme) — try WebFetch for Square/Booksy/listing pages even while the extension is
> down. Restart the Chrome extension before the next session to get richer IG/FB photos + owner voice.

**Done (17):** all have `state/prospects/sites/<place_id>/dist-v2/index.html` + a screenshot
in `state/prospects/review-gallery/`. Each is deliberately a different look:
1. Tutoring With Mrs. Jasmine `ChIJ38YgNSF91YcR0_bY0X_Mplg` — teal/cream academic (hand-built reference)
2. ROASTED THREADS `ChIJEX2z0FvRmoARTUj-BIaLvUk` — warm-retro coffee/vinyl
3. Fellowship Barbershop `ChIJo9fwXw9Ra4gR5saFsK59XZo` — dark charcoal/brass barber
4. Pets and Bubbles `ChIJsd5NqFXXJIgR_6CDgbmVpms` — bright blue/cream bubbly
5. Black Coffee Nails `ChIJFVAe06dFeycR7byoUsbwtW0` — cream/espresso editorial
6. Boston's Groomer `ChIJLzHDMzd744kRwZ_DNrDaRRI` — forest-green/terracotta
7. Magic Tree (aerial) `ChIJNycGArkQsocRRDnBFQ5mBQA` — plum/teal dreamy
8. Take Action Tutoring `ChIJ9xskvW65xokRdr8wcnSyI7M` — bold red/gold energetic
9. The Nail Haven `ChIJG9qMIaFZ54YRk8Oydw4hDbE` — dark/rose-gold luxe
10. Jakes Fourthstreet Barber `ChIJCW5S7-wMIocRioUBbJ25sx0` — Southwest turquoise, **photo-free** (no usable photos)
11. Marlene's Cleaning Service `ChIJo0eelenzwIcR4czk6tqrbzc` (KC) — airy sage-green/cream house-cleaning editorial (first house_cleaning)
12. Mobile mechanic BroniXpress `ChIJi4smQjy32YgR47wzDGp-2Gg` (Miami) — dark asphalt + electric-cyan industrial (first auto_repair; 24/7 mobile)
13. House of Beauty by Esme `ChIJu2VnhU9x1oYRuobyTkxbkhQ` (Tucson) — warm desert blush/chestnut/clay/gold serif (first hair salon). **v2 (2026-06-15): UPGRADED photo-rich — harvested 8 balayage/color result photos from IG; now a real hair gallery instead of one-photo.**
14. Revelry A Studio Salon `ChIJrwPIgLsMIocRR7LS5CQmbns` (ABQ) — monochrome bone/ink + oxblood-wine modern studio (salon sibling; architectural photos)
15. The Soapy Coyote `ChIJy4iVJCYLIocRFlTyNryDX2g` (ABQ) — vibrant orange + cactus-teal Southwest playful (self-service pet wash; walk-in framing)
16. Prince Benji Dog Grooming `ChIJ6S2nPAADyIkRuej-8ExmoC4` (Baltimore/Canton) — regal royal-navy + warm-gold + cream, crown motif (full-service groomer; cage-free, since 2017)
17. Cherry Blossom Cafe `ChIJd9_ZXx9elIAR4t9uVDY0eo0` (Fresno) — fresh sakura pink/green/cream/bark-brown, food-first (courthouse cafe; Chef Martha's burritos, rotating specials)
18. Kotka Y Chucho `ChIJa3JOSaJZXIYRip2Lj9VX_bQ` (San Antonio) — warm folk-Czech cream/poppy-red/cornflower-blue, slab serif (one-man scratch kolache bakery; late-night weekend lockup)
19. Bermudez Landscaping `ChIJP_MNowQtDogRvFw8hmwTeqY` (Chicago) — rugged charcoal-slate + evergreen + wheat-gold, slab (landscaper/hardscape/snow; NO star badge, 3.9 rating intentionally not shown)
20. La Reyna Bakery `ChIJU4uZJn1Z54YRQUcnB_X433M` (El Paso) — festive rosa-mexicano + marigold + pan-dulce-brown, papel-picado/concha/crown (Mexican panadería; bakery sibling to Kotka, totally different)
21. The Beauty Lounge Salon `ChIJ--RGBJ1plIAR0inOPe3G_eg` (Fresno) — emerald-velvet glam lounge + brushed gold + blush, Cormorant serif (3rd beauty_salon; jewel-tone, distinct from Esme/Revelry + earthy greens)
22. Corporate Mind Body Wellness `ChIJIf0nbCgtO4gRunYZlIhdrn4` (Detroit) — calm warm-sand + petrol-teal, photo-free type-forward, ripple/breath motifs (1st massage/wellness; in the RenCen; 1 location photo only)
23. UNCUT Barber Studio `ChIJPW4ypK5Z54YRzPckJSEc_o4` (El Paso) — matte-black + bold-red + white, hexagon geometry, Anton condensed (3rd barber; modern/urban, studio photos, distinct from Fellowship/Jakes)
24. Hi-Tech Roofing `ChIJB2I0VfdnlIARszxd187NpqI` (Fresno) — clean light + steel-navy + safety-amber, roofline/chevron (1st roofer; since 1992, pro-trusted; lighter than the dark trades builds)
25. Precise Taxes & Credit Repair `ChIJh_IlEkQ7OaQRYnF3Iusm2Xg` (Jacksonville) — money-green + gold precision-finance, photo-free, seal/ledger motifs (1st tax/financial; tax-led, NO credit-outcome guarantees — regulated)
26. Yamazaki Bakery `ChIJr5nk2vXHwoARLCLhwNkTTTA` (Los Angeles) — minimal Japanese paper-and-ink + vermilion + matcha, Shippori Mincho, enso motif (3rd bakery; calm/minimal opposite of Kotka + La Reyna)
27. Luv-It Landscaping `ChIJGX1eOTcNaYgRlA1Hp2zgvTY` (Louisville) — warm cream + classic garden-green + honey-gold, Fraunces, leaf/heart motif (2nd landscaper; light/heritage/family + civic feature; NO star badge, 4.1 modest; baked before/after labels handled honestly)
28. Dynasty Beauty Salon `ChIJaRAPxiqJOIgR3trNWeCuclI` (Columbus) — regal aubergine/royal-purple + radiant gold + rose, crown/sunburst, Fraunces (4th beauty_salon; Black-owned, welcoming/natural-hair angle; distinct from Esme/Revelry/Beauty Lounge + Magic Tree)
29. The Doghouse Spaw `ChIJ8RxuDc0tO4gRT_JjjuvdrDc` (Windsor ON, geo'd under Detroit) — soft cozy muted-lavender + sage + cream, paw/bandana motif (5th dog-care; gentle pampering spa; Canadian spelling; distinct from all 4 prior pet builds)
30. Blendz Barbershop & Studio `ChIJmZ7Hj1NZ54YRzgOaWSEhF_g` (El Paso) — fresh modern charcoal + neon-blend gradient (cyan→violet→magenta), Sora (4th barber; the "Blendz" gradient hook; distinct from Fellowship/Jakes/UNCUT)
31. Servicios Internacionales Mtz `ChIJBxXXFR1Z54YR7nh0jY1UBmo` (El Paso) — warm bilingual Spanish-first trust-blue + gold + terracotta, photo-free, seal/passport motifs (2nd notary/services; tax+immigration-docs+notary+marriage; notario-fraud/CROA disclaimers; distinct from Precise Taxes)
32. Chef Wing Villarias (Private Chef) `ChIJq5o0NgBZlIARSXKyByX1FAs` (Fresno) — elegant warm-dark espresso + gold + calamansi fine-dining Filipino, Cormorant (1st chef/fine-dining; private dining + delivery; accurate Bib-Gourmand pedigree, NOT a walk-in restaurant)
33. Barberventures (Mobile Barbershop) `ChIJO4t_Hxu_QIYRVQffx6kKiFU` (Houston) — clean cream + midnight-navy + warm-coral, route/map/pin motif, Space Grotesk (5th barber; MOBILE comes-to-you; accessibility story; distinct from the 4 dark barbers)
34. Main Street Grooming & Company `ChIJ_7rc29q35YgRocc_X8QkQmw` (Jacksonville) — forest-green + navy + cream heritage barbershop (their real logo colors), Saira, barber-pole motif (6th barber; FIRST green barber; distinct from all 5 barbers + non-barber greens)
35. Sunset & Sign Notary `ChIJCxUeuh7HwoARIAKCFAP9jug` (Los Angeles) — photo-free LA-sunset (dusk-navy + sun-gold→coral→pink gradient, setting-sun/horizon/signature motif), Sora (3rd notary; MOBILE same-day; notary-not-attorney disclaimers; distinct from Precise + Servicios)
36. Ru.Nails `ChIJQfRZrrIiTiMRduQlc_RKuNM` (Miami/Brickell) — clean precise-elegant greige + deep-berry + champagne Russian-manicure studio, Cormorant (nail_salon; distinct from Black Coffee espresso + Nail Haven rose-gold)
37. Just Ask Lauri! `ChIJK6yjhVsd9YgRD4f6zlNDe98` (Atlanta) — confident personal-brand charcoal + magenta-pink + gold, headshot-led, Fraunces (4th notary; mobile notary + signing agent + business consulting; notary-not-attorney, no reliability superlatives; distinct from the 3 prior notaries)
38. Yesteryear Plumbing LLC `ChIJrQ0gtXM00AQRnd2ethG41mk` (Baltimore) — vintage/heritage aged-cream + vintage-teal + copper, badge/pipe motif, Fraunces (1st plumber; owner-operated craftsman; warmest of the trades builds, distinct from Bermudez/Hi-Tech/BroniXpress)
39. Basement Cutz `ChIJ_0elWo-POIgRYzZDvF_r2XI` (Columbus) — warm industrial-loft concrete + cream + FRESH-green accent + brick, Archivo (7th barber; welcoming/inclusive lead; distinct from all 6 barbers incl. Main Street's forest-green). **v2 (2026-06-15): added 3 real IG action shots (barber cutting, client in chair, cut at the mural) — feels alive now.**
40. Brilliant Minds Tutoring Academy `ChIJF4mO5CUtO4gRgXGqIhdCW8k` (Windsor ON, geo'd under Detroit) — bright indigo + amber lightbulb theme, photo-free, Fraunces (tutoring; distinct from Jasmine teal + Take Action red/gold). NOTE: had a 1-star refund-dispute flag — **operator APPROVED the preview 2026-06-15** (cleared to proceed).
41. Detroit Dog Salon `ChIJMzXGPIjPJIgRAYIbbWkAzxw` (Detroit) — chic charcoal + cream + coral creative dog SALON + multi-color color-pop motif, Fraunces (6th dog-care; woman-owned, creative-color/dye styling; distinct from all 5 prior pet builds)
42. MD Barber Company (Mills) `ChIJsarTamNZ54YR8E6puGTXtu4` (El Paso) — warm premium master-craftsman photo-free (espresso + cream + camel + oxblood, MD-monogram crest), Cormorant (8th barber; appointment-only; distinct from all 7 barbers incl. Jakes' turquoise photo-free)
43. Milagros Wellness + Massage `ChIJO3c2YkxZ54YRrXjOBb4yULI` (El Paso) — warm botanical-healing cream + terracotta + sage + gold-hamsa, Fraunces, photo-rich (2nd massage; tranquil plant-filled studio, fascia/cupping; distinct from Corporate Mind Body's cool clinical look)
44. Meraz Roofing Inc `ChIJ9UXxwnpmlIARx0TBazdWnmk` (Fresno) — bold charcoal-slate + red + concrete, credential-forward (Licensed/GAF/Bonded/224-projects), Saira Condensed (2nd roofer; NO star badge — 4.4 + service complaints; distinct from Hi-Tech's light navy/amber)

45. Hairy Business Barbershop/Salon/Day Spa `ChIJoQ5bj5N-1YcRtlYOuxpUenE` (Memphis) — quirky charcoal + bold PINK ("the pink door") + cream + terracotta, Bricolage (9th barber-genre, +salon+spa for everyone; 1-photo hidden-gem; pink unused by any prior barber)

46. Bloom Beauty Co. `ChIJqdaW1Llv1oYRWDhtaQtB2c8` (Tucson) — funky industrial-botanical raw forest-green + brick + cream + leaf, Sora (5th beauty_salon; real green-wall/brick/plant space; distinct from glam/serif siblings)

47. Baltimore Legend's Barbershop & Salon `ChIJ7xuUzJ8FyIkRdoDoRNOBYcM` (Baltimore) — bold black + red + GOLD "legend" laurel/star marquee, Bebas (10th barber-genre +salon/locs; Black-owned; NO star/wait/spotless claims — 4.3 + ops complaints; distinct from UNCUT's hexagon-modern)

48. Birdy's Bagels `ChIJ1yJu8dJxToYR4vFMjr89AY8` (Fort Worth) — cheerful sky-blue + cream + golden-bagel "happy morning" bird/bagel brand, Fredoka (4th bakery; weekend-only pop-up→residency; distinct from folk/festive/sakura/minimal bakeries)

49. Bella Musicana `ChIJ2brltXi35YgRXLLcDxzZquw` (Jacksonville) — elegant romantic wedding-strings ivory + wine + dusty-rose + gold, Cormorant (genre was mislabeled music_lessons → it's a live STRING ENSEMBLE for weddings/events; Viktoriya/Violin Vita; first of its kind)

50. FADE LV Barbershop/Mobile `ChIJXa7eTZ7DyIARAhpggATsZL0` (Las Vegas) — Vegas-neon black + gold + magenta marquee, Anton (11th barber, 2nd MOBILE; comes-to-your-hotel; distinct from Barberventures route-map + all dark barbers)

51. Chef's Table Bakery and Cafe `ChIJa0meLNGnK4cRUcOa2Ew8ns8` (Mesa) — warm chef breakfast-cafe cinnamon + cream + kitchen-green + golden-yolk, Fraunces (5th bakery; from-scratch brunch + gigantic cinnamon rolls; distinct from the other 4 bakeries)

52. H&Son's Plumbing `ChIJBdtWhYARsocRoyRMS9O60HQ` (Oklahoma City) — classic family-trades red + navy + cream + steel, crossed-wrenches badge, Archivo, bilingual (2nd plumber; father-son Hector + son, permits/honest-upfront; distinct from Yesteryear's vintage one-man)

53. Yoga with Sunny `ChIJ-TUnDwAzjoARzM5OoO29Nl8` (San Jose) — warm "sunny" yoga golden-sun + cream + sage + terracotta, Fraunces, sun/lotus motif (1st non-aerial yoga; Sunny/Thao all-levels, daily-changing; distinct from Magic Tree's cool plum/teal aerial)
54. Planet Paws Pet Salon & Spa `ChIJP9Dc7y6L20cRfFh7nqHAcsg` (Tucson) — cosmic-spa space-indigo + cosmic-teal + star-gold + cream, planet/orbit/star/paw motif, Fredoka, groomer Lexi, MoeGo (7th dog-care; dogs AND cats + first-timer-friendly; distinct from bubbly-blue/earthy/orange/navy-gold/lavender-spa/charcoal-coral siblings via cosmic theme)
55. Juanita's Bakery `ChIJDY8oACwLIocRdQL5deSn4u4` (Albuquerque) — calm homey neighborhood-family panadería: talavera cobalt-blue + masa-cream + soft dusty concha-pink + caramel, talavera-tile + concha-sunburst motif, Fraunces, bilingual-warm (6th/Mexican bakery; fresh conchas + famous tres leches + affordable; deliberately BLUE-anchored & calm vs La Reyna's saturated festive rosa-mexicano)
56. Unbound Café `ChIJzRMaXQBZ54YR8yRCq2x58Ug` (El Paso) — bold modern plant-based coffee: vivid matcha-green + teal (from their real graffiti logo) + near-black charcoal + razz-magenta pop on cream, Space Grotesk, charcoal/cream rhythm, real Square ordering CTA (3rd coffee_shop; dairy-free-by-default + best-matcha-in-EP + from-scratch syrups; distinct from ROASTED THREADS retro-brown + Cherry Blossom soft-sakura)
57. Genaration Sports Therapies `ChIJ56vj0Y5zToYRS7BSfDwxMVA` (Fort Worth) — grounded-athletic TYPE-FORWARD sports/therapeutic massage: deep pine-green + trophy-bronze + cream + slate, ROM-arc/mobility-ball/cupping-dot SVG system, Fraunces, therapist Genavieve Boyles (licensed since 2010), MassageBook CTA (3rd massage; credible sports-recovery clinician vs the 2 soft-spa siblings). NOTE: most Google photos unusable (CBD retail + certificates); used only 2 real photos (Kinesio-taping + assessment); NO medical claims, NO CBD.
58. Chicas With Glow Beauty `ChIJRWDunizNj4ARNHsjEjLHS7A` (San Jose) — luminous lash/brow/skin esthetician studio: orchid/lilac + champagne-gold + cream with a signature radial-GLOW device + sparkle/swirl motifs, Cormorant, esthetician Nelly, GlossGenius CTA, light bilingual (6th beauty_salon, 1st esthetician studio; distinct from all 4 hair-salon siblings blush/mono/emerald/pine). Verified all photos individually (excluded bridal/glam/stock); open-eye lash shot flagged for blur.
59. L.I.M.E. Full Spectrum Auto Care `ChIJoQ08qYS5t4kRJMSp_0Uyf5M` (Washington DC) — bold dark-automotive MOBILE mechanic: asphalt-charcoal + on-name LIME acid-green + steel, Archivo, location-pin/route/wrench motifs + subtle 'full spectrum' gradient sweep, owner Deandre 'Dre', call/text CTA (1ST auto_repair build; we-come-to-you service-area card NOT a walk-in mapcard; no prices/affiliations/shop). Photos verified individually.
60. Momentary Retreat Massage `ChIJmVgnJgRxToYRToDE585-A3s` (Fort Worth) — elegant calm SANCTUARY massage in their real brand: soft dusty-rose/blush + sage-green + cream + candle-glow, leaf/botanical motif, Marcellus/Cormorant, therapist Donna, MassageBook + gift cards (4th massage; customized-every-session sanctuary, distinct from teal-Corporate/terracotta-Milagros/pine-Genaration). Used the serene room photo; excluded 2 headshots to avoid misattributing Donna; no medical claims.
61. George's Auto Care & Smog `ChIJ6fDncKJflIARGUyTkcwxxIc` (Fresno) — heritage automotive PHOTO-FREE/type-forward: deep navy + signal-red + steel + cream, hand-built EST. 1981 circular emblem (gear+crossed-wrenches), Oswald, George Guzelian + Salvador, smog+full repair, call/visit CTA (2nd auto build; classic fixed decades-old family shop, distinct from L.I.M.E.'s asphalt+lime mobile). Est-1981 BBB-verified; no guaranteed-pass claim.
62. AP Barber Studio `ChIJ3Qd_VgATK4cRl-ewyGsEFWM` (Phoenix) — premium two-man (Ary+Pedro) downtown studio in their REAL brand: deep navy-black + GOLD + SILVER dual-metal + warm walnut + bone, ornate AP barber-pole/crossed-razor crest (EST. 2024), Heard Building, Vagaro+walk-ins (~12th barber; honored real navy/gold-silver crest, differentiated from dark siblings via navy+dual-metal+walnut+ornate-crest + chill-modern story).
63. Sweet Rascals Dog Grooming `ChIJ-6oow2w1joARz9CG6Xk1YsU` (San Jose) — sweet playful grooming in their real red brand: cherry-red + cream + honey/peach + soft sweet-pink, heart/paw/star motifs, Baloo 2, crew Bella+Gloria, salonxpress booking, leads with the text-you-photos-mid-groom trust feature (8th dog-care; RED-anchored playful-sweet, distinct from blue/green/orange/navy-gold/lavender/charcoal-coral/cosmic-teal siblings).
64. Pawfit Paws `ChIJk90gXgAdyIkR45uJlewxww0` (Baltimore) — friendly-premium dog grooming: rich plum/grape + cream + butter-gold + sage, paw/perfect-fit-check/heart motifs, Quicksand, solo groomer Liz (9th dog-care; distinct plum lane vs blue/green/orange/navy-gold/lavender/coral/teal/red siblings). INTEGRITY: one 1-star COMMS complaint → built honest (show 4.8 not perfect-5, NO communication/response claims, NO businessrate '#1' award); led with the great-with-big-and-anxious-dogs strength.
65. Doug's Auto & Towing Repair `ChIJXzPwubZx44kRybq06OoOpZs` (East Boston) — industrial hi-vis: safety-ORANGE + charcoal-black + steel + diagonal HAZARD-STRIPE device + tow-hook/wrench motifs, Saira Condensed, owner Douglas, real tow-truck photo, call CTA (3rd auto build; distinct from L.I.M.E. asphalt/lime sleek-mobile + George's navy/red heritage). Cropped a license plate; no 24/7/website/price claims.
66. Arteta Multiservices `ChIJUf2X4HWQOIgRq9K03DWtmyw` (Columbus) — warm bilingual community multiservicios, PHOTO-LIGHT/type-forward: warm community-RED (their sign) + cream + friendly TEAL + gold, storefront/seal/envelope/check service-icon SVGs, Hanken Grotesk, bilingual (se habla español) (5th notary/services; RED+teal led, distinct from blue-gold Servicios Mtz/green Precise/navy Sunset/charcoal Lauri). REGULATED: notary=document-notarization-ONLY + 'not attorneys, no legal/immigration/tax advice' disclaimer; show 4.6 (1-star receipt/fee complaint → no transparency claims), no bare 'notario'.
67. Salon On the Park `ChIJn-cB0iotO4gRwRzya7djNm0` (Detroit) — refined modern-architectural hair salon, PHOTO-FREE/type-forward: bronze/copper + greige + charcoal + cream, nested-arch/park-leaf/clock SVG hero, Cormorant, Lafayette Park (Mies modernist) nod (7th beauty_salon; bronze/architectural lane vs blush-gold/mono-oxblood/emerald/pine/orchid siblings). INTEGRITY: 4.5 w/ one rudeness 1-star → show 4.5 (no perfect-5), led with professionalism+runs-on-time (NOT warmth), no invented hours/prices/services.
68. Reyna's Mercadito `ChIJH1BzHQBZ54YRLR8f0FCBUHE` (El Paso) — cozy charming café+mercadito in their REAL hand-drawn brand: soft sage-green + warm kraft-tan + cream + strawberry-red pop + black line-art, postage-stamp + cute fruit-doodle motifs (strawberry/pear/chili/citrus), Fraunces, strawberry matcha + fresh food + Too Good To Go rescue bags (4th coffee_shop, 2nd El Paso matcha spot; deliberately soft/hand-drawn/kraft-cozy to diverge HARD from sibling Unbound's bold charcoal street-matcha).
69. Pawfect Pooches Pet Grooming `ChIJmfqQSfNnlIAR_wz2me1creM` (Fresno) — fresh clean-cute groomer: MINT/seafoam + soft blush-pink (their pink salon) + white + charcoal + gold, paw/sparkle/shield motifs, Quicksand, groomers Tatiana+Stephanie, groomer.io booking (10th dog-care; MINT-led, distinct from all 9 siblings + same-name Pawfit's plum). INTEGRITY: 4.7 w/ one scheduling/customer-service 1-star → show 4.7 (no perfect-5), led with safety-+-comfort-first + meticulous (NOT time/scheduling claims).
70. Matthew's Barber Shop `ChIJp8quV_MKFEARFV0MzbjB7_A` (Mesa) — LATE-NIGHT identity (their real superpower: open till midnight + glowing neon-OPEN storefront): deep midnight navy-black + warm AMBER incandescent glow + cream + small neon-red OPEN accent, crescent-moon/clock-at-12/barber-pole motifs, Oswald, barbers Matt/Art/Ray/Michael, Fresha (~13th barber; warm-amber-glow + open-till-12 hook is the distinct lane vs all the cool-neon/metallic-crest dark barbers). 4.7 shown; no 24hr claim.
71. KRoss Plumbing `ChIJXz0Fw_tx44kR7thzdfPHL6w` (Boston) — clean modern plumber in their real brand: teal/cyan + deep navy + white + warm COPPER accent, water-drop (their logo) + pipe/wrench/checkmark motifs, Archivo, owner Kevin Ross, leads with clear-upfront-pricing/no-surprises (well-supported) (3rd plumber; teal/navy/copper clean-modern, distinct from H&Son's red/navy classic-trades + Yesteryear vintage). 5.0 shown; no 24/7/emergency/gas/sewer claims.
72. El Paso Notary Public `ChIJHeP_CqRd54YRQZKrwfsPxlE` (El Paso) — ⚠️FLAGGED LOW-RATING (3.9/14 w/ MULTIPLE serious complaints: rude, 'didn't do their job right', too high prices). Built STRICTLY CLAIM-LIGHT/FACTUAL: NO rating, NO testimonials, NO praise/quality/price claims — only the sign-evidenced services (Notary + Income Tax + Bookkeeping & Payroll + Insurance, bilingual). Established-professional burgundy/maroon + cream + gold, type-forward seal/calculator/ledger/shield icons, Source Serif, bilingual + 'not attorneys/no legal-immigration advice' disclaimer (6th notary; distinct burgundy/gold vs green/blue-gold/navy/charcoal-plum/red-teal siblings). OPERATOR: confirm before pitching (poor service reviews).
73. Gomez Automotive `ChIJtb9dKAZZ54YRM_tRESmmNZI` (El Paso) — classic-car El Paso one-man shop: deep teal-petrol blue + warm CHROME/silver + cream + sunset-AMBER, chrome-lowrider-silhouette + wrench + 24/7 + route-pin motifs, Oswald, owner Tony Gomez, mobile + 24-hr emergency + bilingual (4th auto build; teal/chrome/amber classic-car lane vs L.I.M.E. lime / George's navy-red / Doug's safety-orange). INTEGRITY: 4.6 w/ one serious overcharge/refund 1-star → show 4.6, honesty via concrete anecdotes, NO refund/guarantee/price claims.
74. Jennspuretherapy `ChIJcxoMyx9zToYRlZ_OW_9Ho0o` (Fort Worth) — premium deep-tissue/therapeutic massage in their REAL brand: deep violet/plum + magenta glow + champagne-GOLD + cream, lotus/hands/gold-seal motifs, Cormorant, Jennifer Ramirez LMT, Square booking + in-home option (5th massage; premium-violet luxe lane, distinct from teal-Corporate/terracotta-Milagros/pine-Genaration/blush-Momentary). 4.9 shown; NO medical/cure claims (relief=client experience), CBD add-on listed neutrally, no prices.
75. Puppy Yoga Indianapolis `ChIJ1VozYKtRa4gRL-0nqdEhXps` (Indianapolis) — joyful yoga-with-puppies: soft PINK (their real pink mats) + fresh sage/mint + cream + sunny pop, paw/lotus/heart/puppy motifs, Baloo 2, beginner-friendly + snuggle-puppies + great-for-groups, weekend sessions, online booking (3rd yoga / 2nd non-aerial; bright playful pink+mint vs Magic Tree aerial-plum + Sunny golden-sage). 5.0/28 (highest review count in batch); no adoptable/style/price claims; local arm of multi-city brand → kept LOCAL to Indy.
76. Park Avenue Salon `ChIJj35szS4XsocR2kbdfGF2H30` (Oklahoma City) — classic metropolitan full-service downtown salon in their real brand: deep navy/midnight + CHROME/silver + warm wood-brown + cream, hexagon-and-downtown-SKYLINE logo motif + scissors/comb/barber-pole, Cormorant, stylists Holly+Teri, 30yrs, hair+nails+waxing+shoe-shine (8th beauty_salon; navy+chrome+wood+skyline-hexagon, distinct from Salon On the Park's bronze/greige + emerald/oxblood/blush/orchid/pine). 4.7 shown; led with hair+nails, waxing listed w/o brow overclaim; no prices.
77. Lita's Grooming Studio `ChIJYbZ9RwBR54YRID1Hu8p0lqo` (El Paso) — VETERAN-OWNED caring dog grooming: grounded slate/steel-blue + warm cream + soft dusty-rose (nod to their pink brand) + muted-red star, paw/heart/star/bow/shield motifs, Fraunces, owner Lita + crew (11th dog-care; deliberately did NOT lead pink — 2 siblings already pink — led the unique veteran-owned + true-heart-for-dogs/senior-rescue-care angle in slate/cream/rose, distinct from all 10 siblings). 5.0/13; accurate Closed-Thu+Fri hours; veteran nod tasteful.
78. Steven's Auto Service `ChIJ_Y-R-GNCQ0wRBmbt4JY-9A4` (Houston) — bold performance-precision MOBILE mechanic: deep crimson/racing-RED + graphite/charcoal + steel-silver + white, diagnostic-gauge/checkmark/gear/route-pin/thermometer motifs, Saira Condensed, mechanic Armando (5th auto build, 3rd mobile; LED with the thorough/does-it-right/'no band-aids' quality angle in crimson/graphite, distinct from L.I.M.E. lime-mobile / George's navy-red / Doug's orange-towing / Gomez teal-chrome). 5.0/13; mobile service-area card (not walk-in); no 24/7/price claims.
79. The Barber Studio Fletcher Place `ChIJ0cdcpZhRa4gRTTJRrp6LxXo` (Indianapolis) — refined LUXE-LOUNGE barber in their real interior: black/charcoal + GOLD (brass/champagne chairs+chandelier) + refined crimson accent + tan-leather + cream/marble, barber-pole-in-frame logo + chandelier/star/parking-P motifs, Cormorant, barber Angel, free-downtown-parking perk, Setmore (~14th barber; gold-forward refined luxe vs UNCUT industrial black/red-hexagon + FADE LV neon-magenta + all dark siblings). 5.0/13; best-in-Indy attributed; no prices.
80. Speedy Notary Services `ChIJ-yJge4Uzs1IRkk-1Cx5zzpQ` (Minneapolis) — fast energetic mobile notary, PHOTO-FREE/type-forward: bright electric AZURE + charcoal + white + warm AMBER speed-accent, notary-seal-in-motion + speed-arrow/clock motifs, Space Grotesk, notary Will Viscarra, day-or-night + apostille/loan-signing, bilingual (7th notary; bright-azure SPEED theme, distinct from green/blue-gold/navy/charcoal-plum/red-teal/burgundy siblings). 5.0/13; notary=notarization-only + disclaimer, apostille=process-help-not-legal-advice, no prices.
81. Aura Nail Spa `ChIJbxvMGtbHxokRhD7FqA2FXv0` (Philadelphia) — elegant botanical nail studio in their REAL brand: deep sage/forest-green + GOLD + cream + taupe, delicate botanical hand-+-florals line-art (their logo), Fraunces/Cormorant, nail artist Roula/Rula, Square booking (4th nail_salon; sage-green+gold elegant-botanical, distinct from Black Coffee espresso + Nail Haven dark/rose-gold + Ru.Nails). 4.8/15; leads with long-lasting-gel; no prices, no invented services (no pedi/acrylic).
82. Catalina's Bakery (Panadería y Pastelería) `ChIJ94p9v0INK4cRacTcZNB1j_I` (Phoenix) — warm café-panadería: rich coffee/café-de-olla BROWN + terracotta-clay + cream + soft concha-PINK, concha/churro/café-de-olla-cup-with-steam motifs, Fraunces, family-run, bilingual (7th bakery / 3rd Mexican panadería; CAFÉ angle [café de olla] is the unique hook, warm coffee-brown distinct from La Reyna festive-rosa + Juanita's cobalt-blue). 4.8/13; no prices/invented menu.
83. CEO Auto Mechanic `ChIJs2u4UWgTK4cRFiNvMW366OU` (Phoenix) — sleek executive-racing auto shop in their real brand: black/charcoal + GOLD (gear logo) + chrome + checkered-flag, gold-gear/crown/checkered-flag/checkmark motifs, Saira/Archivo, Est. MMXVI (2016), team Noe+Mariah, Setmore (6th auto build; black+gold executive-racing, distinct from lime/navy-red/orange/teal-chrome/crimson-graphite siblings). 4.7/13; LED transparent-quote/no-overselling + chill-no-nonsense + free-towing-with-repairs; deliberately did NOT feature their used-car/easy-credit line; no prices.
84. Genesis School of Music `ChIJA7V6ySPMJIgRB_KhxhotjBg` (Detroit) — soulful music school, PHOTO-FREE/type-forward: warm charcoal/ink + brass-GOLD + cream + deep soulful PLUM, treble-clef + music-notes + piano-keys hero composition, Fraunces, teacher Mr. Joel, piano/guitar/voice for all ages, Black-owned Detroit-Avenue-of-Fashion pride (1st real music_lessons build; no sibling). INTEGRITY: 4.8/12 w/ one missed-call-back 3-star → show 4.8 (no perfect-5), NO response-speed claims; no prices/invented-instruments.
85. Amigo Notary `ChIJ72Hsqh9Z54YRRpDzZmssASE` (El Paso) — warm friendly bilingual multiservices (notary+taxes+translations+apostille+forms+weddings/bodas), PHOTO-LIGHT/type-forward: sunset-ORANGE/terracotta + marigold-YELLOW + cream + warm charcoal, sun + seal/calculator/translation/rings/form service-icons, Bitter, bilingual (8th notary; sunset-orange+marigold friendly, distinct from green/blue-gold/navy/charcoal-plum/red-teal/burgundy/azure siblings). NORMAL notary (no scam, NOT skipped like Grupo/Rodelas); 4.7/12 w/ one phone-rudeness 1-star → show 4.7 (no perfect-5), no warmth-overclaim; notary=notarization-only+disclaimer, no bare 'notario', no prices.
— ⛔ **SKIPPED row 69: Rodelas Immigration Consultant** `ChIJc3YQCMZZ54YRHMrVua8y1hc` (El Paso, notary) — NOT BUILT on integrity grounds (same pattern as Grupo Francie): 3.5/13 with MULTIPLE explicit scam/theft allegations ('took my money, LOST my documents, refuses to refund after 8 months', 'charge to fill out residency forms then don't send them — scammers!', 'never open, will happily take your money', 'horrible rude service') AND it's an IMMIGRATION CONSULTANT doing residency/apostille paperwork for a vulnerable community (notario-fraud high-risk). Consolidated chip task_15f4a49d filed for operator covering BOTH flagged immigration-paperwork prospects (Grupo Francie + Rodelas) + suggested an immigration-consultant exclusion rule. ✅ OPERATOR CONFIRMED 2026-06-15: dropped from outreach — persisted to the fail-closed suppression registry (source=disqualified; place_id + phone + FB handle keyed).
— ⛔ **SKIPPED row 64: Grupo Francie INC** `ChIJlSw_gQNZ54YR6a6M8wIBU-w` (El Paso, notary) — NOT BUILT on integrity grounds: 3.6/14 with MULTIPLE scam allegations ('a scam... thieves just take your money', 'they raised the price... don't tell you the truth, completely unreliable', no-show consult) AND operates in immigration/passport paperwork for a vulnerable community (notario-fraud high-risk zone). Declined to build a promotional site that could funnel vulnerable people to a possibly-fraudulent immigration service. Filed spawn_task chip (task_850e43ba) for operator to confirm dropping from outreach. ✅ OPERATOR CONFIRMED 2026-06-15: dropped from outreach — persisted to the fail-closed suppression registry (source=disqualified; place_id + phone + FB handle keyed).

**Remaining (48):** `state/prospects/batches/IGFB-remaining-worklist.tsv`
(cols: place_id, city, genre, name). Rows 1–43 are done (builds 11–53 above); **start at row 44**
(Planet Paws Pet Salon & Spa, Tucson dog_groomer) and work top to bottom.

## The per-prospect loop (do this for each remaining place_id)

### 1. Gather Google data + photos (one at a time — see gotcha below)
```bash
python3 scripts/agency/gather_place.py --place-id <PID> --max-photos 10
```
Writes `state/prospects/sites/<PID>/source/place-details.json` (+ photos). Then read the
facts/reviews/hours and build a photo contact-sheet montage to eyeball the photos (PIL;
see any prior build's montage snippet). Note: `userRatingCount`, `weekdayDescriptions`,
the 5 review texts, `nationalPhoneNumber`, `websiteUri` (often a booking link).

### 1b. ALWAYS pull the business's own IG / FB / Square via the Chrome extension
The operator is around to approve consent prompts — so try the browser for **every** business
(richer photos + the owner's voice + service menus beat Google alone). Grep the place_id in
`state/prospects/audited/*.csv` for `contact_instagram` / `contact_facebook` / `contact_booking_url`
/ `web_verify_url`, then for each: `list_connected_browsers` + `select_browser` once per session,
**standalone** `navigate` to the URL (this clears the per-domain consent — wait for the operator to
click Allow if prompted), then **standalone** `get_page_text` (and a standalone screenshot if you
need the visual). Pace it (one business per page load, ~3–4s waits). Pull: service menu + prices
(Square/booking), owner name + voice + photos (IG/FB). If a call hangs (can happen), recover by
navigating to a known-good domain, tell the operator, and fall back to Google + web for that one
rather than blocking. NEVER enter credentials or solve a captcha. See the browser gotchas below.

### 2. Web search — integrity + context (mandatory)
Use the `WebSearch` tool: `"<name>" <city> reviews complaints`. This is the **mandatory
integrity check** (catch scam/fraud/serious-complaint signals Google hides). If you see
real scam/fraud/"took my money"/fake-review/threatened-customer signals → STOP, flag it for
the operator, do not build. Otherwise it also surfaces owner names, concept, services. Pull
contact channels from `state/prospects/audited/*.csv` (grep the place_id) for IG/FB/Square URLs.

### 3. Write the brief + design direction (you, not a subagent)
- `state/prospects/sites/<PID>/source/content-brief.md` — verified facts (each with source),
  what's-true-about-the-work (each tied to a review/photo), paraphrased testimonials (NEVER
  verbatim, NO real names attached), lead-with angle + voice, guardrails (what NOT to claim),
  real CTAs. Copy the structure from a prior build's brief (e.g. Fellowship's).
- `state/prospects/sites/<PID>/source/03-design-direction.md` — palette (from their own
  signage/logo/photos), type, the staged photo filenames + what each shows, section flow.
  **Explicitly state how it must differ from prior builds** so the subagent doesn't converge.
- Stage + web-optimize the chosen photos into `dist-v2/assets/` with semantic names (PIL,
  cap width ~1100–1600, quality ~84). Blur license plates / readable PII if present.

### 4. Dispatch a build subagent (general-purpose)
Use the **build-subagent prompt template** below. The subagent reads the brief + design +
craft-pass + voice + the Jasmine reference and writes `dist-v2/index.html`, self-verifying.

### 5. Verify gate (you) + screenshot
```bash
F=state/prospects/sites/<PID>/dist-v2/index.html
grep -niE "northwind|fast by default|\{\{|lorem| prospect|TODO" "$F" | grep -viE "preconnect|prefers" || echo ghosts-clean
# em-dash + price scan on BODY copy (strip <head> and <script>):
python3 - <<'PY'
import re; h=open("$F").read(); b=h.split("</head>",1)[1]
t=re.sub(r"<script.*?</script>","",b,flags=re.S); t=re.sub(r"<[^>]+>"," ",t); t=re.sub(r"\s+"," ",t)
print("body em-dashes:", t.count("—"), "| $prices:", re.findall(r"[$]\d", t) or "none")
PY
git status --short .claude/    # MUST be empty — see boundary below
python3 scripts/agency/screenshot_demo.py --place-id <PID> --label v1
```
Then `Read` the newest PNG in `state/prospects/review-gallery/` and eyeball it (hero quality,
distinct look, no broken images, location card rendered). Fix or re-dispatch if needed.

## Build-subagent prompt template (copy, fill <PID> + specifics)

> Build ONE bespoke demo website (Better Business Web agency). Bar: premium, hand-built, NOT a template.
> **Read first:** (1) `state/prospects/sites/<PID>/source/content-brief.md` — every line of copy
> traces to it, invent nothing; (2) `state/prospects/sites/<PID>/source/03-design-direction.md`;
> (3) `state/prospects/sites/ChIJ38YgNSF91YcR0_bY0X_Mplg/dist-v2/index.html` — REFERENCE for
> craft-pass techniques + structure (match QUALITY only, its teal look is NOT yours);
> (4) `state/prospects/sites/_scaffold/05-craft-pass.md`; (5) `docs/products/better-business-web/gtm/voice.md`.
> Your build MUST look different from all prior pipeline builds (list the relevant ones).
> **Write** `state/prospects/sites/<PID>/dist-v2/index.html` — self-contained HTML + inlined CSS,
> Google Fonts CDN OK. Use the real staged photos in `dist-v2/assets/` (object-fit:cover). Real
> CTAs only (booking/tel/IG/FB/email + a styled branded `.mapcard` linking to a Google Maps query
> — NEVER a live `<iframe>`, it renders blank in screenshots). Accurate hours. NO invented prices.
> **Craft pass:** distinctive display+body type, palette from their cues, ~3% SVG grain,
> gradient-mesh glow, multi-layer elevation, 1px gradient borders, glass sticky header, bento
> gallery, scroll reveals via `animation-timeline: view()` gated behind `prefers-reduced-motion`
> with visible fallback, count-up on the rating, trust marquee WITH edge-fade gradients, big
> gradient footer wordmark, inline-SVG favicon + OG meta, tabular-lining numerals.
> **Hard rules:** every claim traces to the brief; no banned AI-tell words (voice.md);
> **em-dash budget ≤2 in visible body copy**; no template ghosts (`Northwind`/`Fast by default`/
> `{{`/`prospect`/`preview`/`TODO`/`lorem` = ZERO); responsive — `.wrap` uses `padding-inline`,
> never zero horizontal padding via a `padding` shorthand (use `padding-block`), no horizontal
> overflow at 390px. **Do NOT edit any file outside `state/prospects/sites/<PID>/`** (especially
> not `.claude/` or any launch/config). Do NOT deploy or screenshot. Final message: short report
> (design + how it differs, verify results, judgment calls).

If a prospect has **no usable photos** (happens — open-data businesses are thin), build
**photo-free / type-forward**: tell the subagent "PHOTO-FREE, no stock/fake imagery, carry it
with bold typography + color + CSS/SVG motifs + big stat lockups" (see the Jakes build,
`ChIJCW5S7-wMIocRioUBbJ25sx0`, for a premium photo-free example). Verify `grep -c "<img"` is 0.

## Gotchas / learnings (read these — they cost real time to discover)

- **Google API rate-limits on burst.** Gathering 6+ in a tight loop → HTTP 400 tracebacks.
  Gather **one place_id at a time** (naturally paced by the build work between). A failed
  gather usually succeeds on a lone retry. Some place_ids are stale/closed — skip if a real
  400 persists.
- **Chrome extension (FB/IG/Square) is UNRELIABLE.** Patterns found: a *standalone* `navigate`
  clears the per-domain consent gate; a `navigate` *inside* `browser_batch` re-triggers the
  prompt and fails. Standalone `get_page_text` is the reliable read; batched `computer:screenshot`
  re-triggers permission. New domains/subdomains (instagram.com, square.site, my.canva.site) need
  the user to click **Allow** in Chrome (they set "On All Sites" already, but the MCP has its own
  consent), and they must be **logged into IG/FB**. Worst case: calls hang **300s** then time out,
  and can leave the extension stuck. **Operator directive: ALWAYS try the browser for every
  business** — they will be around to approve consent prompts, and IG/FB/Square give richer photos,
  the owner's voice, and real service menus. Use the reliable patterns (standalone navigate +
  standalone get_page_text). Only fall back to Google + WebSearch for a given business if the
  browser genuinely hangs/stalls on it after a recovery attempt — don't let one stuck call block
  the whole run; recover (navigate to a known-good domain), note it, and move on.
- **Photo availability is the swing factor.** Email-batch prospects had ~10 good Google photos
  each; open-data IG/FB prospects are hit-or-miss (Jakes had 1 unrelated photo → photo-free).
  Always eyeball the montage; discard irrelevant/blank photos; go photo-free when thin.
- **Subagents sometimes overreach.** One added an entry to `.claude/launch.json` (operator-owned,
  forbidden) to run a preview server. The template now forbids editing outside the site folder;
  still `git status --short .claude/` after each build and `git checkout -- .claude/...` if touched.
- **Screenshot filenames** are slugified and can differ from your guess (e.g. `the-nail-haven-el_paso.png`,
  `magic-tree-yoga-studio-oklahoma_city.png`). After screenshotting, `ls -t review-gallery/*.png | head -1`.
- **Faces / PII.** Many real photos show faces (kids, clients, aerialists). Operator approved using
  them **as-is for the private preview**, but every brief must carry a "confirm/blur faces before
  the sent/published version" flag. Favor non-face shots where the brand allows. Always blur
  readable license plates into the file (not CSS).
- **Distinctness is a real requirement.** Two nail salons, two tutoring cos, two groomers exist —
  each pair looks nothing like the other. In the design direction, name the sibling build and say
  "must differ." Reuse the reference's *techniques* (mapcard, marquee, count-up), never its look.

## Hard boundaries (do not cross)

- **Never deploy.** Building stops at local `dist-v2/` + a review-gallery screenshot. Deploy/send
  is a separate, operator-gated step (`build_prospect_site.py --deploy`/`--named-site --approve`).
- **Never invent** facts, prices, hours, services, or testimonials. If a section can't be filled
  with sourced content, cut it. Reviews are paraphrased, never verbatim, no real names attached.
- **Only edit inside `state/prospects/sites/<PID>/`.** Do not touch `.claude/`, `packages/policies/`,
  `packages/schemas/`, `skills/`, or any config. `state/` is runtime — fine to write builds there.
- **Mandatory integrity check** per prospect before building; escalate scam/fraud flags, don't build.
- Honor `docs/products/better-business-web/gtm/voice.md` (banned words) and the demo-site playbook
  hard rules.

## Useful references
- Reference build (study the code): `state/prospects/sites/ChIJ38YgNSF91YcR0_bY0X_Mplg/dist-v2/index.html`
- Craft pass: `state/prospects/sites/_scaffold/05-craft-pass.md`
- Voice/banned words: `docs/products/better-business-web/gtm/voice.md`
- Playbook: `docs/demo-site-build-playbook.md` · Gather protocol: `docs/demo-site-gather-automation.md`
- Worklist (91 remaining): `state/prospects/batches/IGFB-remaining-worklist.tsv`
- Preview a build live: `python3 scripts/agency/preview_site.py --place-id <PID> --port 8013`

## Cadence note
Each build is ~12–18 tool calls (gather, browser pull of IG/FB/Square, web search, montage,
brief, design, stage photos, subagent, verify, screenshot, eyeball). ~4–7 fit comfortably in
one session before context gets heavy. Work top-to-bottom through the worklist; drop each into the review gallery so the
operator can spot-check. It's a long road at one-by-one pace — that's expected.
