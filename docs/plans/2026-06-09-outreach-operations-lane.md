# Outreach Operations Lane Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a durable, human-gated cold outreach lane for deployed Cohort A prospects.

**Architecture:** Keep this repo as the outreach brain, not the sending CRM. Store runtime status under `state/prospects/outreach-lane/`, generate drafts and next actions locally, and leave outbound sending/manual messages human-gated until a later CRM adapter is approved.

**Tech Stack:** Python dataclasses, JSON/JSONL/Markdown state files, existing prospect records, existing agency outreach templates, control-plane worker conventions.

---

### Task 1: Ledger Package

**Files:**
- Create: `packages/agency/outreach_lane.py`
- Test: `tests/python/unit/test_agency_outreach_lane.py`

Build a ledger over `A_gold` records with `mockup_url`, preserving operator-owned fields across refreshes. Default `v2-bespoke` rows to `ready_to_send`; default template-only rows to `needs_bespoke`.

### Task 2: Operator CLI

**Files:**
- Create: `scripts/agency/outreach_lane.py`
- Modify: `scripts/agency/README.md`
- Test: `tests/python/unit/test_agency_outreach_lane.py`

Expose `refresh`, `list`, and `log` commands. `log` records a manual touch in JSONL and updates the ledger; it must never send.

### Task 3: Worker Shell

**Files:**
- Create: `apps/worker-outreach/main.py`
- Create: `apps/worker-outreach/outreach/runner.py`
- Create: `apps/worker-outreach/outreach/__init__.py`
- Create: `apps/worker-outreach/README.md`
- Modify: `packages/schemas/task_packet.py`
- Modify: `apps/runtime-supervisor/supervisor/specs.py`
- Test: `tests/python/unit/test_outreach_worker.py`
- Test: `tests/python/unit/test_default_worker_specs_api.py`

Add a task-claiming worker lane for refresh/draft/log/reconcile operations. The worker may draft and update local state, but outbound send task types fail closed.

### Task 4: Docs And Generated State

**Files:**
- Modify: `docs/waas-prospecting-lane.md`
- Modify: `state/README.md`
- Generate: `state/prospects/outreach-lane/client-status.json`
- Generate: `state/prospects/outreach-lane/client-status.md`

Document the operator list location and the manual-send boundary.

### Verification

Run:

```bash
pytest tests/python/unit/test_agency_outreach_lane.py tests/python/unit/test_outreach_worker.py tests/python/unit/test_default_worker_specs_api.py -q
python scripts/agency/outreach_lane.py refresh
python scripts/agency/outreach_lane.py list --status ready_to_send
```
