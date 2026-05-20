# Codex Cloud dispatch via Chrome MCP

> **Operational source of truth is the canonical skill** at
> [`skills/canonical/codex-cloud-dispatch/skill.md`](../skills/canonical/codex-cloud-dispatch/skill.md)
> (Claude adapter:
> [`skills/adapters/claude/codex-cloud-dispatch.md`](../skills/adapters/claude/codex-cloud-dispatch.md)).
> The canonical skill encodes the invariants, the brief structure,
> and the five-phase procedure. This doc is the detailed UI
> reference — pixel coordinates, MCP tool names, the contenteditable
> typing sequence, and the known quirks — that the canonical skill
> points back to.

How to queue a bounded fix on Codex Cloud (chatgpt.com/codex/cloud) and open a PR against `staging`, driven from a Claude (Cowork) session using the Chrome MCP.

Use this doc when you are NOT using the local `codex-claude-handoff` protocol (Python enqueue script + on-device worker). Codex Cloud is the right channel when:

- You want a PR opened directly on GitHub without running anything locally.
- The repo is already connected in Codex Cloud and the base branch is pre-set to `staging`.
- You want to fan out multiple small PRs in parallel without babysitting.

The local `codex-claude-handoff` skill is still the right channel when you need the task to run against a specific local worktree, use local state/ artifacts, or exercise on-device workers.

## Invariants

1. **Base branch must be `staging`.** Never dispatch against `main`. Verify the branch chip next to the composer reads `staging` before typing anything.
2. **Repo chip must be `ai-company-os`.** Codex Cloud remembers the last-used repo; re-check after any context switch.
3. **One task per dispatch.** If the fix touches more than ~4 files or mixes unrelated bugs, split it. Scope creep is the primary Codex Cloud failure mode — it refactors more than asked when the brief is vague.
4. **Never delete the xfail shim or weaken tests in a dispatched brief.** Tell Codex explicitly: "Do NOT edit `_PREEXISTING_FAILURES` or `pytest_collection_modifyitems`."
5. **Policies and skills require explicit user approval before dispatching edits to them.**

## Brief structure

Every brief should contain, in this order:

