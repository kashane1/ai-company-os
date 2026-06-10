# Art-direction kits + the mood-board generator

**TL;DR.** A **kit** is the durable per-genre *design recipe* — palette, type vibe,
imagery direction, composition rules, references, and 3–5 exemplar images. It's the
compounding asset behind the web lane: not a photo warehouse (stock dates fast and never
matches the next brand), but the recipe that produces on-brief work. One kit powers three
things — (1) an instant **build first-draft** (`niche_to_spec`/`art_direction scaffold`),
(2) a one-page **mood board** that's both a build brief and a *sales artifact*
(`moodboard build`), and (3) a **harvest** loop that grows the library from real builds
(`art_direction harvest`). Kits reuse the existing imagery-provenance contract, so
nothing here can launder the clearance gate.

- Core: [`packages/web/art_direction.py`](../../packages/web/art_direction.py) ·
  [`packages/web/moodboard.py`](../../packages/web/moodboard.py)
- CLIs: [`scripts/agency/art_direction.py`](../../scripts/agency/art_direction.py) ·
  [`scripts/agency/moodboard.py`](../../scripts/agency/moodboard.py)
- Storage + format: [`packages/web/design_reference/kits/README.md`](../../packages/web/design_reference/kits/README.md)

## Where kits live

`packages/web/design_reference/kits/<slug>/` — alongside the other shared design
intelligence (`palettes.md`, `font_pairings.md`). Per kit: `kit.yaml` (the recipe),
`manifest.json` (exemplar provenance — a real `ImageryManifest`), `exemplars/*.webp`
(3–5, optional), `reference.webp` (optional). A kit may be **recipe-only** — exemplars
arrive via harvest, never fabricated speculatively.

Kit slugs are their **own namespace**, decoupled from the 20 `GENRE_PALETTES` keys: a
kit names its palette explicitly (`genre:massage_therapy` or a `#hex`). That's how
`med_spa` reuses the massage palette without being a first-class genre.

## 1 · Build first-draft (`scaffold` / `niche_to_spec`)

A kit is the image-backed successor to the hardcoded catalog in
[`packages/web/niches.py`](../../packages/web/niches.py). `niche_to_spec(niche)` now
overlays a matching kit's recipe (concept, palette, accent, imagery direction,
references, evidence) onto the base spec — so a new build starts on-brief, then you
customize to the real business. The plug point is unchanged: the spec still flows through
`request_from_spec` and `make premium NICHE="…"`.

```bash
python scripts/agency/art_direction.py list                  # kits + freshness
python scripts/agency/art_direction.py show --slug med_spa   # the recipe (incl. image prompts)
python scripts/agency/art_direction.py scaffold --slug med_spa \
    --site-name "Lumina Aesthetics" --audience "…" --goal "book consultations" \
  | python scripts/agency/design_studio.py packet --target <hub> --spec -
```

The business's own visual cues still win — the kit is the starting draft, not an
override (see the demo-site build playbook §4).

### Generate the imagery from the kit (ChatGPT → ingest)

Imagery is generated in-browser (ChatGPT, **Instant** model — not Thinking; self-contained
text, no live URLs, which would trigger a web-search loop) and bridged in with
[`ingest_images.py`](../../scripts/web/ingest_images.py). `prompts` prints the per-role
prompts in the exact generate/ingest order — **hero, bento…, band LAST** (the composer
reserves the last supporting image for the full-bleed band):

```bash
python scripts/agency/art_direction.py prompts --slug fish_tacos
# generate each in ChatGPT → ~/Downloads (turn OFF Chrome's "ask where to save"), then:
python scripts/web/ingest_images.py --target <hub> \
    --hero ~/Downloads/hero.png --supporting <bento…> <band LAST>
# build (reuses the manifest, no Gemini): build_premium_site(packet, <hub>/site)
# deterministic gate (no Gemini): python scripts/agency/design_loop.py composition --target <hub>
```

The kit's **explicit `accent`** is the key control: it stops the engine's default
contrasting complement, so a warm-monochrome reference (cream + sage, cream + terracotta)
renders right (`packages/web/design_system.py` `_color_roles`).

## 2 · Mood board (`moodboard build`) — the sales artifact

Assembles palette + type + 6–9 on-brief images into one self-contained page. Two jobs at
once: the internal build brief, and a client-facing artifact you can send to sell the
vision **before** building. Images are layered **business-first** — a real build's shots
take priority, kit exemplars fill the grid; a recipe-only kit still renders (palette +
type + direction).

```bash
python scripts/agency/moodboard.py build --slug med_spa \
    --business-name "Lumina Aesthetics" --out <dir> --shoot
python scripts/agency/preview_site.py --dir <dir>          # iterate locally
# --deploy publishes a private Netlify draft and writes moodboard_url onto the record
```

`moodboard_url` rides alongside `mockup_url` in `OutreachContext` (no schema change), so
outreach copy can link the board.

## 3 · Harvest (`harvest`) — grow the library from real work

Every good build feeds the kit: promote the winning prompt + selected images back into
the genre's kit. The library grows from demand and stays current.

```bash
python scripts/agency/art_direction.py harvest --slug coffee_shop \
    --from state/prospects/sites/<place_id> --note "Café Ollama build"
```

## Provenance honesty (binding)

Harvest is a provenance-**preserving** copy — each exemplar keeps its original
`provenance` + `production_clearance` verbatim. The gates:

- **Uncleared `generated`** exemplars are refused unless `--allow-uncleared`, and even
  then stay `production_clearance=False`, so `clearance_blockers()` / the deploy guard
  still catch them downstream. A kit never launders clearance.
- **`owner`** exemplars are refused unless `--allow-owner` — a business's own photos are
  not ours to reuse on another client through a shared kit (explicit rights ack only).

Default-harvest only `generated`/`licensed` (cleared). This keeps the founder rule honest:
generated imagery may ship, but always as a logged, conscious choice.

## Seeded kits (both validated; live on better-business-web.netlify.app)

- **`med_spa`** — sage wellness (reference: sage-sound.com). Palette seed `#869178` +
  explicit accent `#6F7D58`; refined-serif type; 3 owner-cleared exemplars; hero + band
  image prompts. Live: `/work/med-spa/`.
- **`fish_tacos`** — sun-warmed coastal taqueria (reference: cafegratitude.com). Palette
  seed `#C8553D` + explicit accent `#C2502F`; high-contrast serif; 5 owner-cleared
  exemplars; hero + 3 bento + band prompts (band ingested last). Live: `/work/fish-tacos/`.

> "Café Gratitude" is the design **reference** for the fish-taco kit, not a coffee shop.

## Tests

`tests/python/unit/test_web_art_direction.py` (recipe round-trip, palette resolution,
spec overlay, harvest provenance gates) and `tests/python/unit/test_web_moodboard.py`
(self-contained render, business-first image merge, token guard). Pure cores, no API key.
