# Preflight for agents

Read this before mutating anything in this repo. It encodes the
boundaries every Claude and Codex session is expected to respect.

## Read first (in this order)

1. [REPO_MAP.md](../REPO_MAP.md) — five-zone orientation
2. [CLAUDE.md](../CLAUDE.md) — Claude-facing project pointers
3. [AGENTS.md](../AGENTS.md) — agent boundaries (links to [docs/agent-model.md](agent-model.md))
4. [docs/skills-index.md](skills-index.md) — full skill catalog and trigger-phrase routing

Then read the lane-specific doc for whatever you're about to touch:

- engineering work → [docs/engineering-flow.md](engineering-flow.md) + [docs/codex-worker.md](codex-worker.md)
- iOS work → [docs/ios-lane.md](ios-lane.md)
- App Store work → [docs/appstore-lane.md](appstore-lane.md)
- web / agency work (prospects, demo sites, client sites, retainer ops) → [docs/agency/README.md](agency/README.md) — the lane map; routes to the prospecting lane, demo playbook, client lifecycle, and the three build paths
- approval changes → [docs/approval-policy.md](approval-policy.md) + [docs/approval-flow.md](approval-flow.md)
- skill changes → [skills/WIRING.md](../skills/WIRING.md) + [skills/spec.md](../skills/spec.md)

## Default-safe areas

These can be edited within the bounds of the task you were given,
without per-edit approval:

- `docs/` excluding `docs/products/<product-id>/` (see below)
- `docs/handoffs/` (write a new dated handoff at session end)
- `docs/plans/` (add new plan files; see [docs/plans/INDEX.md](plans/INDEX.md))
- `todos/` (file/rename a working ticket; see [todos/README.md](../todos/README.md))
- `README.md`, `AGENTS.md`, `CLAUDE.md` for additive, minimal changes
- `REPO_MAP.md` for minor corrections
- `apps/` README files only — not the worker Python implementation

## Explicit-approval areas

Do not edit these without explicit founder approval in the same turn:

- `packages/policies/` — shared policy code (approvals, testing, release readiness, skill evolution, etc.)
- `packages/schemas/` — typed contracts (task, task_run, approval, release, postmortem, etc.)
- `skills/canonical/` — source of truth for every skill
- `skills/adapters/` — runtime translations of canonical skills
- `skills/registry.yaml` — the skill index
- `.github/workflows/` — CI gates
- `infra/` — registries, launchd plists, fastlane configs
- `Makefile` for behavior-changing targets (additive helpers are fine)
- Existing schema-backed JSON files anywhere under `state/checkpoints/`

If a task seems to require one of these and you weren't told to touch it,
**stop and ask** before editing.

## Forbidden areas (do not inspect or edit)

- `products/<product-id>/` — managed iOS product source. Out of scope for
  every root-scaffolding task. Touch only when the task is explicitly
  product implementation work in the iOS lane.
- `state/` — runtime-owned. Source files never live here. Only the
  writer code listed in [state/README.md](../state/README.md) writes
  here, and only at runtime.
- `.claude/skills/` — discovery pointers only. Never add skill logic.
  Edit the canonical source or the adapter instead.
- `.claude/commands/` — operator-owned slash commands.
- `.claude/settings.json`, `.claude/settings.local.json`,
  `.claude/hooks/` — operator-owned environment configuration.
- `.local` (if present) — private operator surface.
- `.codex/` — Codex desktop/app-local session metadata. Gitignored.
- Per-user Xcode UI state (`xcuserdata/`, `*.xcuserstate`).

## Product-app scope rule

Three managed iOS products live under `products/` (see [infra/products.json](../infra/products.json)).
Their source is **out of scope** for any root-scaffolding task.

Acceptable interactions with `products/`:

- read `infra/products.json` for the product registry
- read `docs/products/<product-id>/` for product planning artifacts
  **only** if the task explicitly requires it
- never open Swift/Objective-C files
- never run product builds or product tests

If a doc-fix touches a product reference, prefer the path in
`infra/products.json` (`source_path`) as the ground truth. Don't invent
new product paths.

## Generated-file rule

These are written by tooling and must never be hand-edited:

- everything under `state/`
- everything under `build/` (created by test runners and CI scripts)
- everything under `__pycache__/`, `.venv/`, `.pytest_cache/`,
  `.mypy_cache/`
- per-skill `fixtures/` files are tooling-owned — edit only via the
  fixture-emit workflow documented alongside the skill

## `.local` rule

If you see a file or directory named `.local` or ending in `.local.md`,
treat it as a private operator surface. Do not inspect, do not edit, do
not regenerate. The repo's existing `compound-engineering.local.md` at
root is configuration for a third-party review tool; leave it alone.

## `.claude/skills` pointer rule

Every file under `.claude/skills/` is a thin routing pointer with:

- frontmatter (`description`, `canonical_source`, `adapter_source`)
- a one-line instruction to read and follow the adapter

The skill logic lives in `skills/canonical/<id>/` (source of truth) and
is translated by `skills/adapters/<runtime>/<id>.md`. If you need to
change a skill's behavior, edit the canonical definition and the
adapter — never the project skill pointer.

If the project skill's `description:` drifts from the adapter's
`description:`, the project skill is what needs syncing, per
[skills/WIRING.md](../skills/WIRING.md).

## How to end a session cleanly

1. Make sure every file you touched is intentional. Run `git status --short`.
2. If the worktree is dirty, write a handoff under `docs/handoffs/`
   following the convention in [docs/handoffs/INDEX.md](handoffs/INDEX.md).
3. Do not commit on the founder's behalf unless they explicitly asked.
4. Do not push.
5. Surface anything you noticed but did not fix (broken refs, stale docs,
   unused files) in your final summary — don't bury it.

## When to stop and ask the founder

- The task seems to require editing a forbidden area.
- The task seems to require editing an explicit-approval area you weren't
  scoped to touch.
- A canonical skill, schema, or policy file would need to change to
  complete the work.
- You found drift wider than the task (e.g. a doc references a file
  that doesn't exist anywhere). Report it; do not improvise a rewrite.
- A "simple" rename would touch more than one zone (e.g. renaming a
  product would touch `infra/products.json`, `docs/`, `products/`, and
  `state/` simultaneously — that's a founder-scoped change).
- A check or test reports something you can't explain.
- You're about to take any action against a remote (push, PR, App Store,
  TestFlight, network).

The cost of stopping to confirm is low. The cost of a wrong
irreversible action is high.
