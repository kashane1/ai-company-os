# Genre art-direction kits

Per-genre **design recipes** — the durable, compounding asset behind the web lane.
Not a photo warehouse (stock dates fast and never matches the next brand): the thing
worth keeping is the *recipe* that produces on-brief work, plus a few exemplar images
as proof. Loaded + written by [`packages/web/art_direction.py`](../../art_direction.py);
consumed by the mood-board generator and `niche_to_spec` (the build first-draft).

## Layout

```
kits/<slug>/
  kit.yaml        # the recipe (art_direction.KitRecipe)
  manifest.json   # exemplar provenance — a real ImageryManifest (packages/web/imagery.py)
  exemplars/*.webp  # 3–5 exemplar images (no-crop, downscaled)
  reference.webp    # optional art-direction reference image
```

A kit may be **recipe-only** (empty `manifest.json`, no `exemplars/`). Exemplars are
**harvested from real builds** (`art_direction.py harvest`), never fabricated
speculatively — the library grows from demand.

## `kit.yaml` fields

| Field | Meaning |
|---|---|
| `slug` | kit id (its own namespace — **not** required to be a `GENRE_PALETTES` key) |
| `display_name` | human label |
| `niche_aliases` | substring keys that resolve a free-text niche to this kit (mirrors `packages/web/niches.py` needles) |
| `concept_statement` | the one idea the build serves |
| `palette` | `genre:<key>` (into `GENRE_PALETTES`) **or** an explicit `#rrggbb` brand/concept-palette seed |
| `accent` | explicit accent hex — **the key control**: it stops the engine's default contrasting complement, so warm-monochrome refs (cream + sage, cream + terracotta) render right |
| `type_vibe` | a vibe from [`font_pairings.md`](../font_pairings.md) (drives the mood-board fonts) |
| `concept_type` | free-text type steer passed through as the engine's `concept_type` spec field |
| `imagery_direction` | composition + style steer for the hero + supporting shots (feeds `style_spec`/`build_image_briefs`) |
| `composition_rules` | human-readable layout/shot rules |
| `image_prompts` | per-role ChatGPT prompts: `hero` / `bento[]` / `band` — the durable generation asset. Generate + ingest in `ingest_sequence` order: hero, bento…, **band LAST** (the composer reserves the last image for the full-bleed band) |
| `references` | `DesignReference` rows (title/url/source_type/takeaways) — translate, never copy |
| `evidence_hints` | placeholder proof points a real build replaces with the business's own |
| `harvested_from` | build hubs this kit was harvested from (provenance trail) |
| `version` | bumped on each harvest |

## Provenance honesty (binding)

Exemplars carry their original `ImageAsset.provenance` + `production_clearance`
verbatim. Harvest **never** relabels `generated`→`owner` to dodge the clearance gate,
and **never** pulls a prospect's own (`owner`) photos into a shared kit without an
explicit rights ack. `clearance_blockers()` runs on a kit's manifest unchanged.

## Slug ↔ palette

Slugs are decoupled from the 20 curated genres. `med_spa` is **not** a first-class
genre — its kit sets `palette: genre:massage_therapy` to reuse that palette. Promote a
slug to a real genre (its own `GENRE_PALETTES` row) only when the niche earns it.
