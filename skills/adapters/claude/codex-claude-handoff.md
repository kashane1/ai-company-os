---
description: Dispatch bounded code-change tasks from Claude to Codex via the ai-company-os engineering lane. Use when the user says "hand this to codex", "dispatch to codex", "delegate to codex", "queue a task for codex", "find a few tasks for codex", "have codex fix/add/implement X", or any phrasing that asks Claude to route implementation work through the Codex subprocess pipeline. Covers the full loop: select task, pre-flight checks, enqueue via control plane, monitor the run, review the diff, apply to source, update the backlog.
canonical_source: skills/canonical/handoffs/codex-claude-handoff.md
---

# Codex-Claude Handoff — Claude adapter

You are running the codex-claude-handoff skill. The full protocol lives in `skills/canonical/handoffs/codex-claude-handoff.md` — read it once if you haven't this session. This adapter maps each protocol phase to concrete Claude tool usage.

## Phase 1 — Select

**Mode A (explicit task from user):**
- Read any files the user referenced so you can write concrete constraints. Do not enqueue a task where you haven't read the target file yourself.
- If the scope looks larger than "one file, maybe two," propose a split in-conversation before continuing. Use AskUserQuestion to confirm the split.

**Mode B (you pick from the backlog):**
- Read `docs/products/catchbook/backlog.md` (or whichever product the user named).
- Filter to Build Now items tagged `ios_feature` / `ios_bugfix` / `engineering_change` and not gated by a `product_decision`.
- Use AskUserQuestion to present 1–3 candidates. One question, one option per candidate, plus an "other" option. Do not dispatch more than one per turn without explicit approval.

## Phase 2 — Pre-flight

Run these reads in parallel with a single Bash tool call, piping outputs together:

```
cat state/checkpoints/platform/runtime-supervisor-status.json
cat infra/repos.json
ls state/repos/ai-company-os/ 2>/dev/null && echo OK_REPO || echo MISSING_REPO
ls .venv/bin/python 2>/dev/null && echo OK_VENV || echo MISSING_VENV
```

Bail if any of the following is true:
- `runtime-supervisor-status.json` does not show `"state": "running"`. Tell the user to run `launchctl kickstart -k gui/$(id -u)/com.ai-company-os.runtime-supervisor` and stop.
- The target `repo_id` is missing from `infra/repos.json`, or `state/repos/<repo-id>/` doesn't exist. Do not dispatch to a repo without a managed clone.
- `.venv/bin/python` is missing. Tell the user to recreate the venv.

Also use Read to open each file that will be named in the constraints. You need to know the existing shape of the code to write good "reuse X, don't duplicate it" rules.

## Phase 3 — Dispatch

**You cannot run the Python enqueue script yourself** — the sandbox's Python is too old (3.10 lacks `datetime.UTC`). Always hand the Python script to the user to run on their Mac.

Use this exact template, filling in only title / summary / constraints:

```bash
source .venv/bin/activate
python - <<'PY'
import sys
sys.path.insert(0, '.')
from apps.api.control_plane import ControlPlaneService
from packages.schemas.task_packet import WorkerLane, RiskLevel

svc = ControlPlaneService()

goal = svc.create_goal(
    title="<goal title — one short sentence>",
    summary="<one-paragraph reason this work matters>",
)

task = svc.create_task_for_goal(
    goal_id=goal.id,
    repo_id="ai-company-os",
    lane=WorkerLane.ENGINEERING,
    title="<task title>",
    summary=(
        "<objective paragraph>\n\n"
        "<acceptance criteria as sentences>\n\n"
        "<reuse X helpers, do not duplicate Y>"
    ),
    task_type="ios_feature",  # or ios_bugfix, engineering_change
    product_id="catchbook",
    risk_level=RiskLevel.LOW,
    requires_approval=False,
    constraints=[
        "Operate only inside the managed worktree.",
        "Edit only <explicit file list>.",
        "Do not modify packages/policies/, packages/schemas/, infra/, or docs/.",
        "<task-specific reuse / invariant rules>",
        "Leave all changes uncommitted for manual inspection.",
    ],
)

print("enqueued:", task.id, "under goal", goal.id)
PY
```

Ask the user to paste back the `enqueued: task-... under goal goal-...` line. That task id is the key for Phase 4 and 5.

## Phase 4 — Monitor and review

Wait until the user says "check it" or equivalent, or until you have reason to believe the run is done (≥30 seconds have passed and the task is small).

Run this single Bash command to gather everything:

```
cat state/checkpoints/platform/task_runs/run-<task-id>.json
echo "---DIFF---"
cat state/artifacts/engineering/<task-id>/worktree.diff
echo "---LAST MESSAGE---"
cat state/worktrees/ai-company-os/<task-id>/codex_last_message.md
```

If the task run record doesn't exist yet, the run is still in flight — wait and retry. Do not re-dispatch.

**Walk through the review checklist explicitly in your response to the user:**
1. Status / classification
2. Validation checks pass count
3. Changed files vs. allowed files (call out any mismatch)
4. Diff walk-through — describe what Codex actually did in your own words, not just "it added a swipe action"
5. Invariants held (whatever the task packet said to protect)
6. Codex's self-report from `codex_last_message.md`, especially any `no_test_reason_code`

If anything in the checklist fails, stop. Tell the user what's wrong and propose a specific fix. Do not apply a bad diff.

## Phase 5 — Apply

If review passes:

1. `git apply state/artifacts/engineering/<task-id>/worktree.diff` from the repo root (via Bash tool).
2. Grep for the key additions to confirm they landed. Read the modified region with Read to double-check.
3. Use Edit to update `docs/products/<product-id>/backlog.md`: strike through the completed bullet and append `✓ done — <what actually shipped>`. Do not delete the item.
4. Report to the user: task id, files changed, any Xcode-build caveat if this is an iOS task.

**Do not commit.** Ever. Application to the working tree is the endpoint.

## When to escalate back to the user instead of proceeding

- The requested change isn't a bounded code change (it's a design decision, a research question, or a multi-day effort).
- The backlog has no clean "one file" candidates and the user asked you to pick.
- A dependency the task needs isn't installed (e.g. a framework Codex will have to add).
- The managed repo for the target doesn't exist.
- A previous dispatch is still running and you haven't reviewed it yet.

## Tool-use notes specific to this skill

- Always use TodoWrite to track the five phases. One todo per phase.
- Use AskUserQuestion in Phase 1 (Mode B) to confirm candidates. Do not dispatch without explicit confirmation.
- Do not use AskUserQuestion in Phases 2–5 — those phases should run without interruption unless something fails.
- Never invoke the `codex` CLI yourself. The engineering worker does that. Your job is to enqueue, read state, and apply diffs.
