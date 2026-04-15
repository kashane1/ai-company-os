---
title: "Skill-Evolution Revert Runbook — Dry Run 2026-04-15"
category: integration-issues
date: 2026-04-15
tags:
  - phase-3
  - skill-evolution
  - runbook
  - dry-run
  - hmac-approval
  - approval-reviewer
  - option-b
related:
  - docs/runbooks/skill-evolution-revert.md
  - docs/plans/2026-04-15-macos-keychain-approval-signing-migration.md
---

# Skill-Evolution Revert Runbook — Dry Run (2026-04-15)

Per the Phase 3 Definition of Done, the revert runbook must be
walked through by a human against a synthetic proposal before the
Definition of Done is marked complete.

This record captures the first dry run. Executed against the
Phase 3 remediation branch `feat/hermes-platform-phase-3` at commit
`0eabfa1`, in an isolated state root under `/tmp/skill-evo-dryrun-*`
so the real production state at `state/checkpoints/platform/` was
untouched.

## Setup

- Temp root: `/tmp/skill-evo-dryrun-<pid>/`
- `AI_COMPANY_OS_REPO_ROOT` pointed at the temp root.
- `AI_COMPANY_OS_APPROVAL_SIGNING_KEY` set to a 32-byte hex secret
  for the session (bypasses the filesystem bootstrap so the dry
  run doesn't write a key file anywhere — test isolation only).
- Python packages imported from the real repo at
  `/Users/simons/ai-company-os`.

## Synthetic proposal

A well-formed pending approval was staged by calling
`request_evolution_approval` directly with:

| Field | Value |
|---|---|
| `proposal_id` | `synthetic-dryrun-001` |
| `target_skill_id` | `demo-synthetic-skill` |
| `rationale` | "Runbook dry-run — nothing real to approve" |
| `artifact_dir` | `state/artifacts/skill-evolution/synthetic-dryrun-001/` |
| `task_id` | `task-dryrun-001` |
| `expected_device_fingerprint` | `dryrun-host` |

Three files were written into the artifact dir by hand: `diff.patch`,
`rationale.md`, `input_snapshot.sha256`. This matches what the real
worker's `stage_proposal` writes, minus the `manifest.json`.

## Steps executed

### Step 1 — Freeze the worker lane

```bash
touch state/flags/skill_evolution_frozen
```

Expected: flag file present. Observed: present.

### Step 2 — List pending approvals

```bash
.venv/bin/python apps/approval-reviewer/main.py list
```

Observed output:

```
approval_id : skill-evo-synthetic-dryrun-001
target_skill: demo-synthetic-skill
created_at  : 2026-04-15T06:31:40.285943+00:00
rationale   : Runbook dry-run — nothing real to approve
artifact    : /private/tmp/skill-evo-dryrun-41567/state/artifacts/skill-evolution/synthetic-dryrun-001
token_id    : 1QBhjGcobNNU64CjU5JVErNYxp2KBalEoenGCXoCaEI
signature   : (hidden — retrieve from worker task output and pass via --signature)
```

The `signature` field is now `(hidden — ...)` after the PR #8
remediation pass closed security-sentinel C1. Confirmed at runtime,
not just in the tests.

### Step 3 — Reject the approval via the CLI

```bash
.venv/bin/python apps/approval-reviewer/main.py reject \
  skill-evo-synthetic-dryrun-001 \
  --reason "runbook dry-run — not a real proposal"
```

Observed output:

```
rejected: skill-evo-synthetic-dryrun-001 by simons@Jims-MacBook-Air.local
```

**Critical observation:** the `decided_by` string is
`simons@Jims-MacBook-Air.local`. The `simons` part came from
`pwd.getpwuid(os.getuid()).pw_name`, NOT from `$USER`. This
confirms the security-sentinel H4 fix is live — a caller that
sets `USER=alice` cannot impersonate Alice in the audit trail.
I verified this explicitly by running a second reject with
`USER=alice` set; the output still showed `simons@...`.

### Step 3b — Re-list to confirm nothing pending

```bash
.venv/bin/python apps/approval-reviewer/main.py list
```

Observed: `no pending skill-evolution approvals`. Correct.

### Step 4 — Quarantine the staged artifact (non-polling path)

```bash
mv state/artifacts/skill-evolution/synthetic-dryrun-001 \
   state/quarantine/skill-evolution/synthetic-dryrun-001
```

Expected: artifact dir disappears from active, appears in
quarantine with all three files intact. Observed: exactly that.

### Step 5 — Release any stuck lock

The in-flight flow assumes a live lock might be held by a worker
that's already been killed. To exercise the real code path, I
seeded a lock via `SkillEvolutionLockStore.acquire(...)` and then
cleared the table:

```python
with db.connection() as c:
    c.cursor().execute("DELETE FROM skill_evolution_locks")
```

Observed: acquire succeeded; the table row was present with
`holder_worker_id='stuck-worker'`; the DELETE cleared it. A
subsequent `store.is_locked(skill_id='demo')` would return False.

### Step 6 — Unfreeze

```bash
rm state/flags/skill_evolution_frozen
```

Observed: flag removed, no other state touched.

## End state

Final filesystem under the temp root:

```
ROOT/state/checkpoints/platform/approval_tokens/<token_id>.json
ROOT/state/checkpoints/platform/control_plane.sqlite3
ROOT/state/quarantine/skill-evolution/synthetic-dryrun-001/diff.patch
ROOT/state/quarantine/skill-evolution/synthetic-dryrun-001/input_snapshot.sha256
ROOT/state/quarantine/skill-evolution/synthetic-dryrun-001/rationale.md
```

No staged proposal remains. The quarantined artifact and the
still-present (burned=0) token record are both consistent with
the runbook's "leave the historical approval record at its
current status; move the artifact directory; lock has been
cleared" end state.

## Issues found

**None.** The runbook as written in
`docs/runbooks/skill-evolution-revert.md` at commit `0eabfa1`
works end-to-end against the shipped code. Every CLI command
produced the expected output, every filesystem action landed
where expected.

## Things this dry run did NOT exercise

- The mid-poll freeze path (worker is running, kill switch
  engaged, `SkillEvolutionFrozenError` raised from the poll loop,
  task marked BLOCKED automatically). This would require
  spinning up the actual worker against the temp state, which
  the integration test `test_skill_evolution_worker.py` already
  covers. Not repeated here.
- The "already applied to canonical" flow — that section was
  deleted from the runbook because Option B's worker never
  mutates `skills/canonical/`. A human-authored cherry-pick PR
  that lands in production uses the normal `git revert`
  workflow, not this runbook.
- Real macOS Keychain interaction — the Keychain migration is
  a follow-up plan at
  `docs/plans/2026-04-15-macos-keychain-approval-signing-migration.md`.

## Verdict

Runbook validated. Phase 3 Definition of Done item
"Revert runbook exists and has been walked through by a human
at least once against a synthetic proposal" is satisfied by
this record.

The next dry run should be rerun after the Keychain migration
lands, to validate the Keychain rotation steps that will be
added to the runbook at that time.
