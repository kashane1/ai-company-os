# Operator Guide

A brief command reference for running `ai-company-os` work streams from your Mac.
Use this when you want to **kick off discovery, validate a niche, or route work to
agents** — not when you need architecture deep-dives (see links at the bottom).

**Last updated:** 2026-06-01 (includes `codex/realtime-control-plane`: unified operator
dashboard, Postgres control plane, optional Redis queue, discovery run/score CLIs,
web validation lane).

---

## How ready is this for a new business?

**Short answer:** the **discover → score → validate → build** loop is implemented
and operable today. You can run a niche sweep, rank wedges, gate them, ship a
landing page as the validation experiment, and hand a passed wedge to the build
lanes — mostly from the terminal plus agent sessions for the creative steps.

| Stage | Status | What you run |
|-------|--------|--------------|
| Discover pains in a niche | **Ready** | `discovery_run.py` (HN live with no creds; GitHub/Reddit need tokens) |
| Score & rank opportunities | **Ready** | `discovery_score.py` (offline heuristic or LLM analyst) |
| Validate gate / build gate | **Ready** | Policy enforced in code; see demo output |
| Web-first validation (landing page) | **Ready** | Agent + WEB lane (`packages/discovery/web_handoff.py`) |
| iOS / App Store build & ship | **Ready** | `./scripts/runtime start` + engineering/iOS/App Store workers |
| Control plane visibility | **Ready** | `python3 apps/api/main.py` → `/dashboard`, `/discovery` |
| Fully unattended discovery | **Not yet** | Runs are operator-triggered by design; no cron/queue wiring |
| GTM content loop | **Partial** | Skills + workers scaffolded; not closed-loop autonomous |

**Fastest proof (zero setup, ~10 s):**

```bash
python3 scripts/discovery_demo.py
```

**Fastest live niche sweep (HN only, no API keys):**

```bash
python3 scripts/discovery_run.py start --query "tool to automate <your niche>"
python3 scripts/discovery_score.py --top 10
```

For production-quality ranking, add `OPENROUTER_API_KEY` to `.env` and use
`--provider llm`. For two-source confidence (GitHub + HN), add `GITHUB_TOKEN`.

Deeper context: [discovery-guide.md](discovery-guide.md),
[discovery-backlog.md](discovery-backlog.md), [founder-os.md](founder-os.md).

---

## First-time setup

```bash
# 1. Python env (needed beyond the zero-dep demos)
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[test]"

# 2. Optional credentials — copy and fill what you need
cp .env.example .env
```

| Variable | Unlocks |
|----------|---------|
| *(none)* | Offline demo, HN live discovery, heuristic scoring |
| `GITHUB_TOKEN` | GitHub connector (public search) |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | Reddit connector |
| `OPENROUTER_API_KEY` | LLM analyst (`discovery_score --provider llm`) |
| `AI_COMPANY_OS_DATABASE_URL` | Postgres control plane (optional; SQLite default) |
| `AI_COMPANY_OS_QUEUE_BACKEND=redis` | Redis Streams dispatch (optional; DB remains canonical) |
| `AI_COMPANY_OS_REDIS_URL` | Redis connection when queue backend is `redis` |
| `NETLIFY_AUTH_TOKEN` | Web deploy lane (preview/production) |
| `STRIPE_SECRET_KEY` | Paid validation on landing pages (test key = no approval) |

Init Postgres when you want durable, queryable state:

```bash
docker compose -f infra/compose.yaml up -d postgres redis   # optional
export AI_COMPANY_OS_DATABASE_URL=postgresql://ai_company:ai_company@localhost:5432/ai_company_os
python3 scripts/control_plane_db.py init
```

---

## End-to-end: new niche → validation → build

A practical sequence for exploring **market edge** in a new niche:

```mermaid
flowchart LR
  A[Discovery sweep] --> B[Score inbox]
  B --> C{Validate gate}
  C -->|advance| D[Web landing experiment]
  D --> E{Experiment passed?}
  E -->|yes| F[Build goal → WEB or iOS]
  E -->|no| G[Kill + record why]
  C -->|hold| G
```

