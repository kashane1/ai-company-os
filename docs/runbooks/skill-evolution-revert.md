# Runbook: Revert a shipped skill-evolution proposal

**Audience:** Whoever is on the keyboard when a self-evolved skill
starts misbehaving in production.

**Scope:** Phase 3 (Option B — HMAC token approval, no `gh pr create`).
The worker's only mutable surface is (a) artifact dirs under
`state/artifacts/skill-evolution/`, (b) the matching approval records
in `state/checkpoints/platform/approvals/` and
`.../approval_tokens/`, (c) the `skill_evolution_locks` table in the
control plane DB, and (d) — if the proposal was approved and the
reviewer cherry-picked it into the canonical tree — whatever git
commit landed the diff.

There is **no auto-merge** in this phase. The worker's terminal
state after approval is "wrote applied.flag to the staged artifact
dir" — the canonical tree is mutated only when a human cherry-picks
the staged diff in a separate, human-authored PR. That makes revert
simple: in Option B's first landing, a "revert" is almost always
just rejecting a still-in-flight proposal, because nothing has
landed in `skills/canonical/` via the worker.

The "proposal already applied to canonical" case — where you'd need
a `git revert` against a human cherry-pick PR — is handled by the
normal git revert workflow, not this runbook. This runbook focuses
on the in-flight case.

## Flow — proposal still in flight

Use this when the worker is currently blocked on approval OR the
artifact is staged but not yet applied. The golden path:

### 1. Freeze the worker lane

```bash
touch state/flags/skill_evolution_frozen
```

The flag is read on every claim attempt AND on every poll cycle
(``_poll_with_heartbeat`` in ``apps/worker-skill-evolution/main.py``).
Any in-flight proposal will raise ``SkillEvolutionFrozenError`` on
its next poll and mark the task ``BLOCKED`` with summary
``paused:frozen``.

Verify:

```bash
ps -ef | grep worker-skill-evolution     # no running claim loop
cat state/flags/skill_evolution_frozen   # exists, content irrelevant
```

### 2. Reject the pending approval

```bash
.venv/bin/python apps/approval-reviewer/main.py list
```

This prints every `status=pending`, `approval_type=skill_evolution`
record with its artifact dir and rationale. Copy the `approval_id`
you want to kill, then:

```bash
.venv/bin/python apps/approval-reviewer/main.py reject <approval_id> \
  --reason "reverting phase-3 proposal: <what broke>"
```

The approval record flips to `rejected`. If the worker is still
polling, its next cycle sees the rejection and quarantines the
staged artifact dir automatically.

### 3. If the worker is NOT currently polling, move the artifact by hand

```bash
mv state/artifacts/skill-evolution/<proposal_id> \
   state/quarantine/skill-evolution/<proposal_id>
```

Use `mv` (same-filesystem POSIX rename, atomic). Do NOT use
`shutil.move` or `cp -r && rm -rf` — those can leave the proposal
visible in two places during the transition.

### 4. Drain any leftover queue entries

If a task stayed `PENDING` in the queue instead of being claimed
(e.g. the whole supervisor was down), mark it failed directly in the
DB:

```bash
sqlite3 state/checkpoints/platform/control_plane.sqlite3 <<'SQL'
UPDATE tasks
   SET status = 'failed',
       failed_at = datetime('now'),
       error_summary = 'manual revert via skill-evolution-revert runbook'
 WHERE lane = 'skill_evolution'
   AND status IN ('pending', 'blocked');
SQL
```

### 5. Release any stuck lock

```bash
sqlite3 state/checkpoints/platform/control_plane.sqlite3 \
  "DELETE FROM skill_evolution_locks;"
```

This is safe while the worker is frozen — no live worker can race
the delete.

### 6. Unfreeze (only after the cause is fixed)

```bash
rm state/flags/skill_evolution_frozen
```

## If a proposal was already cherry-picked into canonical

Out of scope for this runbook. In Option B the worker never
mutates `skills/canonical/`, so a diff that landed there was
carried in by a separate human-authored PR and must be reverted
the same way — `git revert <commit_sha>` against that PR,
following whatever your normal production-revert process is.
Once the revert is merged, come back and quarantine the staged
artifact + file a post-mortem:

```bash
mv state/artifacts/skill-evolution/<proposal_id> \
   state/quarantine/skill-evolution/<proposal_id>
```

Leave the approval record's status at `approved` — that's
historical fact, not something to rewrite.

## Appendix A — dry run

Before marking Phase 3 "done," one operator walks through the
in-flight flow above against a synthetic proposal. The dry run
exercises:

1. Kill-switch engage / disengage.
2. `approval-reviewer list` / `reject` / `show`.
3. Artifact quarantine via `mv`.
4. DB-level lock release.

Record the walk-through in
`docs/solutions/integration-issues/skill-evolution-revert-dryrun-<date>.md`
and reference it from the Phase 3 Definition of Done checklist.

## Appendix B — what this runbook does NOT cover

- **Revert a proposal that was signed by a forged token.** The HMAC
  burn path makes this structurally impossible in the first landing,
  but the mitigation if the signing key itself leaks is "rotate the
  key" — see `packages/tools/primitives/approvals.py:_load_signing_secret`
  for the key file path. Rotating the key invalidates every
  outstanding unsigned token on the system; handle that consequence
  separately. The larger fix is the Keychain migration plan at
  `docs/plans/2026-04-15-macos-keychain-approval-signing-migration.md`.
- **Revert an in-flight proposal whose worker process has frozen
  mid-poll.** The kill-switch check is bounded by `poll_interval_seconds`
  (default 5 s); a truly frozen worker is a separate incident. Kill
  the process (`pkill -f worker-skill-evolution`), then rerun the
  in-flight flow from step 2 onward.
- **Cross-plan coordination.** If the proposal touched anything in
  the Phase 4 ACP dispatch path or the Phase 5 command-scan policy,
  those phases have their own rollback surfaces. Consult their
  runbooks (when they exist) alongside this one.
