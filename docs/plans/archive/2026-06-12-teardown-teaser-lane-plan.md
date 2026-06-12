---
status: done
change_id: teardown-teaser-lane
owner: kashane
last_reviewed: 2026-06-12
---

# Teardown-teaser lane — implementation plan

**Date:** 2026-06-12
**Source:** item 7 of [2026-06-11-bbw-v2-strategic-build-list-plan.md](2026-06-11-bbw-v2-strategic-build-list-plan.md)
**Status:** built + proven on 3 real prospects (B.B. King's, Big Boy, Casola's). Batch-to-50 is a runtime activity (capture ~25s/site + agent-filled persona panels).

## What shipped (2026-06-12)

- `scripts/agency/build_teardown_teaser.py` — `prepare` / `finish` orchestrator.
- `packages/agency/teardown_teaser.py` — cohort selection, prompt prep, the
  **no-invented-findings** validation gate, teaser/card/draft renderers.
- `scripts/web/shoot_url.mjs` — external-URL capture (screenshot + innerText), with
  bounded waits + a hard wall-clock guard so flaky sites fail fast.
- `scripts/web/card_to_png.mjs` — annotated-card HTML → PNG.
- `packages/agency/conversion_personas`: `smallest_panel()`.
- Outreach integration: `build_teaser_messages()`, `teaser` in `KNOWN_VARIANTS`,
  an additive `lane` field on `OutreachClientRow`, a teaser gate + row in
  `outreach_lane.py`, and a teaser copy branch + `Teaser lane` facet in
  `outreach_actions.py`.
- Tests: `tests/python/unit/test_teardown_teaser.py` (17, incl. the guardrail and
  the dashboard-surfacing integration).

Refinements vs. the original plan: (a) the dashboard ledger filters to `A_gold`, so
teaser prospects are flagged with `teaser_lane: true` on the record and surfaced via
an additive `lane` field rather than shoehorned into the demo lane; (b) the message
builder reads the validated `teaser.json` sidecar at render time, so dashboard copy
never drifts from the on-disk teaser.

## TL;DR

Build `scripts/agency/build_teardown_teaser.py`: a lane that turns **owned_site**
prospects (61% of the audited DB, 3,712 records) into a one-page Conversion-Audit
teaser. For the highest-review owned-site prospects, we run a *light* Conversion Lab
pass against their **existing homepage**, extract the top-3 conversion blockers
(each traceable to persona output), render a `teaser.md` + an annotated card PNG of
their own site, and emit a `variant=teaser` outreach draft pitching the **paid
Conversion Audit ($199 / $750)** — not a rebuild.

**Settled decisions**

