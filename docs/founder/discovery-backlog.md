# Backlog — discovery layer + adjacent platform gaps

Updated 2026-05-30. Sections A, B, C (the discovery loop and its platform wiring)
are now **built and tested**. What remains is (D) pre-existing platform gaps that
need product decisions, plus (E) newly discovered follow-ups surfaced while
building A–C. Priorities: **P0** = needed before trustworthy daily use,
**P1** = makes it genuinely automated, **P2** = scale/depth.

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
| D1 | Postgres for the control plane | P1 | Control plane still defaults to SQLite. The new stores already work on both backends (they go through `ControlPlaneDatabase`), so this is a config/ops cutover, not a code rewrite. |
| D2 | Redis queue | P2 | Replace the durable queue table once worker daemons run continuously. |
| D3 | Operator dashboard | 🟡 | First panel scaffolded: a read-only **discovery view** (ranked inbox + run status/history) — `packages/discovery/dashboard.py` (view builder + HTML render) served at `GET /discovery` and `/discovery/data` via `apps/api/discovery_endpoint.py`. Remaining dashboard panels (goals/tasks/approvals) still deferred. |
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
   The full find→score→gate loop is now operable from the terminal (pair it with
   a real `OPENROUTER_API_KEY` for the `llm` provider).
2. ~~**E3 — persist run history to the control plane**~~ ✅ done — runs now live
   alongside the opportunity/experiment records (`--store db`, queryable history).
3. The remaining **D** platform items (Postgres cutover, Redis, dashboard,
   OpenClaw, iOS coverage) on their own timeline — these are larger product calls
   that each need a deliberate decision; pick one to take next.
