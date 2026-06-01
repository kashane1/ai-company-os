# Backlog — discovery layer + adjacent platform gaps

Updated 2026-06-01. Sections A, B, C (the discovery loop and its platform wiring)
and section F (web build + ship lane) are **built and tested**. What remains is
(D) pre-existing platform gaps that need product decisions, plus (E) follow-ups.
Priorities: **P0** = needed before trustworthy daily use, **P1** = makes it
genuinely automated, **P2** = scale/depth.

Suggested ticket form: `todos/NNN-todo-PRIORITY-<slug>.md` (see
[todos/README.md](../../todos/README.md)).

## A. Discovery loop — DONE ✅

| # | Item | Status | Landed in |
|---|------|--------|-----------|
| A1 | Analyst `SignalProvider` (heuristic + agent seam) | ✅ | `packages/discovery/analyst.py` |
| A2 | Opportunity store in the control-plane DB | ✅ | `packages/db/opportunity_store.py` |
| A3 | Experiment store + lifecycle state machine | ✅ | `packages/db/experiment_store.py` |
| A4 | Dossier generation step | ✅ | `packages/discovery/dossier.py` |
| A5 | Semantic dedup behind an `EmbeddingProvider` | ✅ | `packages/discovery/semantic.py` |
| A6 | Funnel + source-yield metrics | ✅ | `packages/discovery/evals.py` |

## B. Platform wiring — DONE ✅

| # | Item | Status | Landed in |
|---|------|--------|-----------|
| B1 | On-demand discovery run (human start/stop) + CLI | ✅ | `packages/discovery/run.py`, `scripts/discovery_run.py` |
| B2 | Build gate enforced before handoff (`assert_ready_to_build`) | ✅ | `packages/discovery/handoff.py` |
| B3 | Opportunity → goal projection | ✅ | `packages/discovery/handoff.py` |
| B4 | End-to-end integration test (run→score→gate→handoff, incl. stop) | ✅ | `tests/python/integration/test_discovery_loop.py` |
| B5 | (Optional) scheduled sweep | ⏸ P2 | deferred by choice — on-demand is the model |

## C. Compliance & approvals — DONE ✅

| # | Item | Status | Landed in |
|---|------|--------|-----------|
| C1 | `bulk_crawl` approval gate | ✅ | `assert_bulk_crawl_allowed` in `discovery_gates.py` |
| C2 | httpx-backed robots fetcher for HTML connectors | ✅ | `RobotsPolicy.from_httpx` in `connectors/robots.py` |
| C3 | Outreach gate for sending experiments | ✅ | `assert_outreach_ready` in `discovery_gates.py` |

## D. Pre-existing platform gaps (need a product decision)

These predate the discovery work and are large/architectural — listed so the
backlog stays honest about the whole repo. I did **not** build these; several are
deliberately deferred choices the README documents.

