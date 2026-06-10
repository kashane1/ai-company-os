# Outreach Action Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Status (2026-06-10): shipped on branch `feat/outreach-action-dashboard`.**
- [x] Task 1 — `OutreachStore` (SQLite touches + overrides) + tests
- [x] Task 2 — effective-contact overlay + status auto-bump/manual-set in the lane
- [x] Task 3 — interactive `outreach_panel.py` renderer (own non-refreshing route)
- [x] Task 4 — `outreach_endpoint.py` action routes wired into `apps/api/main.py`
- [x] Task 5 — docs + index
- [x] Verification — 21 new tests + lane regression green; live render screenshotted

**Goal:** Add a localhost-only operator dashboard that turns each deployed prospect into a row of per-channel **launch buttons** (email / SMS / call / FB DM / IG DM), lets the operator **edit missing contact fields inline**, and **logs each send as an append-only touch** — feeding the existing `outreach_lane` ledger and follow-up logic. Semi-auto (draft + prefill + log) / semi-manual (the human clicks send in the native app).

**Architecture:** Extend what already exists — do **not** fork a new app.
- Reuse `packages/agency/outreach_lane.py` (the ledger), `packages/dashboard/operator.py` + `apps/api/dashboard_endpoint.py` (the renderer, served at `127.0.0.1:8765`), and `packages/agency/outreach.py` (per-channel copy).
- **Two stores, split by access pattern** (decided 2026-06-10):
  - **Scanned prospect records stay JSON** (`state/prospects/records/*.json`, ~28.9k files, atomic-write, pipeline-owned). Untouched by this work.
  - **Touches + contact-overrides go to SQLite** via the existing `packages/db/control_plane_db.py` abstraction (backend = `sqlite` default, `postgres` via `DATABASE_URL`). This is the new write-heavy, concurrent, operator-owned data. Postgres is deferred until multi-machine / second-operator / off-localhost — flip one env var, no rewrite.
- **Status model:** one scalar **rollup** `status` per prospect (deal stage) **plus** an append-only `touches` log (one row per send). First touch auto-bumps status to `CONTACTED`; operator manually sets `REPLIED`/`WON`/`LOST`.

**Tech Stack:** Python, FastAPI (existing `apps/api`), `control_plane_db` SQLite store, existing agency outreach templates, server-rendered HTML + light vanilla JS (fetch POST), platform deep-links.

---

## Hard boundaries (binding — preserves the GTM lane posture)

- **No automated sending.** Every button only **opens a prefilled draft** (Gmail compose, Messages, m.me, etc.) or **copies the draft to the clipboard**. Nothing sends without a human click inside the native app/site. This is the compliance design, not a limitation (TCPA/CAN-SPAM).
- **Touch logging is a manual confirm.** A touch is written only when the operator clicks **"✓ Log sent"** — never inferred from a Launch click (they may bail).
- **Bind to `127.0.0.1` only.** Never `0.0.0.0`. Local-only by design.
- **No edits to `packages/schemas/`, `packages/policies/`, `skills/canonical/`, `skills/registry.yaml`.** Touches/overrides live in the new store + the lane layer, so the prospect schema is untouched and **no founder approval gate is triggered**.
- **No first-person send claims** in any generated copy (existing lint stays).

## Channel deep-link mechanics (reference)

| Channel | Launch action | Enabled when | Fallback |
|---|---|---|---|
| Email | Gmail **compose-URL prefill** (`https://mail.google.com/mail/?view=cm&fs=1&to=…&su=…&body=…`) — opens a reviewable draft, **zero OAuth** | effective email present | copy body |
| SMS | `sms:+1…&body=…` → Messages.app prefilled | effective phone present **and** looks mobile (landline → greyed, call instead) | copy body |
| Call | `tel:+1…` + on-screen call script | effective phone present | script shown |
| FB DM | open `m.me/<page>` + copy draft | effective facebook present | copy |
| IG DM | open `instagram.com/<handle>` + copy draft | effective instagram present | copy |