1. **Conversion Lab execution = agent-in-the-loop.** The CL path has no autonomous
   LLM client today (it's `prepare → paste reviews JSON → render`). We mirror that
   contract: the script `prepare`s inputs, Claude runs the smallest persona panel
   and writes `reviews.json`, the script `finish`es (renders + validates).
2. **Target = highest-review owned_site, generate regardless of email.** Only
   282/3,712 owned_site records carry a `contact_email` and the top-review ones have
   none, so we prioritize by `user_ratings_total` and surface drafts in the dashboard
   for the operator to route/backfill the channel.
3. **`genre_id` passed directly as `vertical`** — the modifier `verticals:` lists
   already contain every genre_id verbatim. No mapping table.
4. **New external-URL capture** — `shoot.mjs` only serves local `distDir` builds, so
   a sibling `shoot_url.mjs` captures the prospect's live homepage. `shoot.mjs`'s
   local-build contract stays untouched.
5. **Do not touch `packages/schemas/conversion_lab.py`** (founder-approval boundary).
   Findings + evidence provenance live in a teaser sidecar, not the CL schema.

## Why

`owned_site` prospects are the **majority** of the DB, are easier to contact (sites
list contacts), and have already paid for web work. Conversion Lab is the right
product for them but is only positioned as a preflight today. This lane repositions
it as the lead product for the owned-site majority.

## Data reality (verified 2026-06-12)

| Fact | Value |
|---|---|
| owned_site records | 3,712 |
| …with a site URL (`web_verify_url` \| `contact_owned_website`) | 3,486 |
| …with `user_ratings_total` | 2,260 |
| …with `contact_email` | 282 |
| Top genres | auto_repair (514), beauty_salon (394), coffee_shop (356), restaurant (324), barber_shop (324) |

Cohort = `verdict==owned_site` AND has a site URL AND has a review count, sorted by
`user_ratings_total` desc, `--limit 50`.

## Architecture — pipeline per place_id

```
select cohort ─▶ capture homepage ─▶ prepare CL input ─▶ [agent: run panel]
   ─▶ finish: render report + extract+validate 3 findings
   ─▶ render teaser.md + annotated card PNG
   ─▶ emit variant=teaser outreach draft ─▶ register in outreach lane ledger
```

The script follows the existing `run_conversion_lab.py` two-subcommand shape so the
agent-in-the-loop step is explicit and batchable:

- `build_teardown_teaser.py prepare --limit 50` → selects cohort, captures homepages,
  writes `INPUT.json` + `PROMPTS.md` per prospect, prints the list of `reviews.json`
  paths Claude must fill.
- *(agent runs the panels, writes each `reviews.json`)*
- `build_teardown_teaser.py finish [--place-id … | --all]` → renders report, extracts
  + validates the 3 findings, renders teaser + card, emits draft, registers ledger.

### Stage 1 — Capture homepage  *(new: `scripts/web/shoot_url.mjs`)*

Reuses `shoot.mjs`'s Playwright prep (reduced-motion, scroll-to-reveal, font/image
settle). Takes an **external URL**; writes:
- `homepage.png` — full-page screenshot (card background / annotation source)
- `homepage.txt` — rendered `innerText` (becomes Conversion Lab `page_copy`)

Why both in one pass: avoids a JS-blind `requests` fetch and double-loading the page.
Handles dead/parked sites by exit code → prospect skipped with a logged reason.

### Stage 2 — Prepare Conversion Lab input

```python
ConversionLabInput(
    product_id=<place_id slug>,
    vertical=record["genre_id"],          # modifiers already list these
    target_action=ConversionAction.CALL,  # owned_site default; FORM if booking_url present
    url=site_url,
    page_copy=homepage_txt,
    known_objections=[],
)
```

**Smallest persona panel.** No selector exists today; add `smallest_panel(panel, n=3)`
to `packages/agency/conversion_personas/__init__.py` returning the first N core
personas (urgent-problem-solver, skeptical-researcher, premium-convenience-buyer).
Keeps the pass light and cheap. Artifacts → `state/prospects/sites/<pid>/conversion_lab/`.

### Stage 3 — Run panel (agent-in-the-loop)

Claude reads `PROMPTS.md` + `homepage.txt`, emits `reviews.json` (list of
`PersonaReview` dicts). The script then renders `REPORT.md` via the existing
`write_report`/`ConversionLabReport.from_dict` (unchanged).

### Stage 4 — Extract + **validate** the 3 findings  *(guardrail core)*

From the rendered report, take the top-3 blockers. For each, attach an
`evidence_quote` pulled verbatim from a persona's `objections`/`trust_gaps`/
`clarity_notes`, plus the `persona_id`. **Validation gate:** assert each
`evidence_quote` is a verbatim substring of `reviews.json`; if not, refuse to render
(no invented findings). Provenance saved to `teaser.json` sidecar (not the CL schema):

```json
{"findings":[{"finding":"…","evidence_quote":"…","persona_id":"skeptical-researcher"}, …]}
```

### Stage 5 — Render teaser artifact

