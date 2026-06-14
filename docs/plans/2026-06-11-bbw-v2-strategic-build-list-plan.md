---
status: open
change_id: bbw-v2-strategic-build-list
owner: kashane
last_reviewed: 2026-06-12
---

# BBW v2 — Strategic Build List (2026-06-11)

> **TL;DR** — Output of the 2026-06-11 v1→v2 strategic review. Measured state: 29,820
> collected → 2,428 audited → 896 verified targets → 587 demos built → **0 outreach
> sent → 0 clients → $0 revenue**. v2 is therefore organized around market contact,
> not more platform. Three phases: (0) the Send Sprint — make manual sending fast,
> logged, and compliant, and get every existing draft out the door; (1) close the
> reply loop and open two new outreach arms (teardown-teaser for the owned-site
> majority, postcard/QR for phone-only); (2) scale only what the send data proves —
> demo-build automation, verification pre-filter, new intent-rich prospect sources.
> Each numbered item below is a self-contained spec a coding agent can build cold.
> Hard invariants for every item: **no automated outbound send, no unapproved spend,
> no deploy without operator review; `packages/schemas/` and `packages/policies/`
> edits require explicit founder approval.**

## How to use this file

Hand one numbered section to one coding agent. Each spec includes: Why (context),
What (behavior), Where (files), Done (acceptance), Guardrails (boundaries). All
paths are relative to repo root. Read `REPO_MAP.md` and
`docs/preflight-for-agents.md` before mutating anything.

> **Status (2026-06-12 audit):** Phase 0 and Phase 1 are SHIPPED and audited —
> items 1–7 pass their acceptance criteria with strong test coverage (~106
> outreach/suppression/funnel tests green). Item 8 (postcards) is DEFERRED by
> founder decision. The audit found three cross-module integration gaps that
> per-item tests could not catch; they are specced as **Pre-Phase-2 fix items
> F1–F3** below (between Phase 1 and Phase 2). Do not start Phase 2 items until
> F1–F3 are done and the Phase 2 entry criteria are met.

---

## Phase 0 — The Send Sprint (ship this week)

### 1. Extend the shipped Outreach Action Dashboard for measurable sending

> **Status (2026-06-12): SHIPPED** — variant column + panel selector, suppression
> filtering, due-queue view all verified (commits `4663bd1`, `2ea54d3`).