> Gmail compose-URL prefill is primary because the FastAPI server cannot call the Claude-side Gmail MCP; the compose URL needs no server-side auth and still gives a review-then-send "draft." True Gmail-API drafts are a later optional upgrade.

---

### Task 1: Touches + Overrides Store (SQLite)

**Files:**
- Create: `packages/agency/outreach_store.py`
- Test: `tests/python/unit/test_agency_outreach_store.py`

Back it with `control_plane_db` (sqlite default / postgres via `DATABASE_URL`). Two tables:
- `outreach_touches(id, place_id, channel, sent_at, via, note)` — **append-only**; supports the same channel multiple times (follow-ups).
- `contact_overrides(place_id, field, value, updated_at)` — operator-entered contact values; one row per (place_id, field).

API: `append_touch(place_id, channel, via, note)`, `list_touches(place_id)`, `set_override(place_id, field, value)`, `get_overrides(place_id)`, `derive_status(scalar, touches)` (first touch → ≥`CONTACTED`). All writes transactional. If any legacy JSONL touches exist from the prior `log` CLI, import them once.

### Task 2: Wire Effective Contact + Touches Into The Ledger Row

**Files:**
- Modify: `packages/agency/outreach_lane.py`
- Test: `tests/python/unit/test_agency_outreach_lane.py`

In `OutreachClientRow` / `_row_for_record`, compute **effective contact** = override-or-scanned per field (override wins; scanned record never mutated). Attach `touches` and a derived rollup `status` (manual scalar still wins over the auto-bump for `REPLIED`/`WON`/`LOST`). Preserve operator-owned fields across `refresh`.

### Task 3: Dashboard Action Panel (Render)

**Files:**
- Modify: `packages/dashboard/operator.py`
- Test: `tests/python/unit/test_operator_dashboard.py`

Render each prospect as a row of per-channel controls: **[Launch]** (deep-link from Task-0 table) · **[✓ Log sent]** · **✎ inline-edit** · touch badges (`email ✓ ×2, last 6/8`) · a **status dropdown**. A channel's Launch button is **greyed/disabled** when its effective contact value is empty; the ✎ control stays active so the operator can add it. Build deep-link/clipboard payloads from `packages/agency/outreach.py` copy.

### Task 4: Action Endpoints (Write Paths)

**Files:**
- Modify: `apps/api/dashboard_endpoint.py`
- Test: `tests/python/unit/test_dashboard_endpoint.py`

Add localhost POST routes (CSRF not needed for loopback-only, but validate `place_id`):
- `POST /dashboard/outreach/touch` `{place_id, channel}` → `append_touch` + status auto-bump.
- `POST /dashboard/outreach/contact` `{place_id, field, value}` → `set_override`; response re-enables the channel button.
- `POST /dashboard/outreach/status` `{place_id, status}` → manual rollup set.

Light vanilla-JS `fetch` handlers in the rendered page; re-render the affected row on success. No SPA framework.

### Task 5: Docs + Index

**Files:**
- Modify: `docs/waas-prospecting-lane.md` (link the action dashboard; reaffirm "no automated send")
- Modify: `docs/plans/2026-06-09-outreach-operations-lane.md` (note touches/overrides now SQLite-backed, shared by CLI `log` + dashboard)
- Run: `make doc-index`

### Verification

- `make tokens-check` + `make doc-index` clean.
- Unit tests for store (append/override/derive), lane effective-contact, render (greyed vs live buttons), endpoints (touch appends, override re-enables, status set).
- Manual: launch `apps/api/server.py`, open `127.0.0.1:8765/dashboard`; confirm a prospect with no email shows a greyed Email button → add email via ✎ → button lights up → Launch opens Gmail compose prefilled → ✓ Log sent writes a touch and bumps status to CONTACTED → second send appends a second touch.
- Confirm: nothing sends without a human click; server bound to `127.0.0.1`; no `packages/schemas` diff.
