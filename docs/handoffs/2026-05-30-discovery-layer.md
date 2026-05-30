# Handoff — discovery layer (2026-05-30)

Added a full **discovery layer** (find → score → validate *what* to build) as a
shared platform package, feeding the existing build lanes. All work is **tested
and lint-clean but uncommitted** (see commit plan below).

## What changed

- **Schemas** (`packages/schemas/`): `opportunity.py` (12 signals + evidence),
  `experiment.py` (validation test + success criteria + lifecycle), `dossier.py`.
- **Discovery package** (`packages/discovery/`): connectors (HN, GitHub, Reddit)
  behind one contract with robots.txt + rate-limit compliance; deduped
  opportunity `inbox.py`; `scoring.py` (12-signal scorecard); `scoring_pass.py`
  (rank the inbox); `analyst.py` (heuristic + `LLMSignalProvider`); `storage.py`
  (JSON or DB backend); `run.py` (on-demand, stoppable runs); `handoff.py`
  (opportunity → goal, gate-enforced); `dossier.py`, `evals.py`, `semantic.py`,
  `calibration.py`, `gate_audit.py`.
- **Policy** (`packages/policies/discovery_gates.py`): validate gate, build gate
  (`assert_ready_to_build`), bulk-crawl gate, outreach gate. New
  `PolicyViolationCode` members added to `approvals.py`.
- **DB**: `opportunity_store.py`, `experiment_store.py` + two tables in
  `control_plane_db.py`/`contracts.py` (additive, SQLite + Postgres).
- **Model client** (`packages/tools/llm/`): `ChatModel` protocol + `OpenRouterClient`.
- **Scripts**: `scripts/discovery_demo.py`, `scripts/discovery_run.py`.
- **Docs**: `docs/founder/` (discovery-guide, founder-os, opportunity-scorecard,
  discovery-evals, discovery-compliance, discovery-backlog); `docs/example_prompts.md`;
  updated `README.md`, `REPO_MAP.md`, `AGENTS.md`, `docs/agent-model.md`,
  `docs/architecture.md`, `docs/README.md`, `.env.example`.
- **Tests**: 17 discovery test files (135 tests) under `tests/python/unit/` +
  `tests/python/integration/test_discovery_loop.py`.

## What is open

- Backlog E3 (persist run history to control plane), E6 (3.11 note), E8
  (`discovery_score` CLI), and the D platform items (Postgres cutover, Redis,
  dashboard, OpenClaw, iOS coverage gating). See `docs/founder/discovery-backlog.md`.

## What is blocked

