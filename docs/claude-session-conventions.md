# Claude Session Conventions

Status: active as of 2026-04-10 (Phase 0.3).

## Per-session worktrees

Every Claude session that **mutates code** must work inside a dedicated worktree:

```
state/worktrees/claude/<session-id>/
```

Creation, teardown, and handoff are handled by `SupervisorSession` (see
`packages/tools/supervisor/claude_entrypoint.py`, Phase 3.3). Sessions that
only read the repo or only touch `state/` may skip the worktree.

### Lifecycle

1. `SupervisorSession.open()` creates the worktree at
   `state/worktrees/claude/<session-id>/` via `git worktree add`.
2. Claude performs the work there. All edits, commits, and Codex dispatches
   target the worktree path.
3. `SupervisorSession.close(summary_md=...)` inspects the worktree state:
   - **Clean (no uncommitted changes, nothing stashed)** — the worktree is
     removed and its `.git/worktrees/<id>` entry pruned.
   - **Dirty** — the session writes `handoff.md` to the worktree root and
     leaves the directory in place. The weekly cleanup script
     (`scripts/cleanup_agent_worktrees.sh`) will not delete dirty worktrees.

### Handoff contract

`handoff.md` is required in every non-clean worktree at session close. It
must include:

- Session id and actor (`claude`, model, date).
- What work is in-flight (linked task ids or `SupervisorSession` events).
- What the next owner should do first.
- Any blocked approvals and their ids.

Missing `handoff.md` on a dirty worktree is a session-close failure — the
close call raises rather than orphaning state.

### Cleanup policy

- `scripts/cleanup_agent_worktrees.sh` is on-demand only until it has run
  cleanly three times.
- It never removes `.git/index.lock` automatically; it logs and exits
  non-zero so the founder can inspect.
- Clean `.claude/worktrees/<name>` dirs older than 7 days with empty
  `git status` and empty `stash list` are eligible for removal.

### Test coverage

- `tests/python/integration/test_supervisor_session.py` exercises the open →
  mutate → close clean and dirty paths.
- `tests/python/unit/test_worktree_cleanup.py` (Phase 0.2) covers the
  prune-stale-entry and refuse-to-delete-dirty-worktree paths.
