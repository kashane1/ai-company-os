---
description: Dispatch a bounded fix to Codex Cloud via Chrome MCP and open a PR against staging — never main. Invoke for "use codex cloud", "dispatch via codex cloud", "queue this on codex cloud", "open a PR via codex cloud".
canonical_source: skills/canonical/codex-cloud-dispatch/skill.md
---

# Codex Cloud Dispatch (Claude adapter)

You are running the `codex-cloud-dispatch` skill from
`skills/canonical/codex-cloud-dispatch/skill.md`. Follow the
canonical definition.

The detailed UI mechanics (pixel coordinates, MCP tool names,
known quirks) live in `docs/codex-cloud-dispatch.md`. The canonical
skill is the operational source of truth; the doc is the
reference.

## Quick reference

1. **Pre-flight.** Locate or open the Codex Cloud tab. Screenshot.
   Verify the repo chip reads `ai-company-os` and the branch chip
   reads `staging`. Stop if either is wrong.

2. **Render the brief** in the eight-section order:
   `Title line` → `CONTEXT` → `TASK` → `FILES ALLOWED TO EDIT` →
   `DO NOT EDIT` → `HARD CONSTRAINTS` → `ACCEPTANCE CRITERIA` →
   `PR line`. The PR line must include the literal string
   `Open the PR against the staging base branch`. The
   `DO NOT EDIT` list must always include `tests/**` and
   `_PREEXISTING_FAILURES`.

3. **Submit via the documented Chrome MCP sequence.** Click to
   focus the composer at the documented coordinate, `computer.type`
   the full brief in one call, `find` the Submit button, `left_click`
   by ref. Do NOT press Enter. Do NOT use `form_input` on the
   composer.

4. **Verify submission.** Composer cleared, skeleton-loader row
   appears, notification badge increments. Missing any one →
   re-screenshot, retry once, then stop and report.

5. **Review the diff.** Open the task detail page. Confirm file
   count and file names match the brief. Watch for over-reach:
   bigger diff than implied, files not in the allow-list, new
   deps, unrelated cleanup, unwanted renames. If wrong, reroll
   via the follow-up box — do NOT click Create PR on a bad diff.

6. **Create PR.** `find` the "Create PR" button. `left_click` by
   ref. Verify button text flips to "View PR". Capture the PR URL.

7. **Final report.** Task title, PR URL, diff size, allowed-files
   list, pytest nodeids the PR should flip green.

## Invariants (must hold every dispatch)

- Base branch is `staging`. Never `main`.
- Repo chip is `ai-company-os`.
- One task per dispatch unless explicitly batched.
- Never delete or weaken the xfail shim (`_PREEXISTING_FAILURES`,
  `pytest_collection_modifyitems`).
- Policies, schemas, and canonical skills need explicit approval
  in the same turn before being dispatched as editable.
- Use the documented Chrome MCP contenteditable typing sequence.
- The brief's last line includes
  `Open the PR against the staging base branch`.
- No direct merges, approvals, or pushes from this skill.
- Preserve task-specific scope boundaries.
- Human review before merge.
- Final report captures task title and PR link.
- Stop if the Codex Cloud UI flow diverges from
  `docs/codex-cloud-dispatch.md`.

## Disambiguation

- Local Codex CLI dispatch → `codex-claude-handoff` (deferred).
- Inline implementation by the current session → just do it; this
  skill is for *queuing*, not *executing*.
- Open-ended exploratory search → `Explore` agent.

If two trigger phrases could match, ask the operator.

## Edit boundaries

Read-only outside `state/artifacts/codex-cloud-dispatch/`. Never
edits `packages/`, `apps/`, `products/`, `docs/`, `skills/`,
`tests/`, or `.claude/` locally. No merge, no approval, no push.
Never click any GitHub button other than `Create PR` on the task
detail page.