**Why.** The send cockpit ALREADY EXISTS: the Outreach Action Dashboard shipped to
main 2026-06-10 (commit `2d2223d`; plan:
`docs/plans/2026-06-10-outreach-action-dashboard.md`) — per-channel launch buttons
with prefilled Gmail compose URLs, contact-override editing, append-only touch
logging into `packages/agency/outreach_store.py`, served at `127.0.0.1:8765`.
Phase 0 is therefore mostly *operational* (open it and send), but three gaps keep
sends from being measurable and safe at volume: no variant tagging (A/B arms
can't be compared), no suppression check (item 2), and no follow-up due queue
(item 6).

**What.** Three additive extensions to the existing dashboard stack:
- **Variant tagging.** Add a `variant` column to `outreach_touches`
  (`packages/agency/outreach_store.py`; additive SQLite migration). The panel's
  "✓ Log sent" flow records the active variant (default `demo-link`; selectable
  per-session in the panel header). Surfaces later in funnel telemetry (item 4).
- **Suppression filter.** The panel queue and `outreach_lane` row rendering
  consult `suppression.is_suppressed()` (item 2) and hide/grey suppressed
  prospects; a "disqualify" action in the panel writes suppression with a reason.
- **Due-queue view.** A panel section listing prospects whose `next_touch_at`
  (item 6) has passed, sorted oldest-first, with the touch-2/touch-3 draft
  prefilled in the launch buttons.

**Where.** `packages/agency/outreach_store.py`, `packages/dashboard/outreach_panel.py`,
`apps/api/outreach_endpoint.py`, `packages/agency/outreach_lane.py`. Do not touch
`apps/worker-outreach/` — its refuse-to-send boundary stays. Preserve all hard
boundaries from the 2026-06-10 plan (no automated sending; touch = manual confirm;
bind 127.0.0.1 only; no schema/policy edits).

**Done.** Operator can clear the ready queue in one session with every send logged
with channel + variant + timestamp; suppressed prospects cannot be launched;
follow-ups surface when due. Tests for variant persistence, suppression exclusion,
due-queue ordering; existing 21 dashboard tests stay green.

### 2. Suppression list + opt-out floor

> **Status (2026-06-12): SHIPPED** — `packages/agency/suppression.py`, fail-closed,
> wired into queue/touch/sequencer; opt-out line in email templates (8 tests).

**Why.** Before volume sending, BBW needs a fail-closed do-not-contact registry and
opt-out handling, or it builds CAN-SPAM liability with every batch.

**What.** `packages/agency/suppression.py`:
- A suppression store at `state/prospects/suppression.json` (or a table in
  `outreach.sqlite3` — pick one, document it): entries keyed by place_id AND by
  contact handle (email/IG/FB/phone), with reason + date + source
  (`operator`, `reply-stop`, `disqualified`).
- API: `is_suppressed(record) -> bool` (checks place_id and every contact channel),
  `suppress(record_or_handle, reason, source)`.
- Wire fail-closed into: outreach draft generation (`packages/agency/outreach.py`
  skips suppressed), the dashboard queue (item 1), and the follow-up sequencer
  (item 6).
- Add a one-line opt-out sentence to the email templates (e.g. "Reply 'no thanks'
  and I won't email again.") — edit the templates under
  `state/prospects/outreach/` and the email renderer in `outreach.py`.

**Done.** A suppressed prospect can never appear in a queue or get a new draft;
tests prove fail-closed behavior (unknown/missing data → excluded); templates carry
the opt-out line; reply-sync (item 5) can call `suppress()` on STOP-intent replies.

**Guardrails.** Suppression is one-way by code (un-suppress only by manual edit
with founder involvement). No schema changes to `packages/schemas/` — store
suppression in state, not on ProspectRecord.

### 3. Batch demo deploy + URL backfill

> **Status (2026-06-12): SHIPPED** — `--batch`/`--cleanup-drafts` with idempotency,
> gates, backfill (13 tests). Bonus: gated `--named-site` production mode
> (`529f43a`) + scaffold-copy deploy lint (`103d004`). Only 18/586 deployed so
> far — running it at scale is operator work, not code work.

**Why.** 587 demos exist; only ~12 are live. A demo that isn't deployed can't be
sent. Deploys are currently one-at-a-time CLI invocations.

**What.** Extend `scripts/agency/build_prospect_site.py`:
- `--batch <csv-or-glob>`: deploy every listed place_id's `dist-v2/` to a Netlify
  draft URL via the existing `NetlifyDeployTarget` (`packages/web/deploy.py`),
  honoring the existing secret-scan and approval gates; write `mockup_url`,
  `mockup_site_id`, `mockup_deploy_id` back to the warehouse record (existing
  fields).
- Rate-limit + resume: idempotent (skip place_ids that already have a live
  `mockup_url` unless `--force`), continue past per-site failures, summary table at
  the end.
- `--cleanup-drafts`: list and (with confirmation) delete Netlify draft sites for
  prospects marked `lost`/suppressed, so the account doesn't accumulate junk.

**Done.** One command deploys the next 50 ready demos; records carry working URLs;
re-running is a no-op; cleanup lists before deleting and requires explicit
confirmation.

**Guardrails.** Draft/preview deploys only — production deploys keep their existing
approval gate. Respect Netlify rate limits (sleep between deploys).

### 4. Funnel telemetry — one honest scoreboard

> **Status (2026-06-12): SHIPPED** — `funnel_report.py` + daily launchd schedule +
> dashboard refresh button; 1.6s runtime; variant/channel breakdowns (13 tests).
> One definition mismatch ("sent" counts legacy disqualification calls; ledger
> says 9, funnel says 11) — folded into fix item F2.

**Why.** The 587-built/0-sent imbalance was invisible until measured by hand. The
operating metric of the company should be computed daily, not discovered in audits.

**What.** `scripts/agency/funnel_report.py` writes
`state/prospects/funnel-report.md` (+ `.json`):
- Stage counts measured from primary sources: records dir (collected), audited CSVs
  + record verdict fields (audited, targets by verdict class), `sites/*/dist-v2/`
  (built), records with `mockup_url` (deployed), `outreach_touches` (sent, by
  variant and channel), engagement statuses (replied / proposal / won / lost),
  billing ledger (active clients, MRR at catalog prices).
- Per-stage conversion rates, deltas vs the previous run (keep last run's JSON),
  and a "stages with zero data" callout.
- Optional `--by vertical|city` breakdown for sent/replied once data exists.
- Wire into the runtime-supervisor schedule if trivial; otherwise document the
  cron line.

**Done.** One command, accurate counts matching ad-hoc queries, runs in <30s,
output is committed-format-stable so diffs are readable.

---

## Phase 1 — Close the loop, open new arms (weeks 2–4)

### 5. Reply sync — Gmail-polling reply tracker

> **Status (2026-06-12): SHIPPED** — readonly-scope poller live (cursor persisted,
> ~100 threads processed), token-first + sender-fallback matching, STOP-intent →
> suppression + operator flag (14 tests). BUT: zero ref tokens recorded for the
> 4 emails already sent — matchability gap specced as fix item F3.

**Why.** With sends starting, replies must not depend on the operator remembering
to update a ledger. The reply is the single most valuable event in the company;
it should be captured automatically.

**What.** `packages/agency/reply_sync.py` + a small poller entry
(`apps/worker-reply-sync/` mirroring the billing-poller pattern):
- Outbound drafts get a short per-prospect token (e.g. `ref:BBW-<6char>` derived
  from place_id) appended to the email subject or body footer by `outreach.py`;
  store token→place_id in the outreach DB.
- Poller reads the BBW inbox read-only (Gmail API with readonly scope; config via
  env like the other workers), matches inbound threads by token first, sender
  address second; on match: advance `engagement_status` → `replied`, log a touch
  (`direction=inbound`), write the thread snippet to
  `state/prospects/outreach-lane/replies/<place_id>.md` for operator review.
- STOP-intent detection (conservative keyword list: "unsubscribe", "stop",
  "not interested, don't", "remove me") → call `suppression.suppress()` AND flag
  for operator confirmation rather than silently acting beyond suppression.
- Never sends, never labels/moves mail, never marks read.

**Done.** A reply to a sent email shows up in the ledger as `replied` within one
poll interval with zero operator typing; STOP replies land in suppression; poller
is idempotent across restarts (persist last-seen history id/cursor in state).

**Guardrails.** Read-only mail scope. No auto-replies. IG/FB replies stay manual
(log via send console).

### 6. Follow-up sequencer (draft-only)

> **Status (2026-06-12): SHIPPED, with a live-data gap** — per-step cadence
> (+4d/+8d/stop-at-3), reply-cancel, suppression-exclude all code-enforced and
> tested. BUT: the 10 real sends logged 2026-06-12 have `next_touch_at=""` and
> `follow_up_due=0` — the sequencer never fired for them, so the due-queue is
> empty and follow-ups will silently never surface. Fix item F2.

**Why.** Cold outreach converts on touches 2–3 more than touch 1; today there is no
follow-up machinery at all.

**What.** Extend `packages/agency/outreach.py` + outreach DB:
- On a logged touch with no reply, schedule `next_touch_at` (+4 days for touch 2,
  +8 for touch 3, stop after 3) on the prospect's outreach row.
- Generate touch-2/touch-3 draft variants per channel (shorter, reference the
  demo URL again, one new concrete observation about their business from the
  content brief; obey `docs/agency/outreach-copy-rules.md`).
- The dashboard due-queue view (item 1) surfaces these; replies (item 5) cancel
  pending follow-ups; suppression excludes.

**Done.** After a touch-1 send, the prospect automatically appears in the due queue
on day 4 with a fresh draft; a reply or suppression removes them; max 3 touches
enforced by code.

### 7. Teardown-teaser lane — the owned-site flip

> **Status (2026-06-12): SHIPPED, with a reach blocker** — 50 teasers built with
> verbatim-quote validation (no invented findings), card PNGs, `variant=teaser`
> drafts, dashboard lane + homepage dedupe (`69e6b42`). BUT: of the 50 teaser
> prospects only 1 has an email and 2 have any digital channel (pool-wide:
> 282/3,712 owned_site have email). The arm cannot run without contact
> harvesting. Fix item F1.

**Why.** 61% of audited prospects (1,489 of 2,428) were dropped for having a real
website. They are the majority of the database, they're easier to contact (their
sites list emails), and they've already demonstrated willingness to pay for web
work. Conversion Lab is the product for them; today it's only positioned as a
preflight for existing prospects.

**What.** `scripts/agency/build_teardown_teaser.py`:
- Input: place_ids with `web_verify_verdict == owned_site` and a known site URL,
  prioritized by review count.
- Run a light Conversion Lab pass (`packages/agency/conversion_lab.py`, smallest
  persona panel) against their existing homepage → extract the top 3 conversion
  blockers with evidence quotes.
- Render a one-page teaser artifact: `state/prospects/sites/<place_id>/teaser.md`
  plus a shareable image/PDF (screenshot of their own site annotated with the 3
  findings — reuse `scripts/web/shoot.mjs` for capture; simple HTML→PNG for the
  annotated card).
- Generate a matching outreach draft variant (`variant=teaser`) via `outreach.py`:
  the pitch is the paid Conversion Audit ($100/$250 per
  `packages/agency/catalog.yaml` add-ons), not a website rebuild.

**Done.** 50 teaser artifacts + drafts generated for the highest-review-count
owned-site prospects; each teaser's claims trace to persona output (no invented
findings); drafts appear in the outreach dashboard under the `teaser` variant.

**Guardrails.** Advisory language only — no revenue predictions (existing
Conversion Lab rule). Honest framing: findings are from a structured heuristic
review, with synthetic-audience methodology disclosed if asked.

### 8. Postcard/QR channel for phone-only targets

> **Status (2026-06-12): DEFERRED** — founder decision; doesn't fit the current
> schedule/goals. Keep the spec; revisit if the phone-only segment proves
> valuable or digital channels underperform.

**Why.** `none_found` and many `marketplace_only` targets have no digital channel —
phone only. Physical mail with a QR code to their own demo has zero deliverability
risk, zero spam law exposure (CAN-SPAM doesn't cover postal mail), and high novelty.

**What.** `scripts/agency/build_postcards.py`:
- Input: targets with a deployed `mockup_url` and no email/IG/FB.
- Render a 6×4 postcard PDF per prospect: business name, one-line hook, a cropped
  screenshot of THEIR demo (from `screenshots/`), QR code to `mockup_url`
  (append `?src=qr` so Plausible/Netlify analytics attribute scans), BBW contact.
- Batch mode: one merged PDF for at-home printing, or per-card PDFs sized to
  Lob/PostGrid specs. Actual Lob API submission, if implemented, goes behind a
  spend approval gate consistent with `packages/policies/agency_gates.py`
  conventions (do NOT edit policies without founder approval — if a new gate type
  is needed, stop and ask).
- Log a `postcard` touch per prospect on export (`variant=postcard`).

**Done.** A batch of 20 postcards renders correctly (QR scans to the right demo),
touches logged, spend path (if any) gated.

---

## Pre-Phase-2 fix items (from the 2026-06-12 audit)

Three integration gaps found by auditing runtime state (`outreach.sqlite3`,
`client-status.json`) against the shipped code. Each per-module test suite is
green; these are the seams *between* modules that only live data exposed. Hand
each item to one coding agent. Same invariants as everything else in this file:
no automated outbound send, no unapproved spend, no edits to
`packages/schemas/` or `packages/policies/` without founder approval. Read
`REPO_MAP.md` and `docs/preflight-for-agents.md` first.

### F1. Owned-site contact harvester — unblock the teaser arm

**Why.** The teardown-teaser lane (item 7) is built and validated, but it is
drafts-to-nowhere: of the 50 generated teasers, exactly 1 prospect has a
contact email and only 2 have any digital channel. Pool-wide, only 282 of
3,712 `owned_site` prospects have `contact_email`. These businesses HAVE
websites — their sites publish contact info; nobody has harvested it because
the contact-resolution pass historically only ran on no-site targets.

**What.** A polite, single-domain contact harvester:
- New `packages/prospecting/site_contact_harvest.py` + CLI
  `scripts/prospecting/harvest_site_contacts.py`.
- Input: `owned_site` prospects with a known site URL (reuse the URL-resolution
  + homepage normalization already in `packages/agency/teardown_teaser.py` —
  `site_url_for()` / `normalize_site_url()`). Default worklist: the 50 existing
  teaser-cohort place_ids first (`lane == "teaser"` rows in
  `state/prospects/outreach-lane/client-status.json`), then top-N `owned_site`
  by review count (`--limit`).
- Per prospect: fetch the homepage plus up to 2 likely contact pages (`/contact`,
  `/about`, links whose anchor text matches contact/about — same-domain only),
  with timeouts, one polite delay between requests, a real User-Agent, and
  robots.txt respect. No retries beyond 1, no JS rendering — plain HTTP GET.
- Extract: `mailto:` targets, email-regex hits (filter junk: `example.com`,
  `sentry`/`wixpress`/`godaddy` noise, image filenames), Instagram/Facebook
  profile URLs, and a contact-form URL if a `<form>` with an email/message
  field exists. Normalize (lowercase emails, canonical IG/FB handles).
- Write results as **contact overrides** via the existing
  `OutreachStore.set_override()` path (`packages/agency/outreach_store.py`) with
  a source note `site-harvest` — the dashboard already merges overrides into
  effective contacts. Do NOT mutate `state/prospects/records/*.json`
  (pipeline-owned) and do NOT touch `packages/schemas/`.
- Verify (and extend if needed) that the outreach lane's effective-contact
  overlay applies to **teaser-lane rows**, not just demo-lane rows, so harvested
  emails immediately make teaser rows launchable; add a test.
- Extend `teardown_teaser.select_cohort()` to prefer prospects that have (or
  just gained) a sendable digital channel; phone-only prospects only with an
  explicit `--allow-phone-only` flag.
- Emit a hit-rate summary (N fetched / emails found / IG / FB / form-only /
  nothing) to stdout and append a row to
  `state/prospects/contact-harvest-log.jsonl`.

**Done.** Harvester run over the 50-teaser cohort + top-200 owned_site by
review count; measured hit-rate reported; ≥50% of the teaser cohort is
launchable (or replaced by contactable equivalents via re-selection); overrides
visible in the dashboard; funnel report's blocked/needs-contact count drops
accordingly; unit tests for extraction (fixture HTML), junk filtering,
override writing, and teaser-row overlay.

**Guardrails.** Same-domain fetches only, ≤3 pages per site, rate-limited —
this must look like a polite visitor, not a crawler. No third-party enrichment
APIs (Hunter/Apollo stay out of scope). Suppressed prospects are skipped.

### F2. Sequencer + ledger backfill — the first 10 sends must get follow-ups

**Why.** 10 real sends were logged 2026-06-12 (4 email, 6 SMS; see
`outreach_touches`). Their ledger rows show `status="sent"` and a correct
`last_touch_at`, but `next_touch_at=""` on every one, and `summary.follow_up_due`
is 0 — the sequencer (item 6) never fired for them. Net effect: the due-queue
stays empty forever and the company's first real prospects silently never get
touch 2. Separately, the funnel report counts "sent = 11" while the ledger says
9 — the funnel's distinct-place_id count includes the two 2026-06-10
disqualification calls.

**What.**
1. One-shot backfill: `scripts/agency/backfill_followups.py`. For every ledger
   row (`state/prospects/outreach-lane/client-status.json` via
   `packages/agency/outreach_lane.py`) with a sent-class status, an outbound
   touch history, and empty `next_touch_at`: compute `outbound_count` from
   `outreach_touches`, call
   `outreach_sequencer.schedule_next_touch(...)` anchored at `last_touch_at`,
   and write the row. `--dry-run` is the default; `--apply` writes. Idempotent
   (re-running changes nothing). Skips suppressed and terminal-status rows.
2. Root-cause + regression-proof the live path: figure out which send-logging
   path was used on 2026-06-12 (dashboard `record_touch` vs CLI
   `log_manual_touch`) and why it scheduled nothing (most likely the sends
   predate commits `a311bf1`/`e6fdaef`; if instead one path skips the
   sequencer, fix that path). Add integration tests asserting that BOTH paths,
   on a sent touch: advance status, schedule `next_touch_at` per cadence, and
   (for email) record the ref token. These tests are the contract that the
   2026-06-12 desync can never recur.
3. Align the "sent" definition: funnel (`packages/agency/funnel.py`) and ledger
   summary must agree. Recommended: funnel counts distinct place_ids with an
   outbound touch whose ledger row is not disqualified/do-not-contact; document
   the chosen definition in both modules. Add a test pinning funnel-sent ==
   ledger-sent on a fixture with a disqualification call in history.

**Done.** The 10 sent rows carry correct `next_touch_at` (+4d from their
2026-06-12 send), `follow_up_due` surfaces them in the dashboard due-queue when
due; integration tests cover both logging paths end-to-end; funnel and ledger
report the same sent count; backfill is idempotent and dry-run-first.

### F3. Reply matchability — token-on-send guarantee + poller hardening

**Why.** `outreach_ref_tokens` is EMPTY despite 4 emails sent — token-first
matching (item 5's primary mechanism) cannot work for any mail already in
flight. Those 4 can only match by sender address, which fails if the owner
replies from a different mailbox than the one we recorded. The audit also
flagged two hardening gaps: no unit test for the poller's cursor-state
roundtrip, and unverified OAuth access-token refresh behavior.

**What.**
1. Matchability audit of the 4 sent emails: confirm each prospect's
   `contact_email` (including overrides) is present and normalized in the
   sender index that `reply_sync.resolve_place_id()` consults; check one sent
   draft artifact (`state/prospects/sites/<place_id>/outreach.md`) to determine
   whether the sent bodies actually contained the `ref:` footer. If they did,
   backfill `outreach_ref_tokens` with the deterministic tokens
   (`bbw_ref_token(place_id)` — deterministic, so backfill is safe); if they
   did not, document in the module docstring that pre-token sends rely on
   sender matching only.
2. Invariant, code-enforced: recording an email touch MUST record its ref
   token in the same transaction — move/duplicate the `record_ref_token()` call
   so that no email-channel touch path (dashboard endpoint, CLI, future
   callers) can skip it; add a test that fails if an email touch exists
   without a token row.
3. Poller hardening: unit test for `reply-sync-state.json` load/save roundtrip
   (cursor + processed-thread set, bounded at 2000); verify the Gmail worker
   refreshes an expired access token via the stored refresh token
   (`google.oauth2.credentials.Credentials` + `Request()` refresh) rather than
   dying — add the refresh call and a test with an expired-token fixture if
   missing.

**Done.** Every email touch has a token row (test-enforced invariant); the 4
historical sends' matchability is verified and documented; state-roundtrip and
token-refresh tests pass; no Gmail scope change (stays `gmail.readonly`).

### Phase 2 entry criteria (operational, founder-owned — no agent needed)

The code will be ready after F1–F3. The *experiment* is not ready until there
is send volume to learn from. Before starting any Phase 2 item:

- **≥150 sends total** across the demo-link arm (inventory exists: 586 built,
  18 deployed — run item 3's `--batch` and keep sending), and
- **≥30 teaser-arm sends** (unblocked by F1), and
- reply-sync has run over the resulting inbox for ≥1 week, so reply/variant
  data exists in the funnel report.

Rationale: Phase 2's biggest item (9 — demo-build automation) only makes sense
if the demo-led arm is the one that converts; if the teaser arm wins, the
build-automation priority changes shape. Don't automate the leg the data
hasn't voted for.

## Phase 2 — Scale what the data proves (month 2)

### 9. Demo Builder Agent — automate the build leg

> **Precondition (added 2026-06-12):** start this only after the Phase 2 entry
> criteria — if the teaser arm out-converts the demo arm, automating teaser
> throughput (cheap already) beats automating demo builds, and this item drops
> in priority. Note the scaffold-copy deploy lint (`103d004`) now applies to all
> deploys: generated builds must pass it, which is a useful extra gate for
> agent-built pages.

**Why.** Hand-building costs 2–4 founder-hours per demo. At plausible cold-convert
rates (~1 client per 20–40 demo-led sends) that's 40–160 founder-hours per client —
underwater at Package A/B prices. The gather→brief→design-direction inputs are
already structured; the Craft Pass and voice gates are written procedures; the
Design Studio loop (`scripts/agency/design_studio.py`, `packages/web/design_studio.py`)
already does build→judge→revise. Promote that loop to the default demo path.

**What.** `scripts/agency/auto_build_demo.py`:
- Input: a place_id whose `source/` contains place-details, photos, content brief,
  and design direction (generate the design direction from
  `packages/web/palette.py` + genre defaults when absent, flagging low-confidence
  palettes for operator override).
- Produce `dist-v2/index.html` (self-contained HTML + inlined CSS, same contract as
  hand-built demos) via an agent loop bound by:
  `state/prospects/sites/_scaffold/05-craft-pass.md` (checklist in the prompt),
  the voice/banned-word gate, `packages/web/validation.py` (contrast, a11y,
  390px/1440px responsive), and a screenshot self-review cycle
  (`scripts/agency/screenshot_demo.py`) with the Gemini judge
  (`packages/web/gemini_judge.py`) scoring against the visual rubric; revise until
  pass or 3 attempts, then flag for human.
- Batch mode: build N demos, emit a review gallery (existing
  `state/prospects/review-gallery/` convention) so the operator approves/rejects
  in one pass. Rejected builds carry operator notes back into a revise cycle.
- Log per-demo wall time and AI cost (token counts) to
  `state/prospects/build-metrics.csv`.

**Done.** 10 demos build end-to-end with ≤20 minutes total operator review; all
pass `validation.py` and the voice grep gate; cost per demo measured and logged;
output is byte-format-compatible with the existing deploy + screenshot tooling.

**Guardrails.** Deploys remain gated (item 3 path). Every factual claim in copy
must trace to the content brief — the brief is the only allowed source; no
invention. If the brief is too thin to build honestly, fail loudly instead of
padding.

### 10. Verification pre-filter — cut browse labor ~50%

**Why.** Verification/contact resolution is browse-only and bounds the top of the
funnel. There is a labeled dataset sitting in the repo: 2,428 audited rows with
ground-truth verdicts — use it.

**What.** `packages/prospecting/prefilter.py` + eval harness
`scripts/prospecting/eval_prefilter.py`:
- Cheap automated signals per candidate: HTTP/DNS probe of the Maps website field
  and obvious domain guesses (status, redirect target, parked-domain fingerprints);
  classify social/marketplace URLs with the existing logic in
  `packages/prospecting/web_presence.py`; Maps metadata heuristics (review count,
  category, chain detection).
- Output a tri-state: `auto_owned_site` (drop), `auto_target_candidate`, or
  `needs_browse` — only the last goes to the human/agent browser pass.
- Eval harness replays the pre-filter over the 2,428 audited rows
  (`state/prospects/audited/*.csv`) and reports precision/recall per class.
  Ship only if `auto_owned_site` precision ≥ 95% (a target misclassified as owned
  is a silently lost lead — that's the expensive error).

**Done.** Eval report committed under `state/artifacts/` showing measured
precision/recall; the verify-web-export flow gains a `--prefiltered` mode that
excludes auto-classified rows; measured reduction in rows-needing-browse reported.

**Guardrails.** Pre-filter never overwrites a human verdict. No edits to
`packages/schemas/` without founder approval — store pre-filter verdicts in a
sidecar state file if the schema lacks a field.

### 11. Lapsed-site cohort — the second-warmest list

**Why.** A business whose site is broken, parked, or expired already valued a
website once — warmer than never-had-one. The warehouse already stores website
fields for thousands of records; nobody has probed them for decay.

**What.** A detector pass + new cohort:
- `packages/prospecting/site_decay.py`: probe recorded website URLs for: DNS
  failure / parked-domain pages, SSL expired, 4xx/5xx, "free trial" builder
  banners (Wix/Weebly markers), HTTP-only, visibly dead (domain-for-sale
  fingerprints). Output a `decay_class` per record into a sidecar state file.
- Add cohort `L_lapsed_site` to `packages/prospecting/cohorts.py` (this file is
  NOT in the protected list, but confirm before merging; if `ProspectRecord`
  needs a new field, stop — schema edits need founder approval).
- Outreach copy angle for this cohort ("your site at <domain> is down — here's a
  working replacement we already built") added to the genre snippets.

**Done.** Probe run over all records with website fields; count of lapsed
candidates reported; cohort surfaces in existing export tooling; 20 lapsed
prospects taken through verify → demo → draft as a pilot.

### 12. New-business-registration connector — intent-rich top of funnel

**Why.** A just-registered LLC needs its first website — the highest-intent moment
in the entire market, and nobody is scanning for it in this repo. Several states
publish filings as open data.

**What.** `packages/discovery/connectors/sos_filings.py` following the existing
`Connector` protocol in `packages/discovery/connectors/`:
- Start with two easy states (Florida Sunbiz daily files, Colorado open-data API).
  Pull registrations < 30 days old, filter to consumer-facing entity-name
  heuristics (exclude holdings/realty-trust noise).
- Map into `ProspectRecord`-compatible rows (no schema changes; missing fields stay
  empty), cohort `N_new_registration`, dedupe against existing records by
  name+city.
- Respect the existing `assert_bulk_crawl_allowed` gating pattern for any
  large fetch.

**Done.** Weekly run yields ≥100 fresh sub-30-day registrations into the warehouse,
deduped, cohort-tagged; documented in the prospecting lane doc.

### 13. Ad-library connector — businesses paying for traffic with no site (optional)

**Why.** A business running Meta ads whose destination is their Facebook page has
budget AND no site — proof of willingness to spend. Highest-quality cold signal
available.

**What.** `packages/discovery/connectors/meta_ad_library.py`: query the public Meta
Ad Library API by region/category, keep advertisers whose ad destination is a
facebook.com/instagram.com URL, map to prospect rows (cohort `P_paid_no_site`).
Mark experimental; API quotas are tight — design for small daily pulls.

**Done.** 50 candidates pulled for one metro; manual spot-check confirms ≥50% are
genuine no-site advertisers.

---

## Decisions for the founder (small builds, big consequences)

### 14. Pricing restructure + upmarket pilot tier

- Package A at $50/mo is underwater at any nonzero monthly labor; either raise to
  ~$99/mo or constrain A to fully-automated deliverables only. Package C is where
  LTV lives ($8,400 Y1) — the sales motion should default-pitch B and upsell C,
  not lead with A.
- Add an annual-prepay option (2 months free) — Stripe checkout already supports
  it; one `catalog.yaml` + `payments.py` change. Cash up front matters more than
  optics at this stage.
- Pilot a Package D (~$5k setup + $750–1,500/mo) for multi-location/upmarket
  verticals (med-spa, HVAC, dental — the Conversion Lab persona library already
  has med-spa depth). Needs: multi-page demo support via Design Studio premium
  track, and the trust surface below.
- `packages/agency/catalog.yaml` is typed and renders the public pricing — small
  diffs, founder decides numbers.

### 15. Minimum trust surface (blocking for scale, cheap to fix)

Before sends reach hundreds/month: a privacy policy + terms page on the BBW site
(demo sites collect form leads — privacy policy is not optional), an IP-ownership
clause in OFFER.md (who owns the demo/final site), and the entity status
documented. One agent-day of work with founder review of the legal text.

---

## Anti-roadmap — explicitly do NOT build yet

Deferred until ≥10 paying clients or send data demands it: ESP/sending
infrastructure and domain warmup (manual sends are correct at current volume);
Google Ads / Meta Ads / GBP write APIs; review-SMS Twilio path (compliance gate
exists, keep it shut); CRM integrations (HubSpot etc.); call tracking; more
platform polish (skills, CI, repo tooling — already above the bar); **and more
demo inventory beyond confirmed send capacity** — build-on-signal replaces
build-ahead until conversion is measured.

## Sequencing logic

Send data is the highest-information artifact the company can produce. Phase 0
liquidated tooling friction; Phase 1 built the loop (replies, follow-ups, the
teaser arm). As of 2026-06-12 the machine works end to end but has produced only
~10 real sends — the experiment hasn't started. F1–F3 close the integration
seams; the Phase 2 entry criteria (≥150 demo-arm sends, ≥30 teaser-arm sends,
≥1 week of reply data) decide WHICH Phase 2 item leads. Items 9–13 stay
deliberately behind that data: automating the wrong leg of the funnel is the
only way v2 can fail as politely as v1. (Item 8 postcards: deferred by founder,
2026-06-12.)
