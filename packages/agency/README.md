# packages/agency — WaaS lane business logic

Business logic for the Website-as-a-Service agency lane: prospecting, demo sites,
client onboarding, and monthly retainer ops. Runnable entrypoints live in
`scripts/agency/`; site machinery (scaffold/validation/palette) lives in
`packages/web/`.

> **Start at the lane map:** [docs/agency/README.md](../../docs/agency/README.md)
> — pipeline stages, the `state/prospects/` data layout, and the three web build paths.

## Modules by area

**Prospects & demos**
- `prospect_site.py` — render/deploy glue for prospect mockups; `resolve_prospect_dist_dir()` (requires `dist-v2/`, refuses legacy `dist/`).
- `demo_theme.py` — **legacy** token-fill theming (path A, deprecated for prospects; kept for `--legacy-build` + some portfolio).
- `demo_maps.py` — map embeds for demos.
- `outreach.py` — channel × genre outreach templates.

**Sale → client (Phases 3–6)**
- `promotion.py` / `client_lifecycle.py` — promote prospect → client; lifecycle state.
- `intake.py` — capture business details → `CLIENT_BRIEF.md` + client-site context.
- `launch.py` — pre-launch readiness (composed by the `launch-checklist` skill).
- `local_seo.py` — service × geo page generation with thin-content guards.

**Retainer ops**
- `retainer_ops.py` — plans the month's actions, **fenced to active billing** (a
  lapsed/disputed client gets an empty plan), and tracks each planned action to
  completion (`mark_action_complete` / `outstanding_actions`), not just a wishlist.
- `retainer_executor.py` — runs the safe prep actions of a plan (injectable
  executors; tracks completion) and is the **single gate** for outward/irreversible
  steps: `assert_outward_action_allowed()` routes ad go-live / review SMS / deploy
  to their policy gates, so the gates are enforced from production code, not tests.
  `default_safe_executors` auto-runs the drafts that work from the persisted
  workspace (`intake.json`): GBP changeset, Google/Meta ads (eligibility-checked),
  local SEO pages, and the monthly report (Plausible) — each skips cleanly when its
  inputs aren't ready. `manage_booking` stays operator-run.
- `monthly_report.py` — monthly report; `metrics_from_plausible()` wires real
  visit/lead numbers in (a missing lead goal degrades to "Not tracked yet", never a fake 0).
- `lead_health.py` — the `hosting` "contact-form monitoring" SLA: flags leads that
  were captured but never emailed to the owner (silent Resend failure).
- `gbp.py`, `google_ads.py`, `meta_ads.py`, `plausible.py` — Google Business Profile, Ads, analytics.
- `ad_policy.py` — ad vertical eligibility (banned/restricted verticals per platform);
  the draft CLIs refuse to draft an un-runnable campaign.
- `ad_creative.py` — ad images at all placements + promo overlays; **real client
  photos first, AI (Gemini) fallback**; drafts only (go-live stays gated).
- `business_email.py`, `booking.py`, `promo_page.py` — email setup, booking embeds, promo pages.

**Money**
- `billing.py`, `payments.py`, `stripe_receiver.py` — invoicing + Stripe events.

**Shared**
- `catalog.py`, `templates.py`, `registry.py`, `approvals.py`, `inbound.py`,
  `inbound_fulfillment.py` — service catalog, render templates, registries, approval
  glue, and inbound-lead handling.

## Conventions

- Workers don't own policy — policy lives in `packages/policies/`.
- Demo palette: derive from the business's own visual cues first; the design
  reference (`packages/web/design_reference/`) is fallback only.
- Deploy is a separate, approval-gated step — build logic here stops at green validation.
