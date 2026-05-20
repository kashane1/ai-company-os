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

This snapshot reflects what's in the directory at the time this README
was written. It is not authoritative — `ls todos/` is.

- Total files: 72
- Pending: 23
- Completed: 49 (see note below on the `complete` vs `completed` token)
- p1: 17
- p2: 30
- p3: 25

### Token inconsistency to clean up

Two status tokens are currently in use:

- `completed` (older entries)
- `complete` (later entries)

The convention going forward is **`completed`** (matches the lifecycle
states above). A future maintenance pass should rename any
`<NNN>-complete-<priority>-<slug>.md` files to
`<NNN>-completed-<priority>-<slug>.md` so the token is uniform. Do not
do this in the current batch — file renames are out of scope here.

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
