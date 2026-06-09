# packages/web — site machinery

Shared code for building, validating, theming, and deploying web sites. Used by
the agency lane's **client sites** (path C: `scaffold.py` → Astro under
`products/<slug>-site/`) and for offline preview/validation.

> Lane map: [docs/agency/README.md](../../docs/agency/README.md) (incl. the three
> web build paths — this package owns path C).

## Modules

| Module | Purpose |
|---|---|
| `scaffold.py` | Materialize an Astro static-first landing site from a token context (`scaffold_site`); also `render_landing_html()` for offline, Node-free preview. `default_context` / `local_business_context` build the token dicts. |
| `design_studio.py` | Premium-design contract for the web lane: creates structured art-direction packets before a build and screenshot-backed visual review reports after a build. Complements the technical gate by rejecting valid-but-generic pages. |
| `validation.py` | The web gate — `validate_web_dist()` runs build / internal-links / assets / responsive / accessibility / **contrast** checks on a built `dist/`. |
| `palette.py` | Design intelligence: WCAG contrast primitives (`contrast_ratio`, `passes_aa`), a genre→palette table (`GENRE_PALETTES`), and a deterministic HSL synthesizer (`derive_palette`). |
| `ux_audit.py` | Deeper responsive/a11y/perf/SEO audit (`audit_dist`) behind the `web-ux-audit` + `launch-checklist` skills. |
| `build.py` / `deploy.py` | Build orchestration and the (approval-gated) deploy path. `NetlifyDeployTarget` also attaches a client's custom domain — `attach_domain` (www-primary + apex-alias, GET-merge-PATCH so it never clobbers existing aliases), `provision_ssl`/`get_ssl` (+ `CertState`), and `transfer_ownership` for client handoff. Driven by `packages/agency/domain_attach.py`. |
| `stripe_monetization.py` | Stripe wiring for monetized sites. |

## Subdirectories

- **`scaffold/`** — the Astro template(s) copied by `scaffold_site` (`astro-landing/`).
- **`design_reference/`** — curated, MIT-licensed design data (palettes, font
  pairings, UX rules) + `LICENSE` + `ATTRIBUTION.md`. The machine-readable palette
  form lives in `palette.py::GENRE_PALETTES`; keep the two in sync.

## Contrast gate (note)

`check_contrast` is **sound, not complete**: it resolves only literal light-mode
`:root` foreground/background pairs and *skips* (never guesses) `var()`,
`color-mix()`, alpha<1, and dark-mode `@media` values. Body text is held to AA
4.5:1; on-color labels (CTA on accent) to 3:1.

## Design Studio gate (note)

`design_studio.py` is intentionally separate from `validation.py`: it evaluates
art direction, not HTML mechanics. A page can pass the web gate and still fail
Design Studio review when the hero is forgettable, imagery is incoherent, type is
generic, or screenshots are missing. See
[`docs/agency/design-studio-lane.md`](../../docs/agency/design-studio-lane.md).
