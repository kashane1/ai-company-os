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

There is **no auto-merge** in this phase. That makes revert simpler
than the PR-based design in the plan, but it also means the revert
steps for the "already in canonical" case are human git operations,
not `gh pr close` calls.

## Decision tree

```
                    ┌─ Something went wrong ─┐
                    ▼                        ▼
        Proposal still in flight?    Proposal already applied?
         (staged, awaiting sign)      (canonical tree mutated)
                    │                        │
                    ▼                        ▼
           → Section 1                   → Section 2
```

Section 1 is cheap and routine. Section 2 is a real revert and should
be treated like any other production rollback.

## Section 1 — proposal still in flight

Use this when the worker is currently blocked on approval OR the
artifact is staged but not yet applied. The golden path:

### 1.1 Freeze the worker lane

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

### 1.2 Reject the pending approval

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

### 1.3 If the worker is NOT currently polling, move the artifact by hand

```bash
mv state/artifacts/skill-evolution/<proposal_id> \
   state/quarantine/skill-evolution/<proposal_id>
```

Use `mv` (same-filesystem POSIX rename, atomic). Do NOT use
`shutil.move` or `cp -r && rm -rf` — those can leave the proposal
visible in two places during the transition.

### 1.4 Drain any leftover queue entries

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

### 1.5 Release any stuck lock

```bash
sqlite3 state/checkpoints/platform/control_plane.sqlite3 \
  "DELETE FROM skill_evolution_locks;"
```

This is safe while the worker is frozen — no live worker can race
the delete.

### 1.6 Unfreeze (only after the cause is fixed)

```bash
rm state/flags/skill_evolution_frozen
```

## Section 2 — proposal already applied to canonical

Use this when a signed proposal was cherry-picked into
`skills/canonical/` and then caused a regression. This is a real
revert.

### 2.1 Freeze the lane FIRST

Same as 1.1 — stop anything new from happening while you work:

```bash
touch state/flags/skill_evolution_frozen
```

### 2.2 Identify the commit that applied the diff

The cherry-pick happens out of band (Option B: human reviewer reads
the signed artifact, applies by hand). The commit message should
reference the approval ID — grep for it:

```bash
git log --all --oneline --grep="skill-evo-<proposal_id>"
```

If you can't find a commit message referencing the approval ID,
treat it as an unreferenced human commit and find it by path:

```bash
git log --oneline -- skills/canonical/<target_skill_id>/
```

### 2.3 Revert the commit

```bash
git revert --no-edit <commit_sha>
git push origin HEAD:revert/skill-evolution-<proposal_id>
```

Open a PR from the revert branch to `main` — this is the one case
where a human PR is non-optional because the revert is touching
production canonical skills.

### 2.4 Quarantine the artifact dir AND the signed token record

Even though the canonical tree is being reverted via git, the signed
approval record + token still exists in state. Leave the approval
record's status at `approved` (it was approved — that's historical
fact), but move the artifact dir:

```bash
mv state/artifacts/skill-evolution/<proposal_id> \
   state/quarantine/skill-evolution/<proposal_id>
```

The token itself is already burned and cannot be replayed per the
`ApprovalToken.burn_count` check, so there's no token revocation
step.

### 2.5 File a post-mortem entry

```bash
mkdir -p docs/solutions/integration-issues
cat > docs/solutions/integration-issues/skill-evolution-revert-<date>.md <<'MD'
# Skill-evolution revert: <proposal_id>

## What was proposed
<short description>

## What broke
<symptom + logs + trace>

## Why the gates didn't catch it
- allowlist: (yes / no / N/A)
- denylist:  (yes / no / N/A)
- fixture/skill atomicity: (yes / no)
- regression fixture gate: (deferred in Phase 3 first landing)
- reviewer sign-off: (who + when)

## Fix
<link to revert PR>

## Gate improvement to follow up
<what should have caught this — open a task>
MD
```

The "Gate improvement to follow up" section is the load-bearing
output of the revert — every revert should produce one new
check/fixture that would have caught the failure earlier. This is
how Phase 3 compounds over time without sliding toward auto-merge.

### 2.6 Unfreeze after the revert PR merges

```bash
rm state/flags/skill_evolution_frozen
```

## Appendix A — walked-through dry run

Before marking Phase 3 "done," one operator MUST walk through this
runbook against a synthetic proposal. The dry run exercises:

1. Kill-switch engage / disengage.
2. `approval-reviewer list` / `reject` / `show`.
3. Artifact quarantine via `mv`.
4. DB-level lock release.
5. (Section 2 only) A dummy `git revert` on a throwaway commit.

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
  separately.
- **Revert an in-flight proposal whose worker process has frozen
  mid-poll.** The kill-switch check is bounded by `poll_interval_seconds`
  (default 5 s); a truly frozen worker is a separate incident. Kill
  the process (`pkill -f worker-skill-evolution`), then run Section 1
  from step 1.2 onward.
- **Cross-plan coordination.** If the proposal touched anything in
  the Phase 4 ACP dispatch path or the Phase 5 command-scan policy,
  those phases have their own rollback surfaces. Consult their
  runbooks (when they exist) alongside this one.
