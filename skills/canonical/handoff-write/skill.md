---
id: handoff-write
name: Handoff Write
purpose: Write a dated session handoff under docs/handoffs/ following the convention defined in docs/handoffs/INDEX.md, so the next session can pick up without prompt archaeology.
owner_agent: any
target_runtimes: [claude]
stage: active
kind: agentic
allowed_edit_boundaries:
  - docs/handoffs/
forbidden_areas:
  - packages/
  - apps/
  - products/
  - state/
  - skills/canonical/
  - skills/adapters/
  - skills/registry.yaml
  - .claude/skills/
  - HANDOFF.md
---

# Skill: handoff-write

Kind: agentic
Owner: any
Runtimes: claude

## Purpose

Sessions end. The next session needs to know what changed, what's
open, and what to do next. Without a structured handoff, each new
session re-derives state from `git log` and inference, which is slow
and error-prone.

This skill writes a single dated handoff file under `docs/handoffs/`
following the convention defined in
[docs/handoffs/INDEX.md](../../docs/handoffs/INDEX.md). The skill
covers the *writing* of the handoff. It does not commit, push, or
mutate any state outside `docs/handoffs/`.

## When to invoke

Trigger phrases: "write a handoff", "wrap this session", "end the
session with a handoff", "draft the next-session prompt".

Do NOT invoke this skill for:

- Reading prior handoffs (use a plain `Read` on the file).
- Capturing current repo state in a structured report (use
  `agent-preflight` instead).
- Committing the change (the operator decides whether to commit).

If the operator wants a one-line summary rather than a full handoff,
ask before writing — the convention is full-shape, not summary.

## Contract

Inputs:

- `slug`: str — kebab-case short slug describing the scope of the
  handoff (e.g. `worker-runtime-fix`, `appstore-submission-prep`).
  Must match `^[a-z0-9][a-z0-9-]*$`.
- `date`: str | None — ISO date `YYYY-MM-DD`. Defaults to today's
  UTC date.
- `same_day_counter`: int | None — when present, appended as `-NNN`
  to disambiguate multiple handoffs on the same date.
- `session_summary`: object with keys:
  - `what_changed`: list[str] — bullets of meaningful work landed
  - `what_is_open`: list[str] — work in flight or staged but not done
  - `what_is_blocked`: list[str] — items waiting on a decision or
    external system
  - `what_is_stale`: list[str] — references, plans, or artifacts that
    drifted during the session
  - `files_touched`: list[{path, summary}] — one-line summaries
  - `validation_run`: list[{check, outcome}]
  - `next_action`: str — the single very next thing the next session
    should do
  - `resume_prompt`: str | None — paste-ready prompt for the next
    session, when one fits cleanly

Outputs:

- `handoff_path`: str — the path of the file written, of the form
  `docs/handoffs/YYYY-MM-DD-<slug>.md` (or with `-NNN` suffix).
- `wrote_file`: bool — true if the file was written, false if the
  skill stopped because the path already existed (see Boundaries).

## Procedure

1. **Validate the slug.** Match `^[a-z0-9][a-z0-9-]*$`. Reject
   anything else with a clear error.

2. **Compute the target path.**
   `docs/handoffs/YYYY-MM-DD-<slug>.md`, plus `-NNN` if
   `same_day_counter` is provided.

3. **Refuse to overwrite.** If the target path already exists, do
   NOT overwrite. Stop, set `wrote_file: false`, and surface the
   conflict to the operator. The operator decides whether to bump
   `same_day_counter` or to merge into the existing handoff manually.

4. **Render the handoff.** Use the structure defined in
   `docs/handoffs/INDEX.md`:

   ```markdown
   # <slug> — <date>

   ## What changed
   - …

   ## What is open
   - …

   ## What is blocked
   - …

   ## What is stale
   - …

   ## Files touched
   - `<path>` — <one-line summary>

   ## Validation run
   - <check>: <outcome>

   ## Exact next action
   <one sentence>

   ## Resume prompt
   ```
   <paste-ready prompt or "(none)">
   ```
   ```

5. **Write the file.** Single atomic write. Do not create any other
   files. Do not modify the index in `docs/handoffs/INDEX.md` — the
   index lists handoffs by convention; the file appearing on disk is
   the source of truth.

6. **Never touch `HANDOFF.md` at root.** That file is the historical
   snapshot superseded by this convention.

7. **Return the structured output.**

## Examples

### Example — clean session, full shape

```
input:
  slug: "anti-drift-batch-2"
  session_summary:
    what_changed: ["Added three anti-drift skills", "..."]
    what_is_open: []
    what_is_blocked: []
    what_is_stale: ["docs/codex-cloud-dispatch.md still bypasses canonical chain"]
    files_touched: [{path: "skills/canonical/agent-preflight/skill.md", summary: "new"}, ...]
    validation_run: [{check: "check_doc_paths.sh", outcome: "exit 0"}]
    next_action: "Run skill-stocktake and verification-loop, then commit."

→ handoff_path: "docs/handoffs/2026-05-20-anti-drift-batch-2.md"
→ wrote_file: true
```

### Example — collision

```
input:
  slug: "anti-drift-batch-2"
  date: "2026-05-20"
  (file already exists)

→ handoff_path: "docs/handoffs/2026-05-20-anti-drift-batch-2.md"
→ wrote_file: false
→ error: "Target path exists. Use same_day_counter to disambiguate, or merge manually."
```

## Boundaries and failure modes

- **Writes exactly one file** under `docs/handoffs/`. Nothing else.
- **Never overwrites.** Refuse on path collision.
- **Never edits the root `HANDOFF.md`.** That file is historical and
  marked superseded.
- **Never commits, never pushes.** Operator decides.
- **No state mutation.** Does not write to `state/`, does not update
  any registry, does not run any worker.
- **Verbatim section names.** The eight section headings come from
  `docs/handoffs/INDEX.md`. Renaming them is convention drift; this
  skill does not improvise.

## References

- Convention: `docs/handoffs/INDEX.md` (Anti-drift batch 1).
- Sibling skills: `agent-preflight` (session start),
  `stale-doc-detector`, `verification-loop`.
- Historical: `HANDOFF.md` at repo root (superseded).