**1. Sweep the niche** (repeat `--query` for variants):

```bash
python3 scripts/discovery_run.py start \
  --query "automate invoicing for freelancers" \
  --query "etsy listing photo resize"
```

Stop mid-run: `python3 scripts/discovery_run.py stop` (or Ctrl-C).
Check last run: `python3 scripts/discovery_run.py status`.

**2. Rank what landed in the inbox:**

```bash
python3 scripts/discovery_score.py --provider heuristic --top 10   # offline first pass
python3 scripts/discovery_score.py --provider llm --top 10         # production analyst
```

**3. Review** — read the markdown report. Rows show score, confidence, and
advance/hold reasons from `evaluate_opportunity`.

**Control plane cockpit** (optional but recommended for week-long runs):

```bash
python3 apps/api/main.py
open http://127.0.0.1:8000/dashboard          # unified operator view
open http://127.0.0.1:8000/discovery          # discovery-only panel
curl -s http://127.0.0.1:8000/dashboard/data  # JSON for agents/scripts
```

`/dashboard` shows database backend health, active queue backend (`database` or
`redis`), per-lane queue depth + latest task, recent tasks/approvals/events.
`/discovery` shows ranked inbox + latest discovery run. Both have `/data` JSON
siblings for tooling (`packages/dashboard/operator.py`,
`packages/discovery/dashboard.py`).

**4. Validate the top wedge** — use an agent session (see prompts below) to:
create a `LANDING_PAGE` validation experiment, route a WEB build goal, and ship
a landing page. The build gate blocks any full build until the experiment passes.

**5. Build lanes** — when validation passes, start workers:

```bash
./scripts/runtime start
./scripts/runtime status
./scripts/runtime stop
```

The runtime supervisor manages **engineering, iOS, and App Store** loops only.
Discovery stays operator-triggered.

---

## Command reference by work stream

### Discovery (find → score → validate)

| Command | Purpose |
|---------|---------|
| `python3 scripts/discovery_demo.py` | Offline end-to-end demo (gates, scorecard example) |
| `python3 scripts/discovery_demo.py --live --query "…"` | Live HN fetch into a temp inbox |
| `python3 scripts/discovery_run.py start --query "…"` | Production sweep → persistent inbox |
| `python3 scripts/discovery_run.py status` | Latest run report |
| `python3 scripts/discovery_run.py stop` | Halt a running sweep |
| `python3 scripts/discovery_score.py` | Rank inbox (heuristic, default) |
| `python3 scripts/discovery_score.py --provider llm --top 10` | LLM analyst ranking |
| `python3 -m pytest tests/python/unit/test_discovery_*.py` | Discovery unit tests |

Run reports persist to the control plane by default (`--store db`). Use
`--store file` for zero-dependency JSON only.

### Control plane cockpit (realtime ops)

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | API + DB backend health |
| `GET /dashboard` | HTML operator cockpit (lanes, tasks, approvals, events) |
| `GET /dashboard/data` | Same view as JSON |
| `GET /discovery` | HTML discovery panel (inbox + run status) |
| `GET /discovery/data` | Same view as JSON |
| `POST /goals`, `/tasks/claim`, `/approvals` | Control-plane API (workers + agents) |

| Command | Purpose |
|---------|---------|
| `python3 apps/api/main.py` | Start API on `127.0.0.1:8000` |
| `python3 scripts/control_plane_db.py status` | DB backend + schema health |
| `python3 scripts/control_plane_db.py init` | Ensure control-plane schema |
| `python3 scripts/control_plane_db.py migrate-sqlite` | Copy SQLite → Postgres |

Start Postgres/Redis locally: `docker compose -f infra/compose.yaml up -d postgres redis`
(see [local-dev.md](../local-dev.md)).

### Platform runtime (build & ship)

