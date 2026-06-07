# todos

Per-task working tickets that the system or operator picks up. This is
the repo's backlog, not hand-maintained documentation. Each file is a
single ticket.

## Naming convention

```
todos/NNN-<status>-<priority>-<slug>.md
```

- `NNN` — zero-padded sequence number (`001`, `002`, …)
- `<status>` — `pending` or `completed`
- `<priority>` — `p1`, `p2`, or `p3`
- `<slug>` — kebab-case description of the ticket

Example:

```
todos/042-pending-p1-tighten-postmortem-redaction.md
```

## Priority

- **p1** — blocking. Urgent. Should be the next thing picked up.
- **p2** — important. Not urgent, but needs to land soon.
- **p3** — polish or follow-up. Safe to defer.

## Lifecycle

A ticket moves through:

1. **`pending`** — not done. May be in flight or untouched.
2. **`completed`** — done. The work landed and any acceptance criteria
   met.

Status transitions happen by explicit, reviewed rename of the file.
Renaming `001-pending-p1-foo.md` to `001-completed-p1-foo.md` marks the
ticket done. The sequence number and slug stay stable.

**On completion, move the file to `todos/archive/`.** The top level of
`todos/` is the *working set* — only `pending` tickets an agent should
consider picking up. Completed tickets live in `todos/archive/` so a
fresh agent scanning `ls todos/*.md` sees the backlog, not the history.
The trail is preserved (we never delete todos); it's just one directory
down. This keeps the working set small for token-efficient scans.

When marking a todo `completed`, append a short completion note at the
bottom of the file. One or two lines is enough:

```md
## ✓ Completed YYYY-MM-DD
Landed in <PR / commit / artifact>. <One sentence summary.>
```

If a todo is no longer relevant but never done, mark it `completed` and
note "Abandoned" in the completion line, with a reason. Don't delete
todos — the trail is part of the audit.

## Inventory snapshot (filenames only)

This snapshot is not authoritative — `ls todos/*.md` (working set) and
`ls todos/archive/*.md` (history) are.

- Working set (pending, top level of `todos/`): ~42
- Archived (completed, under `todos/archive/`): ~65

The `complete` vs `completed` filename token inconsistency that existed
before Anti-drift batch 1.2 has been normalized — all completed tickets
now use `-completed-`.

## When to file a new todo

- A task is too small to need a full plan under `docs/plans/`
- A follow-up surfaced during another task and should not block the
  current change
- A polish-tier finding from a review or audit needs a home
- A reviewer asked for something the current PR shouldn't expand to
  cover

## When NOT to file a todo

- The work is in scope for the current task — just do it
- It needs founder-level discussion — file a brainstorm under
  `docs/brainstorms/` first
- It's a recurring operator workflow — that belongs as a skill or a
  scheduled-session prompt, not a todo
- It's a one-line typo fix — fix it inline

## Related

- [docs/plans/INDEX.md](../docs/plans/INDEX.md) — for larger
  implementation work that needs structure
- [docs/handoffs/INDEX.md](../docs/handoffs/INDEX.md) — for session-to-session
  baton-passing
- [docs/brainstorms/](../docs/brainstorms/) — for upstream ideation
