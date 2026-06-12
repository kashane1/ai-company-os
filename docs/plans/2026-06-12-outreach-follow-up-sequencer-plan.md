---
status: open
change_id: outreach-follow-up-sequencer
owner: kashane
last_reviewed: 2026-06-12
---

# Follow-up Sequencer (draft-only) — Implementation Plan (2026-06-12)

> **TL;DR** — Item 6 of the BBW v2 build list. ~60% of the machinery already
> shipped with items 1 (due-queue) and 5 (reply-sync): `next_touch_at` exists,
> the dashboard surfaces a "Due now" queue, replies clear pending follow-ups, and
> suppression already excludes. This plan closes the three real gaps: (A) replace
> the flat +3-day cadence with a **per-step +4 / +8 schedule that hard-stops after
> touch 3**, derived from the outbound touch count (no schema change); (B) make the
> dashboard surface a **step-aware follow-up draft** instead of re-showing touch-1
> copy; (C) source the "one new concrete observation" with a **hybrid honest
> strategy** — a verified line from the content brief when one exists, else a
> shorter re-pitch of the already-verified gap, never a fabricated claim. All four
> channels (email/SMS/call/DM) get follow-up variants. Nothing sends; the boundary
> is unchanged.

## Decisions locked (2026-06-12)

- **Observation source:** Hybrid. Parse the content brief's verified "What's true
  about the work" lines, rotate in one *unused* line per step; when none are
  available, fall back to a shorter re-pitch of the same already-verified gap.
  Never invent. Honors the "brief is the only source" guardrail and still ships a
  draft for every prospect.
- **Channels:** All of email / SMS / call / DM get step-aware follow-up copy
  (mirrors how touch-1 works today; operator picks the channel per prospect).

## What already exists (do NOT rebuild)

| Capability | Where | State |
|---|---|---|
| `next_touch_at` on the lane row | [outreach_lane.py:109](../../packages/agency/outreach_lane.py) | flat +3d, never stops |
| Due-queue compute + chip + "Due first" sort | [outreach_actions.py:414](../../packages/agency/outreach_actions.py), [outreach_panel.py:136](../../packages/dashboard/outreach_panel.py) | ✓ done |
| Replies cancel follow-ups | reply-sync → `set_row_status(REPLIED)` → `TERMINAL_STATUSES` clears `next_touch_at` | ✓ done |
| Suppression excludes from queue | `due = … and not suppressed` | ✓ done |
| Per-channel draft + deep-links | [outreach_messages.py](../../packages/agency/outreach_messages.py) | step-agnostic (touch-1 only) |
| Outbound touch counts | `OutreachStore.touch_summary()` (outbound-only) | ✓ available |

## The three gaps to close

### A. Per-step cadence + hard stop at 3 touches

Today every non-terminal touch stamps `next_touch_at = occurred_at + 3d` via
`_next_touch_for` / `_default_next_touch_at` ([outreach_lane.py:664](../../packages/agency/outreach_lane.py))
and never stops. Replace with a step schedule keyed by how many outbound touches
the prospect has *already* received (the just-logged touch is already in the store
when scheduling runs, since `record_touch` appends before bumping):

```
STEP_CADENCE_DAYS = {1: 4, 2: 8}   # outbound_count_so_far -> days until next touch
# count >= 3 -> next_touch_at = ""  (sequence complete; drops out of the due-queue)
```

So: after touch 1 → due again in 4d (touch 2); after touch 2 → due in 8d (touch 3);
after touch 3 → cleared, max-3 enforced by code.

### B. Step-aware follow-up drafts

`build_messages_from_context` always emits the touch-1 body, so a due touch-2
prospect shows duplicate copy. The follow-up variants must be:
- **shorter** than touch-1 (obey `docs/agency/outreach-copy-rules.md`: one soft
  ask, plain punctuation, no em dash, no sales language),
