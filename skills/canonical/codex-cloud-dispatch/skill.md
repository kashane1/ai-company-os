---
id: codex-cloud-dispatch
name: Codex Cloud Dispatch
purpose: Dispatch a bounded fix to Codex Cloud (chatgpt.com/codex/cloud) via the Chrome MCP and open a PR against the staging branch, with explicit invariants and a documented submission sequence so scope creep and shim-deletion can't slip through.
owner_agent: any
target_runtimes: [claude]
stage: active
kind: agentic
allowed_edit_boundaries:
  - state/artifacts/codex-cloud-dispatch/
forbidden_areas:
  - packages/
  - apps/
  - products/
  - docs/
  - skills/canonical/
  - skills/adapters/
  - skills/registry.yaml
  - .claude/skills/
  - state/
  - tests/
  - HANDOFF.md
---

# Skill: codex-cloud-dispatch

Kind: agentic
Owner: any
Runtimes: claude

## Purpose

`codex-cloud-dispatch` queues one bounded fix on Codex Cloud
(`chatgpt.com/codex/cloud`) from a Claude (Cowork) session via the
Chrome MCP, and opens a PR against the `staging` branch on
`github.com/kashane1/ai-company-os`. The dispatched task runs in
Codex Cloud's environment; this skill never executes the change
locally. It writes briefs, drives a web UI, and reports back.

Use this skill when the operator wants a PR opened directly on
GitHub without running anything locally. Use `codex-claude-handoff`
(the sibling on-device pipeline) when the task must run against a
specific local worktree, use local `state/` artifacts, or exercise
on-device workers.

The detailed UI mechanics — pixel coordinates, MCP tool names,
known quirks of the contenteditable composer — live in
`docs/codex-cloud-dispatch.md`. That doc is the reference for the
*how*. This canonical skill is the source of truth for the *what*:
the invariants, the brief shape, the procedure, and the boundaries.

## When to invoke

Trigger phrases: "use codex cloud", "dispatch via codex cloud",
"queue this on codex cloud", "open a PR via codex cloud".

Do NOT invoke this skill for:

- Local Codex CLI dispatch (use `codex-claude-handoff` — deferred,
  but still the right channel when un-deferred).
- Implementation work the current session can do directly inline.
- Changes that touch `packages/policies/`, `packages/schemas/`,
  `skills/canonical/`, `skills/adapters/`, or
  `skills/registry.yaml` without explicit founder approval in the
  same turn.

If two trigger phrases could match, ask the operator. Do not guess.

## Invariants

Every dispatch must satisfy all of these. Violating any one of them
is grounds to stop and ask the operator before continuing.

1. **Base branch is `staging`.** Never dispatch against `main`.
   Verify the branch chip on the composer reads `staging` before
   typing anything.
2. **Repo chip is `ai-company-os`.** Codex Cloud remembers the
   last-used repo; re-verify after any context switch.
3. **One task per dispatch.** Unless the operator explicitly
   authorizes a batch, dispatch exactly one task at a time.
   Multi-file or multi-bug briefs must be split.
4. **Never delete or weaken the xfail shim.** The brief MUST tell
   Codex: "Do NOT edit `_PREEXISTING_FAILURES` or
   `pytest_collection_modifyitems`." Tests must not be weakened or
   skipped to make the change pass.
5. **Policies / schemas / canonical skills require explicit
   approval before being dispatched as editable.** If the brief
   touches `packages/policies/`, `packages/schemas/`,
   `skills/canonical/`, or `skills/adapters/`, stop and confirm
   with the operator in the same turn before sending.
6. **Use the documented Chrome MCP contenteditable typing
   sequence** (`docs/codex-cloud-dispatch.md` §"Typing a brief"):
   click to focus at the composer coordinate, `computer.type` the
   full brief in one call, locate the Submit button by `find`, then
   `left_click` by `ref`. Do NOT submit by pressing Enter — Enter
   inserts a newline. Do NOT use `form_input` on the composer; it
   returns success without updating visible state.
7. **The brief's final line is the PR instruction.** Include the
   exact instruction `Open the PR against the staging base branch`
   (the literal `staging` is load-bearing; do not paraphrase to
   `the staging branch` or `staging branch`).
8. **No direct merges, no approvals, no pushes.** This skill stops
   at "Create PR clicked, button flipped to View PR". Merging the
   PR, requesting reviews, and any post-PR action are out of scope.
9. **Preserve task-specific scope boundaries.** The brief's
   `FILES ALLOWED TO EDIT` list is the contract. Capped at ~4 files
   unless the fix genuinely touches more. The `DO NOT EDIT` list
   must always include `tests/**`, `_PREEXISTING_FAILURES`, and any
   policy/skill files not approved for this turn.
10. **Human review before merge.** This skill leaves an open PR on
    `staging`. The human reviewer (Kashane) decides whether to
    merge.
11. **Final report captures the dispatched task title and the PR
    link.** No exception; the report is how the next session knows
    what shipped.
