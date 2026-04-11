---
id: codex-claude-handoff
name: Codex-Claude Handoff
purpose: Select, dispatch, monitor, review, and apply bounded code-change tasks from Claude to Codex via the ai-company-os engineering lane.
owner_agent: any
target_runtimes: [claude, codex]
stage: active
inputs:
  - either a specific task description the user provided, OR a directive to pick tasks from the backlog
  - the target product (default: catchbook unless the user specifies another)
  - the target repo (default: ai-company-os unless another is in infra/repos.json and has a synced managed clone)
outputs:
  - one or more enqueued task records in the control plane
  - a worktree, diff, task run record, and codex_last_message.md per dispatched task
  - applied source changes (if user approves the diff)
  - updated backlog entries marking completed items done
allowed_edit_boundaries:
  - state/artifacts/
  - state/checkpoints/platform/tasks/
  - docs/products/<product-id>/backlog.md (for marking items done)
  - products/<product-id>/ (for applying approved diffs)
forbidden_areas:
  - packages/policies/
  - packages/schemas/
  - infra/
dependencies:
  - ai-company-os monorepo layout
  - runtime-supervisor LaunchAgent installed and running
  - .venv present at repo root with pyyaml installed
  - codex CLI authenticated on the host
validation_steps:
  - runtime-supervisor-status.json shows state=running before dispatch
  - managed repo exists at state/repos/<repo-id>/
  - each dispatched task results in a task run record under state/checkpoints/platform/task_runs/
  - diff review confirms only expected files changed
handoff_contract:
  what_is_handed_off: a task packet rendered into a worktree; executed via codex exec; reviewed diff applied to source
  handed_to: codex (for execution), back to claude (for review + apply)
claude_adaptation_notes: |
  This is the primary skill Claude uses when the user asks to dispatch, delegate,
  hand off, queue, or send work to Codex. See the Claude adapter for the exact
  tool-by-tool procedure.
codex_adaptation_notes: |
  Codex does not read this skill directly. The engineering worker renders the
  task packet using bounded-codex-implementation, and the packet IS the prompt
  Codex receives via `codex exec`.
---

## Operating protocol

This skill has one job: turn a backlog item (or a user-described change) into an executed, reviewed, applied code change via Codex, with every step observable in `state/`.

The protocol runs in five phases. Do not skip any phase. If a phase fails, stop and report — do not silently fall back.

### Phase 1 — Select

Two entry modes:

**Mode A — user named the work explicitly** ("hand this fix to codex", "have codex add X to Y"):
- Confirm the change is small enough to be "bounded": one file ideally, at most two or three closely related files. If the scope is larger, propose splitting into multiple tasks before continuing.
- Confirm the change is a code change, not a design/product/research question. If the user is asking for a decision, this is the wrong skill — respond in-conversation instead.

**Mode B — user asked you to pick** ("find a few tasks for codex", "what's ready to dispatch"):
- Read `docs/products/<product-id>/backlog.md`, default `docs/products/catchbook/backlog.md`.
- From the **Build Now** section only, select items tagged `ios_feature`, `ios_bugfix`, or `engineering_change`.
- Exclude items that are blocked on an upstream `product_decision`.
- Prefer items scoped to one file. Prefer items where the target file already exists in the repo.
- Propose 1–3 candidates with a one-line reason each. Ask the user to confirm before proceeding. Do not dispatch multiple tasks without explicit approval.

### Phase 2 — Pre-flight

Before writing any task packet, verify the runtime is healthy. If any check fails, stop and tell the user what to fix.

1. Read `state/checkpoints/platform/runtime-supervisor-status.json`. `state` must be `running`. If stopped, tell the user to run `launchctl kickstart -k gui/$(id -u)/com.ai-company-os.runtime-supervisor` and wait.
2. Confirm `infra/repos.json` lists the target repo and that `state/repos/<repo-id>/` exists. If the repo isn't synced, the managed-repo sync step needs to run first — flag this and stop.
3. Read each target file named in the task scope. Confirm it exists and note any existing functions, types, or helpers Codex should reuse rather than duplicate.
4. Check `.venv/bin/python` exists. If not, the enqueue step will fail — tell the user to recreate the venv.

### Phase 3 — Dispatch

For each selected task, construct a task packet and enqueue it.

