# Handoffs index

Dated session handoffs from one operator/agent to the next. A handoff
exists to make it cheap for the next session to pick up where the last
one left off without prompt archaeology.

## Convention

Filename:

```
docs/handoffs/YYYY-MM-DD-<short-slug>.md
```

`<short-slug>` is kebab-case and describes the scope of the handoff
(e.g. `worker-runtime-fix`, `appstore-submission-prep`, `skill-registry-cleanup`).
Same-day handoffs may add a `-NNN` counter.

Each handoff should include the following sections. Keep them short —
this is a baton, not a memoir.

1. **What changed** — bullets of meaningful work landed this session
2. **What is open** — work that's in flight or staged but not done
3. **What is blocked** — items waiting on a decision, an external system, or someone else
4. **What is stale** — references, plans, or artifacts that are out of date
5. **Files touched** — bulleted list with one-line summaries
6. **Validation run** — what tests, scripts, or manual checks were exercised; their outcomes
7. **Exact next action** — the very next thing the next session should do
8. **Resume prompt** *(optional)* — a paste-ready prompt for the next session

Handoffs do not commit on the founder's behalf and do not push. They
leave changes uncommitted unless the founder explicitly approved the
commit in the same turn.

## Why handoffs go here, not in root `HANDOFF.md`

The previous repo convention used a single root `HANDOFF.md`. That file
captured one point in time and got overwritten on each new session,
losing history. Dated files under `docs/handoffs/` preserve the trail
and let an agent diff what's changed across sessions.

The root [`HANDOFF.md`](../../HANDOFF.md) is preserved as a historical
snapshot. See its top-of-file banner.

## Current handoffs

| File | Date | Slug | Scope summary |
|---|---|---|---|
| [2026-06-15-bbw-online-ordering-line.md](2026-06-15-bbw-online-ordering-line.md) | 2026-06-15 | bbw-online-ordering-line | New à-la-carte Online Ordering catalog line (Square/Clover, hosted-only, Toast gated); 4 SKUs + builder fix + routing doc; uncommitted |
| [2026-05-30-discovery-layer.md](2026-05-30-discovery-layer.md) | 2026-05-30 | discovery-layer | New discovery layer (find → score → validate), tests + docs; uncommitted, commit plan included |
| [round-2-worker-runtime-fix.md](round-2-worker-runtime-fix.md) | (undated filename — content references 2026) | round-2-worker-runtime-fix | Codex Cloud-driven worker-runtime fixes; staging → main fast-forward |
| [2026-06-15-bbw-batch-b-demo-builds.md](2026-06-15-bbw-batch-b-demo-builds.md) | 2026-06-15 | bbw-batch-b-demo-builds | Bespoke demo builds for Batch B; 10/101 done (9 email + Jakes), 91 IG/FB remain — full pipeline + gotchas to finish |

When a new handoff is written, append a row above this one (newest at top).

## Pre-flight checks before writing a handoff

- Working tree state captured (`git status --short` output, even if dirty)
- Any files you renamed or moved are listed
- Any approval IDs in flight are linked
- Any test failures or `xfail` shrinks are noted
- If you opened a draft PR, link it
- If you stopped because of a stop condition, say why and what would unblock you

## Pre-flight checks before consuming a handoff

- Confirm the date in the filename matches "recent enough" for your task
- Confirm the working tree state at the bottom of the handoff matches
  the current `git status` — if it doesn't, the handoff was written
  during in-flight work and you may be picking up a partial state
- Read the most recent handoff first, then older handoffs as needed
- If two handoffs disagree, the newer one wins; flag the conflict in
  your own handoff at session end