12. **Stop if the Codex Cloud UI flow differs from the documented
    assumptions.** If the composer coordinate, the "Create PR"
    button location, or the branch chip behavior diverges from
    what `docs/codex-cloud-dispatch.md` describes, halt the
    dispatch and report the divergence to the operator before
    proceeding.

## Brief structure

Every brief must contain, in this order:

1. **Title line** — short imperative ("Fix X", "Add Y").
2. **CONTEXT** — one paragraph explaining bug/root cause in prose.
   Include file paths and the symptom. If the diagnosis is already
   known, say so.
3. **TASK** — the exact change. Prefer prescriptive over
   descriptive. Multiple acceptable shapes → list as Option A /
   Option B and say Codex may pick.
4. **FILES ALLOWED TO EDIT** — bulleted absolute paths, capped at
   ~4 unless the fix genuinely touches more.
5. **DO NOT EDIT** — bulleted patterns. ALWAYS includes
   `tests/**`, `_PREEXISTING_FAILURES`, and any policy/skill files
   not approved this turn.
6. **HARD CONSTRAINTS** — "no new deps", "no refactors", "keep
   imports sorted", and any task-specific rules.
7. **ACCEPTANCE CRITERIA** — bulleted, testable. Name specific
   pytest nodeids when tied to test outcomes.
8. **PR line** — the literal `Open the PR against the staging base
   branch.` plus a suggested commit message.

The prescriptive form matters: Codex Cloud does not have this
repo's `CLAUDE.md` in its context. Worker boundaries, the
`_PREEXISTING_FAILURES` shim, and the policy-edit approval rule
must be re-stated in the brief or Codex won't know.

## Procedure

The dispatch runs in five phases. Do not skip any phase. If a
phase fails, stop and report — do not silently fall back.

### Phase 1 — Select

Confirm the operator named the work, the scope is bounded (≤ ~4
files), and the change is a code change (not a product/design
decision). If scope is too broad, propose splitting before
continuing.

### Phase 2 — Pre-flight

1. Open or locate a Codex Cloud tab via
   `mcp__Claude_in_Chrome__tabs_context_mcp` /
   `tabs_create_mcp` with `url: https://chatgpt.com/codex/cloud`.
2. Screenshot the tab. Verify the repo chip reads `ai-company-os`
   and the branch chip reads `staging`. If either is wrong, stop
   and ask the operator.

### Phase 3 — Dispatch

1. Render the brief in the structure above. Verify every
   invariant is reflected in the brief text.
2. Click to focus the composer at the documented coordinate.
3. `computer.type` the full brief in one call. The brief can be
   thousands of characters.
4. `find` the Submit button by query (e.g. "Submit send button at
   right end of composer"). Capture the returned ref.
5. `left_click` by ref to submit.
6. Verify submission: composer cleared, skeleton loader row
   appears in Tasks list, notification badge increments. If any
   one of the three is missing, re-screenshot and retry once. If
   it still fails, stop and report.

### Phase 4 — Review

1. Open the task detail page from the Tasks list.
2. Read the Summary in the left pane. Skim the Diff in the right
   pane. Confirm file count and file names match the brief.
3. Watch for over-reach signals: diff much larger than implied,
   changes to files not in the allow-list, new dependencies,
   unrelated cleanup, renames not requested.
4. If scope is wrong, use the "Request changes or ask a
   follow-up…" box to reroll with a tighter instruction. Do NOT
   click Create PR on a bad diff.

### Phase 5 — Create PR

Only after review passes:

1. `find` the "Create PR" button in the top-right header.
2. `left_click` by ref. Verify the button text flips to "View PR".
3. Capture the PR URL on GitHub against `staging`.

### Final report

Hand off to the human reviewer with:

- The task title as it appears on Codex Cloud.
- The PR URL on GitHub.
- The final diff size (`+N -M`).
- The allowed-files list from the brief.
- The pytest nodeids the PR should flip green, if any.

The skill ends here. The human decides whether to merge.

## Boundaries and failure modes

- **No merge. No approval. No push.** The skill stops at PR
  opened on `staging`.
- **Never click any GitHub button other than Create PR** on the
  task detail page.
- **Never merge to `main` from Codex Cloud.**
- **Read-only outside `state/artifacts/codex-cloud-dispatch/`.**
  Never edits `packages/`, `apps/`, `products/`, `docs/`,
  `skills/`, `tests/`, or `.claude/` locally.
- **No product source inspection.** Do not open Swift,
  Objective-C, `.pbxproj`, or any file under `products/`.
- **Halt on UI divergence.** If the Codex Cloud UI no longer
  matches `docs/codex-cloud-dispatch.md`, stop and report
  instead of improvising.
- **No external calls beyond the Chrome MCP and the documented
  Codex Cloud surface.** No raw HTTP to chatgpt.com, no GitHub
  API calls.

## References

- Detailed UI reference: `docs/codex-cloud-dispatch.md` (pixel
  coordinates, MCP tool names, known UI quirks, post-PR handoff
  shape).
- Sibling skill: `codex-claude-handoff` (deferred local pipeline
  for tasks that must run against a local worktree).
- Operating doc: `docs/preflight-for-agents.md` (boundary table
  this skill respects).