- `state/prospects/sites/<pid>/teaser.md` — one page: the 3 findings + evidence
  quotes, advisory framing, **methodology disclosure** ("structured heuristic review
  using a synthetic audience"), CTA = paid Conversion Audit. Pricing read from
  `packages/agency/catalog.py` (`conversion_snapshot` $199 / `conversion_audit` $750)
  so it stays in sync with the catalog.
- `state/prospects/sites/<pid>/teaser-card.png` — annotated card: their `homepage.png`
  with 3 callout chips. Rendered via new `scripts/web/card_to_png.mjs` (serves an HTML
  card template, screenshots it — same Playwright dependency).

### Stage 6 — Outreach `variant=teaser`

1. Add `"teaser"` to `KNOWN_VARIANTS` in `packages/agency/outreach_store.py`
   (dashboard dropdown auto-populates).
2. New teaser message template + a `variant=="teaser"` branch in
   `packages/agency/outreach_messages.build_messages_from_context` that renders the
   **paid-audit pitch** (no `mockup_url`; references the homepage findings + price).
3. Write the per-prospect draft to `state/prospects/sites/<pid>/outreach-teaser.md`.
4. Register the prospect into the outreach lane ledger (`client-status`) so the
   dashboard surfaces it; `variant=teaser` tags every logged touch.

## File change list

**New**
- `scripts/agency/build_teardown_teaser.py` — orchestrator (`prepare` / `finish`)
- `scripts/web/shoot_url.mjs` — external-URL screenshot + innerText
- `scripts/web/card_to_png.mjs` — HTML card → PNG
- teaser message template (alongside existing outreach templates)
- per-prospect artifacts under `state/prospects/sites/<pid>/`: `homepage.{png,txt}`,
  `conversion_lab/{INPUT.json,PROMPTS.md,reviews.json,REPORT.md}`, `teaser.{md,json}`,
  `teaser-card.png`, `outreach-teaser.md`

**Modified** (all within `packages/agency/` — *not* founder-gated)
- `packages/agency/conversion_personas/__init__.py` — `smallest_panel(panel, n=3)`
- `packages/agency/outreach_store.py` — add `"teaser"` to `KNOWN_VARIANTS`
- `packages/agency/outreach_messages.py` — teaser variant branch
- `packages/dashboard/outreach_panel.py` — surface teaser drafts (dropdown auto-updates)
- outreach-lane ledger registration for teaser prospects (reuse existing lane-add path)

**Must NOT touch:** `packages/schemas/conversion_lab.py`, `packages/policies/`,
`skills/canonical/`, `skills/registry.yaml` (founder approval).

## Guardrails (from the eval doc)

- **Advisory only, no revenue predictions** — inherit Conversion Lab's built-in
  caveat; teaser template repeats it.
- **Honest framing** — pitch is the paid Conversion Audit, not a rebuild; methodology
  (synthetic audience / heuristic review) disclosed in the teaser and "if asked".
- **No invented findings** — Stage 4 substring-validation gate enforces every claim
  traces to `reviews.json`.

## Done criteria → mechanism

| Done criterion | Mechanism |
|---|---|
| 50 teaser artifacts + drafts for highest-review owned_site | cohort select + `--limit 50` |
| Each claim traces to persona output | Stage 4 evidence-quote substring gate |
| Drafts appear in dashboard under teaser variant | `KNOWN_VARIANTS` + ledger registration + teaser branch |
| Annotated image of their own site | `shoot_url.mjs` + `card_to_png.mjs` |

## Phasing

1. **Capture + lab** — `shoot_url.mjs`, cohort select, prepare CL input,
   `smallest_panel`. Prove end-to-end on 1 prospect.
2. **Teaser render** — `teaser.md`, `card_to_png.mjs`, evidence-quote gate.
3. **Outreach + dashboard** — `teaser` variant, template, ledger registration,
   dashboard surfacing.
4. **Batch** — run 50; screenshot the dashboard teaser tab + a sample card as proof.

## Open risks

- **Email coverage** — only 282/3,712 have email; high-review set has ~none. The 50
  drafts are generated regardless; sendability depends on a later homepage email-scrape
  pass (out of scope here, flagged as the natural follow-on).
- **JS-heavy / parked homepages** — `shoot_url.mjs` must fail gracefully and skip.
- **Card legibility** — tall homepages make a single annotated card awkward; may need
  to crop to the hero region (reuse `make_thumb.py`'s crop ratio).
