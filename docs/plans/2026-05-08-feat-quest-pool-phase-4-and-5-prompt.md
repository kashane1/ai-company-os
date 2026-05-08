# Prompt — kick off Phase 4 + 5 in a fresh Claude session

Paste the block below into a new chat. Self-contained context for a Claude session that hasn't seen the previous LFG cycles.

---

```
/lfg

Goal: ship Phase 4 (90-quest authoring) + Phase 5 (cutover) of the
Life Clock quest-pool affinity engine.

Context:

- Worktree: /Users/simons/ai-company-os/.claude/worktrees/eloquent-heyrovsky-c27bc0
  (cd there before doing anything else)
- Current state: PRs #30 (Phase 2 schema), #31 (Phase 3a+3b engines),
  #32 (Phase 3c+3d wiring) are open in stacked review on
  github.com/kashane1/ai-company-os. useQuestPoolEngine defaults
  false → production behavior unchanged today.
- Production JSON pool ships empty; only the 6-slug fixture pool
  exists. Phase 4 fills the production pool. Phase 5 flips the flag
  + retires the 15 legacy inlined Quest constructors.

Read these in order before starting:

1. docs/plans/2026-05-08-feat-quest-pool-phase-4-and-5-plan.md
   — your blueprint. Authoring template + intent grids + exclusion
   groups + tone voice guide + PR sequencing all live there.
2. docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md
   — master plan. Cite for D1–D10 design decisions; do not
   re-litigate.
3. docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md
   — Phase 3 plan. Cite for G1–G26 edge cases.
4. todos/050-pending-p3-quest-pool-phase3-polish-and-deferrals.md
   and todos/051-pending-p3-quest-pool-phase3cd-polish-and-deferrals.md
   — Phase 5a hardening prerequisites (items 2/3/5 in todo 051 must
   be addressed before flag flip).
5. products/life-clock-ios/Resources/QuestPool/fixture.json
   — your authoring template. The 6 slugs there are the voice + shape
   reference for the production pool.
6. products/life-clock-ios/Sources/App/ToneMode.swift
   — 40+ existing tone-keyed copy examples. Match the register.
7. products/life-clock-ios/Tests/QuestPoolToneParityTests.swift
   — the four quality gates this work must pass.

Pipeline:

- Run LFG steps 2–9 (skip step 1 / ralph-loop; not installed).
- Step 2 (/workflows:plan): the Phase 4+5 plan above is your origin.
  Don't re-derive design — write a focused execution plan.
- Step 3 (/deepen-plan): SKIP unless the agent finds genuine new
  gaps not covered by the master plan + Phase 3 plan deepening
  passes. Both are already deepened multiple times.
- Step 4 (/workflows:work): the meat. See "Authoring strategy" below.
- Step 5 (/workflows:review): expect at least one CRITICAL flag
  on tone parity drift or eligibility filter coverage. Apply P1 fixes
  inline.
- Step 6 (/resolve_todo_parallel): inline P1 fixes; capture P3 in
  a new todo file (next id is 052).
- Steps 7–8: SKIP. iOS Swift; flag stays default-false until the
  separate Phase 5a flag-flip PR. No web surface, no UI capture.

Authoring strategy:

- Phase 4 is content-heavy. 90 quests × 3 tones = 270 strings + targets
  + exclusion groups + eligibility filters. ONE LFG cycle may not
  fit at quality. The plan doc recommends splitting into 4a (activity
  + EligibilityFilter restoration), 4b (diet), 4c (sleep) as separate
  PRs.
- Ship as much as fits at high quality. If only 4a fits, ship 4a as
  a stacked PR and stop. The user can run /lfg again to continue.
- Quality bar: every authored slug must pass the four gates listed
  in the Phase 4+5 plan §4.6. A test that times out or a slug that
  fails parity is a P1 — do not paper over.
- Phase 4 output is a DRAFT pending human editorial review. The
  agent ships content that passes mechanical tests; a tone-aware
  reviewer signs off before Phase 5a.

Phase 5 sequencing:

- Phase 5a (flag flip) is a SEPARATE small PR. Do NOT bundle it with
  Phase 4 authoring PRs. Preconditions: all 90 slugs landed,
  authoring reviewer sign-off, hardening items 2/3/5 from todo 051
  closed.
- Phase 5b (delete legacy constructors) is a SEPARATE PR that waits
  for ≥1-week production bake of Phase 5a. The agent should NOT ship
  Phase 5b in the same LFG cycle as Phase 5a. If the user runs
  /lfg again after the bake, that's when 5b ships.

Branch strategy:

- New branch off claude/eloquent-heyrovsky-c27bc0-phase-3cd (the
  current head of PR #32) — call it
  claude/eloquent-heyrovsky-c27bc0-phase-4 or similar.
- Each Phase 4 sub-phase (4a/4b/4c) is a stacked PR. Phase 5a
  branches off the final 4c. Phase 5b branches off 5a.

Honesty constraint:

- Don't ship 90 quests with copy-paste-d tone variants. The four
  quality gates exist precisely to catch that.
- If the agent's tone-distinction starts feeling formulaic by quest
  20 of a genre, ship 20 + a P3 todo flagging the rest, not 30
  weak ones.
- Phase 4 quality bar overrides cycle-count target.

Safety:

- iOS Swift, no destructive operations, no remote APIs, no
  payments, no auth. Standard worktree commit + push + PR
  workflow per the LFG pattern from cycles 1–3.
- Do not flip useQuestPoolEngine to true in Phase 4 PRs. The flag
  flip is its own gated PR (Phase 5a).
- Do not delete the inlined Quest constructors in Phase 4 PRs.
  Constructor deletion is Phase 5b only.

Begin.
```

---

## Notes on the prompt

- Self-contained: a fresh Claude session reading this gets the worktree path, branch state, predecessor PRs, plan to follow, and quality bar without needing prior conversation.
- LFG-shaped: matches the pipeline pattern from cycles 1–3 so the agent knows what to do at each step.
- Honest about scope: Phase 4 is content-heavy and may not fit one cycle. The prompt explicitly OK-s shipping a partial PR rather than dropping quality.
- Phase 5 split: 5a (flag flip) and 5b (legacy deletion) are explicitly separate PRs with different gating. The prompt forbids bundling them.
- Branch strategy: stacked PRs continuing the chain from #30 → #31 → #32.
- Safety: no destructive ops, no flag-flip-by-accident, no constructor-deletion-by-accident.