- **Reddit + model credentials** — code is done; needs runtime values in `.env`
  (`REDDIT_CLIENT_ID/SECRET`, `OPENROUTER_API_KEY`, `GITHUB_TOKEN`). Reddit app
  registration could not be automated (reddit.com is blocked by the browser
  tool's safety rules) — it's a 1-minute manual step at reddit.com/prefs/apps.

## What is stale

- Nothing known. Structural docs were updated this session to reference discovery.

## Files touched

See `git status` (45 entries). New: `packages/discovery/**`, `packages/tools/llm/**`,
`packages/schemas/{opportunity,experiment,dossier}.py`,
`packages/db/{opportunity_store,experiment_store}.py`,
`packages/policies/discovery_gates.py`, `scripts/discovery_*.py`,
`tests/python/**/test_discovery_*`, `docs/founder/**`, `docs/example_prompts.md`.
Modified: `README.md`, `REPO_MAP.md`, `AGENTS.md`, `docs/{README,architecture,agent-model}.md`,
`packages/policies/approvals.py`, `packages/db/{contracts,control_plane_db}.py`,
`packages/config/settings.py`, `.env.example`.

Not mine (pre-existing, leave out of discovery commits):
`products/life-clock-ios/UITests/AppStoreScreenshotsRecon.swift`,
`.claude/settings.local.json`.

## Validation run

- `ruff check` on all new/changed files — clean.
- Discovery suite: **135 passed**, ~94% line coverage on the new code.
- Full collectable repo suite: **578 passed**, 0 new failures. (5 failures + 29
  collection errors are a pre-existing Python 3.10-vs-3.12 `datetime.UTC` issue in
  worker/supervisor modules not touched here; they pass on the repo's real 3.12.)
- `scripts/discovery_demo.py` runs end to end offline.

## Exact next action — commit plan

The work is on branch `submission-prep-life-clock` (unrelated). Move it to its own
branch and commit in logical chunks, **excluding** the two not-mine files above.
Run locally (the sandbox's `.git` is not writable):

```bash
git stash push -- products/life-clock-ios/UITests/AppStoreScreenshotsRecon.swift   # set aside unrelated change
git checkout main && git pull
git checkout -b feat/discovery-layer

# 1. schemas + scoring core
git add packages/schemas/opportunity.py packages/schemas/experiment.py packages/schemas/dossier.py \
        packages/discovery/__init__.py packages/discovery/scoring.py packages/discovery/config \
        packages/policies/discovery_gates.py packages/policies/approvals.py \
        tests/python/unit/test_discovery_schemas.py tests/python/unit/test_discovery_scoring.py
git commit -m "feat(discovery): opportunity/experiment/dossier schemas + 12-signal scoring + gates"

# 2. connectors + compliance + inbox + storage
git add packages/discovery/connectors packages/discovery/inbox.py packages/discovery/storage.py \
        packages/db/opportunity_store.py packages/db/experiment_store.py \
        packages/db/contracts.py packages/db/control_plane_db.py packages/config/settings.py \
        tests/python/unit/test_discovery_compliance.py tests/python/unit/test_discovery_connectors.py \
        tests/python/unit/test_discovery_reddit.py tests/python/unit/test_discovery_inbox.py \
        tests/python/unit/test_discovery_storage.py tests/python/unit/test_discovery_stores.py
git commit -m "feat(discovery): HN/GitHub/Reddit connectors, inbox dedup, DB stores"

# 3. scoring pass, analyst, model client, run controller, handoff, dossier, evals, semantic, calibration, gate audit
git add packages/discovery/scoring_pass.py packages/discovery/analyst.py packages/tools/llm \
        packages/discovery/run.py packages/discovery/handoff.py packages/discovery/dossier.py \
        packages/discovery/evals.py packages/discovery/semantic.py packages/discovery/calibration.py \
        packages/discovery/gate_audit.py scripts/discovery_demo.py scripts/discovery_run.py \
        tests/python/unit/test_discovery_scoring_pass.py tests/python/unit/test_discovery_analyst.py \
        tests/python/unit/test_discovery_llm_analyst.py tests/python/unit/test_llm_client.py \
        tests/python/unit/test_discovery_run.py tests/python/unit/test_discovery_dossier_evals.py \
        tests/python/unit/test_discovery_semantic.py tests/python/unit/test_discovery_calibration.py \
        tests/python/unit/test_discovery_gate_audit.py tests/python/unit/test_discovery_gate_wiring.py \
        tests/python/unit/test_discovery_compliance_gates.py tests/python/integration/test_discovery_loop.py
git commit -m "feat(discovery): scoring pass, LLM analyst, on-demand runs, gate wiring, calibration"

# 4. docs
git add README.md REPO_MAP.md AGENTS.md docs/README.md docs/architecture.md docs/agent-model.md \
        docs/founder docs/example_prompts.md docs/handoffs/2026-05-30-discovery-layer.md .env.example
git commit -m "docs(discovery): guides, backlog, example prompts, structural-doc updates"

./scripts/test_python.sh        # confirm green on 3.12
# open a PR from feat/discovery-layer; do not push without your review
```

(Adjust grouping to taste. The point is a readable, chunked history rather than one mega-commit.)

## Resume prompt

> Pick up the discovery layer: add `OPENROUTER_API_KEY` and the Reddit creds to
> `.env`, then build E8 (`scripts/discovery_score.py`) so the full
> find → score → gate loop runs from the terminal with the real LLM analyst.
