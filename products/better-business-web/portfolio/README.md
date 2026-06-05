# Better Business Web — portfolio demos

Anonymized demo sites shown as proof-of-work on the BBW landing page. Each is a
real prospect mockup (built via the bespoke playbook, path B) with identifying
details swapped for a fictional business.

> Part of the WaaS agency lane — see [docs/agency/README.md](../../../docs/agency/README.md).

## Files

- **`curated.json`** — the input registry. One entry per genre mapping a real
  `place_id` → the anonymized `portfolio_name` / address / phone / area used on
  the public demo. Edit this to choose which business represents each genre.
- **`manifest.json`** — generated output. Per-demo: `name`, `source_business`,
  `dist` path, public `url` (`/work/<slug>/`), and `thumbnail`. Written by the
  build script; don't hand-edit.
- **`<genre>/dist/`** — the built, anonymized static site per genre
  (`auto_repair/`, `bakery/`, `barber_shop/`, …).

## How it's built

`scripts/agency/build_portfolio_demos.py`:
1. reads `curated.json`,
2. copies each business's `state/prospects/sites/<place_id>/dist-v2/`,
3. **anonymizes** the HTML (real name → `portfolio_name`, etc.),
4. publishes to `products/better-business-web/site/public/work/<slug>/`,
5. writes `manifest.json` + WebP thumbnails (`site/public/portfolio/<slug>.webp`)
   + full-page PNGs to `docs/products/better-business-web/screenshots/`.

```bash
python scripts/agency/build_portfolio_demos.py            # rebuild all
python scripts/agency/build_portfolio_demos.py --deploy   # rebuild + deploy BBW site
```

Demos are **honestly labeled** as concept demos; business details are fictional,
craft reflects real builds.