1. **Title line** — short imperative: "Fix X", "Add Y".
2. **CONTEXT** — one paragraph explaining the bug/root cause in prose. Include file paths and the symptom. If you already diagnosed it, say so.
3. **TASK** — the exact change to make. Prefer prescriptive ("rename X to Y", "add key Z conditionally") over descriptive. If there are multiple acceptable shapes, list them as Option A / Option B and say Codex may pick.
4. **FILES ALLOWED TO EDIT** — bulleted absolute paths. Cap at 4 unless the fix genuinely touches more.
5. **DO NOT EDIT** — bulleted list of files/patterns that must stay untouched. Always include tests/**, `_PREEXISTING_FAILURES`, and any policy/skill files you didn't get explicit approval on.
6. **HARD CONSTRAINTS** — "no new deps", "no refactors", "keep imports sorted", etc.
7. **ACCEPTANCE CRITERIA** — bulleted, testable. If tied to specific pytest nodeids, name them.
8. **PR line** — "Open the PR against the `staging` base branch. Suggested commit message: ...".

The prescriptive form is important: Codex Cloud does NOT have this repo's CLAUDE.md in its context, so it will not know about worker boundaries, the `_PREEXISTING_FAILURES` shim, or the policy-edit approval rule unless you tell it.

## Driving the web UI with Chrome MCP

Chrome MCP (`mcp__Claude_in_Chrome__*`) is the right tool. Computer-use tools click pixels and are slower and more fragile.

### One-time setup per session

1. `tabs_context_mcp` to find an open Codex Cloud tab, or `tabs_create_mcp` with `url: https://chatgpt.com/codex/cloud` to open one.
2. Screenshot the tab and verify the repo chip (`ai-company-os`) and branch chip (`staging`) are correct.

### Typing a brief

The composer at chatgpt.com/codex/cloud is a contenteditable (ProseMirror/Slate), NOT a plain textarea. `form_input` does not reliably update its visible state. Use this sequence:

1. `computer` with `action: left_click` and `coordinate: [1000, 207]` to focus the composer. (Coordinates are stable for 1440-wide windows; re-screenshot if layout changes.)
2. `computer` with `action: type` and the full brief as `text`. The brief can be thousands of characters — one call is fine.
3. `find` with a query like `"Submit send button at right end of composer"` — returns a ref like `ref_100`.
4. `computer` with `action: left_click` and `ref` set to the submit ref.

Do NOT try to submit by pressing Enter; that inserts newlines. Always click the button.

### Verifying submission

After clicking submit, screenshot. You should see:

- Composer cleared (placeholder "Ask a question with /plan" returns).
- A skeleton loader row in the Tasks list above the TODAY header.
- The notification badge at the top right increments.

If any of the three is missing, re-screenshot and retry the submit click — the button click can no-op if focus was stolen.

### Clearing the composer between briefs

If the composer still has text from a previous dispatch:

1. Click at `[1000, 207]` to focus.
2. `key` with `cmd+a` then `Delete` (or `Backspace`).
3. Then `type` the new brief.

### Opening the PR

Codex Cloud does NOT auto-open PRs after the task finishes. The button in the task detail header starts as "Create PR" and must be clicked explicitly. Then it flips to "View PR" and the PR appears on GitHub against `staging`.

Workflow after each task completes:

1. From the Tasks list, click the task row title to open its detail page.
2. Read the Summary in the left pane and skim the Diff in the right pane. Confirm scope matches the brief (file count, files named).
3. If scope is wrong, use the "Request changes or ask a follow-up…" box at the bottom of the left pane to reroll — do NOT click Create PR on a bad diff.
4. If scope is right, `find` the "Create PR" button in the top-right header and click it via `ref`.
5. Verify the button text flips to "View PR".
6. Click the back arrow (`find` for "Go back to tasks") to return to the Tasks list for the next task.

## Signals that Codex Cloud over-reached

Watch for these when reading the diff before clicking Create PR:

- Diff size much larger than the brief implied (e.g. a "trivial one-line fix" returns +67 −55).
- Changes to files not in the allow-list — especially schemas, db, tests, conftest.py, skill canonical definitions.
- New imports or new dependencies.
- Unrelated cleanup committed alongside the fix.
- Variable or function renames that weren't requested.

On any of these, reroll via the follow-up box with a tighter instruction referencing the specific overreach, rather than clicking Create PR.

## Known quirks

- The composer briefly flashes cleared between the focus-click and the `type` action. That is normal; the typed text lands correctly.
- Long briefs (>2000 chars) render correctly but may scroll the composer view — check the final screenshot shows the trailing acceptance-criteria text, not just the middle of the brief.
- Task rows show diff stats (`+16 -12`) as soon as the task finishes, BEFORE a PR is opened. An "Open" badge with a PR icon only appears after Create PR is clicked and GitHub confirms.
- `form_input` on the composer returns success but does not update the visible state. Use `computer.type` instead.
- `left_click` by ref on the composer returns success but does not always focus the contenteditable. Use `left_click` by coordinate `[1000, 207]` to focus.
- The tasks list paginates under "TODAY". Scroll if you dispatched more than ~5 tasks in a sitting.

## After the PR is open

Hand off to the human reviewer (Kashane) with:

- The task title as it appears on Codex Cloud.
- The final diff size (`+N -M`).
- The allowed-files list from the brief (so the reviewer can confirm no scope creep).
- The pytest nodeids the PR should flip green (so the reviewer can strike them off `_PREEXISTING_FAILURES` after CI passes).

Never merge to `main` from Codex Cloud. Never click any GitHub button other than Create PR on the task detail page.