| Command | Purpose |
|---------|---------|
| `make demo` | Zero-dep control-loop demo (goal → task → approval) |
| `./scripts/runtime start` | Background supervisor (engineering + iOS + App Store) |
| `./scripts/runtime status` | Supervisor health |
| `./scripts/runtime stop` | Clean shutdown |
| `python3 apps/api/main.py` | API + operator dashboard |
| `./scripts/test_python.sh` | Full Python test lane |
| `./scripts/test_ios.sh` | iOS test lane (Catchbook) |

Note: `./scripts/runtime` currently supervises **engineering, iOS, and App Store**
loops only. WEB/WEBDEPLOY workers exist but are not yet in the runtime supervisor.

### Control plane DB (optional Postgres)

| Command | Purpose |
|---------|---------|
| `python3 scripts/control_plane_db.py init` | Create schema |
| `python3 scripts/control_plane_db.py migrate-sqlite` | Copy SQLite → Postgres |
| `python3 scripts/control_plane_db.py status` | Backend health |

### Preflight

| Command | Purpose |
|---------|---------|
| `make doctor` | Local setup checklist |
| `make audit` | Doc-path drift check |

---

## Agent prompts (copy/paste into Cursor or Cowork)

Full menu with blast-radius notes: [docs/example_prompts.md](../example_prompts.md).

**Discovery sweep + rank:**

> Run a discovery sweep for "[your niche]" using `scripts/discovery_run.py`, then
> score with the LLM analyst and show me the top 5 with advance/hold reasons.

**Web-first validation for the top wedge:**

> Opportunity `[opp_id]` cleared the validate gate. Create a landing-page validation
> experiment with success criteria set before launch, hand off a WEB build goal via
> `web_handoff`, and stop at deploy approval.

**Niche research brief (GTM memory):**

> Research the niche "[niche]" and produce a structured brief — audience, pain points,
> competitors, content gaps — under `docs/products/[product-id]/gtm/`.

**Decompose a build goal:**

> Here's a founder goal: "[goal]". Decompose into typed tasks, route to the right
> lane, and tell me what needs my approval.

**After validation passes → full build:**

> Experiment `[exp_id]` passed. Record it, run `assert_ready_to_build`, generate the
> dossier, and create a build goal for `[web|ios]`.

---

## Weekly cadence (human review)

| When | Action |
|------|--------|
| Mon | Pick ≤2 wedges to validate; approve experiments |
| Tue–Thu | Run validation (landing page, outreach, concierge) |
| Fri | Pass/kill gate; write outcomes to memory |
| Anytime | `discovery_run` + `discovery_score` when exploring a new niche |
| Monthly | Review evals; retune `packages/discovery/config/scoring.yaml` |

Full operating principles: [founder-os.md](founder-os.md).

---

## Scheduled sessions (optional automation)

Markdown session specs under `scripts/scheduled/` — wire these in your agent
scheduler (Cowork, launchd, etc.):

| Session | File |
|---------|------|
| Morning briefing | `scripts/scheduled/morning_briefing_session.md` |
| Approval sweep | `scripts/scheduled/approval_sweep_session.md` |
| Evening close | `scripts/scheduled/evening_close_session.md` |
| Weekly digest | `scripts/scheduled/weekly_digest_session.md` |

---

## What still needs a product decision

Tracked honestly in [discovery-backlog.md](discovery-backlog.md):

- **OpenClaw bridge** — documented, not integrated
- **GTM closed loop** — content/scheduling scaffolded, not autonomous
- **iOS coverage gate in CI** — measured, threshold not enforced yet
- **Scheduled discovery sweeps** — deliberately deferred (on-demand is the model)

---

## Read next

- [discovery-guide.md](discovery-guide.md) — discovery layer deep dive
- [opportunity-scorecard.md](opportunity-scorecard.md) — 12-signal rubric
- [example_prompts.md](../example_prompts.md) — full agent prompt menu
- [local-dev.md](../local-dev.md) — Postgres, Redis, Codex, Xcode setup
- [cowork-capabilities.md](cowork-capabilities.md) — Cowork-specific reference
- [REPO_MAP.md](../../REPO_MAP.md) — 60-second repo orientation