| # | Item | Pri | Note |
|---|------|-----|------|
| D1 | Postgres for the control plane | ✅ | `ControlPlaneDatabase` now exposes backend/schema health, redacts Postgres DSNs, creates hot-path indexes, and has `scripts/control_plane_db.py` for init/status/SQLite→Postgres migration. SQLite remains the fallback. |
| D2 | Redis queue | ✅ | `TaskQueue` now selects `database` (default) or `redis` via `AI_COMPANY_OS_QUEUE_BACKEND`. Redis Streams dispatch is opt-in; the DB remains canonical for task records. |
| D3 | Operator dashboard | ✅ | Unified read-only cockpit at `GET /dashboard` + `/dashboard/data` covering DB/queue status, lanes, tasks, approvals, and events. The existing `/discovery` panel remains available. |
| D4 | Broaden approval *persistence* | P1 | C1/C3 added the gate *logic*; wiring those decisions into the `approvals` store + approval-reviewer surface (so they're recorded/replayable like task/release approvals) is the remaining half. |
| D5 | OpenClaw bridge | P2 | Documented as optional/future; no integration code, by design. |
| D6 | Gate iOS coverage | P2 | iOS coverage measured but not enforced. Small CI change, but flip it deliberately. |

## E. Newly discovered (surfaced while building A–C)

| # | Item | Status / Pri | Notes |
|---|------|--------------|-------|
| E1 | Wire the analyst into a real model call | ✅ | `LLMSignalProvider` + `packages/tools/llm` (OpenRouter `ChatModel`, strict-JSON scorecard prompt, insufficient-evidence escape). |
| E2 | One source of truth for the inbox | ✅ | `OpportunityRepository` seam: JSON default, DB store when configured, `migrate_opportunities` for the cutover (`packages/discovery/storage.py`). |
| D4 | Persist gate decisions to approvals store | ✅ | `GateDecisionRecorder` records bulk-crawl + outreach decisions as `ApprovalRecord`s (`packages/discovery/gate_audit.py`). |
| E4 | Reddit connector (OAuth) | ✅ | `RedditConnector` — app-only OAuth, token caching, registered + enabled (`connectors/reddit.py`). **Needs runtime creds** (see below). |
| E5 | Call C1/C3 gates at the point of action | ✅ | Bulk runs gated in `run_discovery` (`FetchOptions.authorized` only set after the gate passes); `start_sending_experiment` gates outreach before an experiment goes live. |
| E7 | Analyst calibration eval | ✅ | `packages/discovery/calibration.py` + a canonical labelled dataset; 100% against the heuristic provider as a drift tripwire. |
| E3 | Persist `DiscoveryRunReport` to the control plane | ✅ | `DiscoveryRunRecordStore` (`packages/db/discovery_run_store.py`) + a `discovery_runs` table; `DiscoveryRunRepository` seam makes the file/DB stores interchangeable, `migrate_runs` does the cutover, and `discovery_run --store {db,file}` (db default) makes runs queryable alongside opportunity/experiment records. |
| E6 | Backfill 3.11 compatibility note | P2 | Repo targets 3.12 (`datetime.UTC`); the new discovery code is 3.10-safe. One-line note if 3.10 support is ever wanted. |
| E8 | `discovery_score` CLI | ✅ | `scripts/discovery_score.py` — runs the scoring pass with a chosen `SignalProvider` (`heuristic` default / `llm`), prints a ranked markdown report. |

### Manual step: Reddit + model credentials (runtime)

The code is done; these just need values in `.env` (see `.env.example`):

- **Reddit** — create a *script* app at `https://www.reddit.com/prefs/apps`
  (redirect uri `http://localhost:8080`); copy the client id (under the app name)
  and secret into `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`. (Reddit is blocked
  by the browser tool's safety rules, so this can't be automated — it's a 1-minute
  manual step.)
- **OpenRouter** — `OPENROUTER_API_KEY` for the `LLMSignalProvider`.
- **GitHub** — `GITHUB_TOKEN` for the GitHub connector.

## Suggested next three

1. ~~**E8 — `discovery_score` CLI**~~ ✅ done — `scripts/discovery_score.py`.
2. ~~**E3 — persist run history to the control plane**~~ ✅ done.
3. ~~**F — web build + ship lane**~~ ✅ done — Astro scaffold, Netlify deploy,
   web-first validation handoff, Stripe paid validation.
4. **Pick one D item deliberately** — OpenClaw bridge (D5), iOS coverage gate
   (D6), or GTM closed loop (Phase 2.2, tracked elsewhere). Postgres (D1),
   Redis (D2), and the operator dashboard (D3) are already shipped.

## Audit note (2026-06-01)

The platform can **discover → score → validate → build (web or iOS) → ship**
end to end, with shared policy gates throughout. The web lane closes the
fastest path from a scored wedge to a real customer-facing validation page.
Remaining gaps: (1) discovery is operator-triggered, not queued/scheduled;
(2) GTM task types are scaffolded but not a closed autonomous loop; (3) OpenClaw
is optional and unwired; (4) iOS coverage is measured but not CI-gated. Operator
entry point: [`operator-guide.md`](operator-guide.md).

## F. Web build + ship lane — DONE ✅

_Added 2026-05-30 after a repo-wide capability audit; implemented same day._

**Why.** Before section F, the only customer-facing ship lane was **iOS**
(App Store review). That is slow and overkill for validating demand. The **WEB**
and **WEBDEPLOY** lanes add a portable, fast path: landing pages, waitlists, and
paid validation before committing to a full app build.

**The case for it (assessment).** A web target is a strong fit, for three reasons:

1. **Faster, lower-friction validation than the App Store.** No review queue, no
   signing, instant deploys, instant iteration. You can be in front of real
   traffic the same day an opportunity clears scoring.
2. **It doubles as a validation experiment.** The discovery loop already has an
   experiment store + an outreach gate (C3), and `assert_ready_to_build` requires
   a *passed* validation experiment before any build goal is created. A landing
   page with a waitlist/CTA is the cheapest possible demand test — so the web lane
   isn't just another ship target, it **feeds the gate the loop already enforces**.
   Web-first validation → then commit to an app (or a fuller web app) only for
   wedges that convert.
3. **The architecture already accommodates it cleanly.** Codex is
   target-agnostic (it edits files from a markdown packet; lane-specific checks
   live in the worker). `opportunity_to_goal` is target-agnostic too. And
   `docs/architecture.md` already names "production deploys" and "domain or DNS
   modifications" as approval-required — the policy intent for web deploys is
   now enforced via `packages/policies/deploy_readiness.py` and the WEBDEPLOY lane.

**Cautions / guardrails (baked into the tickets below).**

- Deploys are public and effectively irreversible, so **production deploy + custom
  domain/DNS are approval-gated**; per-PR preview deploys can be ungated.
- Keep **build and deploy as separate lanes**, mirroring the deliberate iOS↔App
  Store split.
- **Scope discipline:** start *static-first* (landing pages, waitlists, simple
  marketing/SaaS sites) before full web apps with backends, auth, or payments.
- Hosting **spend** and secrets are gated like other high-spend/external actions.

### Tickets — ✅ all implemented + tested (2026-05-30)

| # | Item | Status | Landed in |
|---|------|--------|-----------|
| F1 | Web lane primitives | ✅ | `WorkerLane.WEB`/`WEBDEPLOY`, `ProductPlatform.WEB`, `TestLane.WEB`, `ProductArtifactType.WEB_ARCHITECTURE`; supervisor `plan_goal` routes web-build → WEB and deploy/publish → the gated WEBDEPLOY lane (`apps/worker-supervisor/main.py`). |
| F2 | Web implementation worker + gate | ✅ | `apps/worker-web/` + `packages/web/validation.py` (build, internal-links, assets, **responsive viewport**, baseline a11y) and `packages/web/build.py` (npm ci/build behind an injectable runner). |
| F3 | Astro scaffold + artifact chain + skill | ✅ | `packages/web/scaffold/astro-landing/` (polished, mobile-first, fluid `clamp()` type, `auto-fit` grids, dark-mode, reduced-motion) + `packages/web/scaffold.py`; `landing-page-build` skill registered. |
| F4 | Web deploy lane + `DeployTarget` seam | ✅ | `packages/web/deploy.py` (`DeployTarget` + `NetlifyDeployTarget`, account abstraction for handoff) + `apps/worker-webdeploy/`. Netlify first adapter (free tier permits commercial use). |
| F5 | Deploy + DNS approval gates | ✅ | `packages/policies/deploy_readiness.py`: preview ungated; production needs validated build + reviewed preview + approval; custom-domain/DNS + spend each gated. New `PolicyViolationCode`s. |
| F6 | Web-first validation handoff | ✅ | `packages/discovery/web_handoff.py`: ships a landing page as the `LANDING_PAGE` validation experiment + a WEB-routed build goal — feeds the existing build gate. `BuildTarget` enum. |
| F7 | Web UX audit skill | ✅ | `packages/web/ux_audit.py` scores responsive / a11y / performance / SEO (Lighthouse-flavored, static); `web-ux-audit` skill registered. |
| F8 | Stripe monetization + paid validation | ✅ | `packages/web/stripe_monetization.py` (live-mode gate, FAKE_DOOR paid-validation experiment, checkout→pass/fail) + Stripe Checkout/webhook Netlify functions in the scaffold. |

**Build order used:** F1 → F2 → F3 → F4 → F5 → F6 → F7 → F8, each its own commit
with unit tests. The discovery synergy (F6 + F8) means a single landing page is
both the thing the WEB lane builds *and* the validation experiment the build gate
reads — ship a page that can take money, measure intent, then commit to a fuller
build only for wedges that convert.

> Implementation note: the new platform code is Python-3.10-safe and fully
> unit-tested (102 tests green). The worker *runtime loops* follow the existing
> engineering/iOS worker pattern and so share their `datetime.UTC` (3.12)
> requirement — not exercised in a 3.10 sandbox, same as the other workers.

**Decided (2026-05-30):** framework = **Astro static-first** (Next.js for graduating
wedges); host = **Netlify** as the first `DeployTarget` adapter (chosen over Vercel
because Netlify's free tier permits commercial use); monetization = **Stripe**
(hosted Checkout + Netlify webhook). Business scope = **own products first, deploy
lane designed so client/agency handoff is possible later** (ownership transfer +
recurring billing). These are revisable, but they're the working defaults for F.