- **re-reference the demo URL**,
- carry **one new concrete observation** (gap C),
- keep the `ref:<token>` footer on email (reply-sync still matches by it),
- keep the `'Reply "no thanks"…'` opt-out line (suppression depends on it).

### C. "One new concrete observation" — hybrid, honest

Sourcing order per step (never fabricate):
1. Parse the prospect's content brief (`state/prospects/sites/<place_id>/02-content-brief.md`,
   falling back to the scaffold-derived brief if the per-prospect one is absent)
   for verified lines under **"What's true about the work"**. Rotate in one line
   not already used by an earlier touch (touch 2 uses line 1, touch 3 uses line 2).
2. If the brief has no usable/remaining line, fall back to a shorter re-pitch of
   the **same already-verified `observed_gap`** the touch-1 copy used (no new
   claim, just a new framing + nudge). This is the floor that guarantees every
   due prospect has a draft.

Honesty guardrails carried through: a brief line is used verbatim/paraphrased only
from the "verified" section (never the `[HUMAN] picks` or guardrail sections);
low/no-confidence → fall back, don't pad.

## Build steps

### 1. New module: `packages/agency/outreach_sequencer.py`

> Named `outreach_sequencer` to avoid collision with the existing
> `packages/agency/follow_up.py`, which is the **client-retainer** automation
> (HubSpot/SMS) — a different concern.

Owns the pure step/cadence + observation logic so both the dashboard and CLI
paths share one implementation:

- `STEP_CADENCE_DAYS = {1: 4, 2: 8}` and `MAX_TOUCHES = 3`.
- `next_step_for(outbound_count: int) -> int` — the touch number a new send would
  be (`outbound_count + 1`), capped for display.
- `schedule_next_touch(outbound_count: int, occurred_at: str) -> str` — returns the
  ISO `next_touch_at` for the *next* touch, or `""` when `outbound_count >= MAX_TOUCHES`.
- `brief_observations(place_id, repo_root) -> list[str]` — parse the content brief's
  verified-work lines (cached per render). Empty list when no brief/section.
- `observation_for_step(place_id, step, ctx, repo_root) -> str` — pick the
  step-appropriate brief line, else the safe gap re-pitch fallback. Runs the result
  through `sanitize_outreach_copy`.

Pure functions, no sends, unit-testable with a tmp brief file.

### 2. Wire cadence into the two touch paths

Both must produce identical schedules (CLI `log --outcome sent` and dashboard
"Log sent" already mirror each other today):

- **`auto_bump_on_touch`** ([outreach_lane.py:401](../../packages/agency/outreach_lane.py)):
  accept an explicit `outbound_count: int | None`; when provided, compute
  `next_touch_at` via `outreach_sequencer.schedule_next_touch(...)` instead of the
  flat `_next_touch_for`. Keep terminal-status clearing.
- **`record_touch`** ([outreach_actions.py:445](../../packages/agency/outreach_actions.py)):
  it already holds the `store`; after `append_touch`, read the new outbound count
  (`sum` of `store.touch_summary()[place_id]` channel counts) and pass it into
  `auto_bump_on_touch`.
- **`log_manual_touch`** ([outreach_lane.py:272](../../packages/agency/outreach_lane.py)):
  same — when the outcome is a real send, read the count from its store and use the
  step schedule. Status-only outcomes keep current behavior.

Keep `FOLLOWUP_CADENCE_DAYS` / `_default_next_touch_at` as the back-compat default
for any caller that doesn't pass a count (and document that the sequencer is now
the source of truth).

### 3. Step-aware message bodies

- Extend `build_messages_from_context` ([outreach_messages.py:47](../../packages/agency/outreach_messages.py))
  with `step: int = 1` and `observation: str = ""`. `step == 1` → exact current
  copy (no behavior change, existing tests stay green). `step >= 2` → shorter
  follow-up bodies per channel that reference the URL again and weave in
  `observation`; email keeps the `ref:` footer + opt-out line.