**Constraints every packet must include:**
- "Operate only inside the managed worktree."
- "Edit only <explicit list of allowed files>."
- "Do not modify packages/policies/, packages/schemas/, infra/, or docs/."
- "Leave all changes uncommitted for manual inspection."
- Any task-specific "do not duplicate X, reuse Y" or "do not touch allowlist Z" rules that protect existing invariants.

**The summary field must include:**
- Objective in one paragraph
- Acceptance criteria as plain sentences (not a checklist)
- Any existing code path / helper Codex should reuse

**Enqueue mechanism:** use `ControlPlaneService.create_goal` + `create_task_for_goal`. The user runs the Python from the repo root with `.venv` activated. Capture the returned `task_id` — this is the key for every later step.

**Never edit `state/checkpoints/platform/tasks/*.json` directly.** Those files are snapshots written by the control plane, not the queue itself. Writing JSON there does nothing.

### Phase 4 — Monitor and review

Once enqueued, the supervisor claims the task and invokes `codex exec` via subprocess. Codex runs headlessly — it does not appear in the Codex GUI. Expected artifacts when the run completes:

- `state/worktrees/<repo-id>/<task-id>/` — full worktree with changes
- `state/worktrees/<repo-id>/<task-id>/TASK_PACKET.md` — the prompt Codex received
- `state/worktrees/<repo-id>/<task-id>/codex_last_message.md` — Codex's final message
- `state/worktrees/<repo-id>/<task-id>/codex_execution.json` — exit code, timings
- `state/artifacts/engineering/<task-id>/worktree.diff` — the diff to review
- `state/artifacts/engineering/<task-id>/review_summary.json`
- `state/checkpoints/platform/task_runs/run-<task-id>.json` — canonical task run record

**Default Codex timeout is 120 seconds.** If the task isn't done in that window the run fails with `timed_out: true`. Keep tasks small enough to fit.

**Review checklist** — read the task run record and verify all of these:
- `status` is `succeeded` and `classification` is `safe_for_review`
- `validation_checks` — every entry has `passed: true`
- `execution.exit_code` is `0` and `timed_out` is `false`
- `post_run_git_state.changed_files` contains only files the constraints allowed
- Open `worktree.diff` and read it end to end. Confirm:
  - no scope creep (no unrelated files touched, no new dependencies added)
  - protected invariants held (privacy allowlists, schema fields, policy files)
  - new helpers or types don't duplicate existing ones
  - the change actually implements the acceptance criteria
- Open `codex_last_message.md` and read Codex's self-report. Watch for any `no_test_reason_code` that doesn't match the task type, or any note that Codex couldn't complete part of the objective.

If the review reveals a problem, do not apply the diff. Surface the issue to the user with a specific proposed fix: tighten the constraints, re-dispatch with revised scope, or hand-edit before applying.

### Phase 5 — Apply

Only after review passes:

1. From the repo root: `git apply state/artifacts/engineering/<task-id>/worktree.diff`
2. Verify the change landed — grep for key additions, or read the modified region.
3. Update `docs/products/<product-id>/backlog.md`: strike through the completed item and append a short `✓ done — <what was actually done>` note on the same line. Do not delete the item; keeping it visible as done is part of the trail.
4. Tell the user: the task id, the files that changed, and any build-time note (e.g. "needs an Xcode build to confirm it compiles").

Do not commit the change on the user's behalf. Application to the working tree is the final step of the skill. The user decides what to commit.

## Operating boundaries

- **Never** commit or push the applied diff. Leave it staged or unstaged for the user to review visually.
- **Never** dispatch more than one task at a time without explicit approval in the same turn.
- **Never** bypass review by applying without reading the diff.
- **Never** invent a task that isn't in the backlog or specified by the user.
- **Never** edit `packages/policies/`, `packages/schemas/`, or `infra/` through this skill. Those changes go through their own review process.

## Failure modes to catch early

- Runtime supervisor is stopped → nothing claims the task → enqueue appears to hang.
- Venv missing pyyaml → Python enqueue script fails with `ModuleNotFoundError: yaml`.
- Managed repo `state/repos/<repo-id>/` not synced → engineering worker cannot create a worktree.
- User writes JSON to `state/checkpoints/platform/tasks/` directly → nothing happens; tasks live in the SQLite control plane DB, not those files.
- Task scope is too broad → Codex hits the 120s timeout and returns nothing.
- Constraints are too loose → Codex touches files you didn't expect, diff fails review.
