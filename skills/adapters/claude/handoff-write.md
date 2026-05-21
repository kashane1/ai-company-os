---
description: Write a dated session handoff under docs/handoffs/ following the docs/handoffs/INDEX.md convention. Refuses to overwrite. Invoke for "write a handoff", "wrap this session", "end the session with a handoff", "draft the next-session prompt".
canonical_source: skills/canonical/handoff-write/skill.md
---

# Handoff Write (Claude adapter)

You are running the `handoff-write` skill from
`skills/canonical/handoff-write/skill.md`. Follow the canonical
definition.

## Quick reference

1. **Validate slug.** Must match `^[a-z0-9][a-z0-9-]*$`.

2. **Compute target path.** `docs/handoffs/YYYY-MM-DD-<slug>.md`,
   plus `-NNN` if `same_day_counter` is given.

3. **Refuse to overwrite.** If the file exists, stop and tell the
   operator. Do NOT silently overwrite.

4. **Render the file** with these eight sections, in this order:
   - `## What changed`
   - `## What is open`
   - `## What is blocked`
   - `## What is stale`
   - `## Files touched`
   - `## Validation run`
   - `## Exact next action`
   - `## Resume prompt`

5. **Write the file.** Single atomic write. Do not modify
   `docs/handoffs/INDEX.md`; the file appearing on disk is the
   source of truth.

6. **Never touch the root `HANDOFF.md`.** Historical only.

7. **Never commit. Never push.** The operator decides.

## Disambiguation

- Capture current state in a structured report → `agent-preflight`.
- Read a prior handoff → plain `Read`.
- One-line summary → ask the operator first; the convention is
  full-shape.

## Edit boundaries

Writes exactly one file under `docs/handoffs/`. No other writes. No
state mutation. No commit. No push.