- Add follow-up template variants under `state/prospects/outreach/` (e.g.
  `email/follow-up.md`, mirrored for sms/dm) so copy stays editable in the
  template library rather than hard-coded — consistent with the touch-1 templates.

### 4. Surface the right step in the dashboard

- In `_buttons_for_row` ([outreach_actions.py:233](../../packages/agency/outreach_actions.py)):
  the touch summary is already passed in. Compute `prior_outbound = sum(channel
  counts)`, `step = next_step_for(prior_outbound)`, resolve `observation =
  observation_for_step(...)`, and pass `step`/`observation` into the message
  builder so a due touch-2 prospect's buttons carry the follow-up copy.
- No UI change needed — the "Due now" chip, badge, and "Due first" sort
  ([outreach_panel.py](../../packages/dashboard/outreach_panel.py)) already render
  off `due` / `next_touch_at`. Optionally add a small "touch N/3" badge next to the
  due label (nice-to-have, not required by the spec).

### 5. Batch draft generation parity (optional but cheap)

`scripts/agency/build_outreach.py` writes `sites/<place_id>/outreach.md`. Extend it
to also emit the touch-2/touch-3 follow-up sections (using the same sequencer
helpers) so the on-disk drafts match what the dashboard surfaces. Keeps the
`draft_path` link useful for the operator.

## Boundaries & guardrails (unchanged)

- **No automated send.** The sequencer only schedules a *slot* and pre-writes a
  *draft*; a human still clicks send and confirms the touch. `apps/worker-outreach/`
  refuse-to-send boundary untouched.
- **No schema/policy edits.** Touch count derives from existing append-only touch
  rows; no new column, no `packages/schemas/` or `packages/policies/` change. (If a
  reviewer prefers an explicit `touch_no` column later, that's a separate,
  founder-approved migration — not needed for this build.)
- **Honesty.** Follow-up observations come only from the brief's verified section or
  re-pitch an already-verified gap; never fabricated. Em-dash/sales-language rules
  enforced via `sanitize_outreach_copy` + the copy-rules doc.
- **Suppression & replies stay authoritative.** Both already clear `next_touch_at`;
  the new cadence only ever *sets* it for live, non-terminal, non-suppressed rows.

## Tests (target: all green, existing suites unbroken)

New `tests/python/unit/test_outreach_sequencer.py`:
- `schedule_next_touch`: count 1 → +4d, count 2 → +8d, count ≥3 → `""`.
- Max-3 enforcement: a 3rd logged send clears `next_touch_at` (no touch 4).
- `observation_for_step`: brief line chosen when present (and not reused across
  steps); safe-gap fallback when the brief is empty; output passes
  `sanitize_outreach_copy` (no em dash).
- Reply cancels a pending follow-up (regression guard over reply-sync + cadence).
- Suppression keeps a due-scheduled row out of the queue (regression).

Extend existing suites:
- `test_agency_outreach_lane.py` — `auto_bump_on_touch` / `log_manual_touch`
  produce step cadence given a count.
- `test_agency_outreach_actions.py` — `record_touch` advances the schedule; due
  touch-2 row surfaces follow-up copy (different body than touch-1).
- `test_outreach_panel_render.py` — due badge still renders; optional touch-N badge.
- `test_outreach_messages*` — `step=1` output is byte-identical to today.

## Acceptance (from the spec)

- After a touch-1 send, the prospect appears in the due queue on **day 4** with a
  fresh, shorter draft that re-references the demo URL. ✓ (steps 2–4)
- A reply or suppression removes them. ✓ (already true; regression-tested)
- **Max 3 touches enforced by code.** ✓ (step 1, `MAX_TOUCHES`)

## Open implementation note

Reading the content brief per-row at render time is one file read per prospect on
a `127.0.0.1` local dashboard — acceptable, with a per-render cache in
`outreach_sequencer`. If profiling shows it matters at full roster size, precompute
the observation into the ledger row during `refresh_client_status`. Defer until
measured.
