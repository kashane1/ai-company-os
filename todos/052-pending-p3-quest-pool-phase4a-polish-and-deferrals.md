---
status: pending
priority: p3
issue_id: 052
tags: [code-review, life-clock, ios, quest-pool, phase-4-polish, content]
dependencies: []
pr: https://github.com/kashane1/ai-company-os/pull/33
---

# Quest Pool Phase 4a — polish + deferrals from PR #33 review

## Problem Statement

Multi-agent review of PR #33 (Phase 4a — activity authoring + EligibilityFilter restoration) surfaced 2 CRITICAL + 6 IMPORTANT items resolved inline (see commit history), plus several NICE-TO-HAVE items deferred here.

## Findings

### Resolved inline (CRITICAL + IMPORTANT)

The fixes are already on PR #33 — listed for synthesis completeness:

- **CRITICAL #1 (architecture)**: `requiresSmoker` predicate misclassified `"former"` smokers as current smokers (`!= "none"`). Cessation-supportive slugs marked `requiresSmoker: false` would have been excluded for former smokers — exactly the wrong audience. **Fixed**: extracted `QuestSelector.isCurrentSmoker(_:)` with explicit enum-value mapping (`light` / `heavy` → current; `none` / `former` → not).
- **CRITICAL #2 (architecture)**: silent string-comparison brittleness on `smokingStatus` and `alcoholFrequency`. A future onboarding value (e.g. `"occasional"`) would have silently misclassified. **Fixed**: typed switch statements with `assertionFailure` on unknown values; both predicates moved to dedicated helpers (`isCurrentSmoker`, `isHabitualDrinker`).
- **IMPORTANT (architecture)**: 7-day cold-start threshold was duplicated between `discoveryDamp` and the eligibility filter. **Fixed**: extracted `QuestSelector.coldStartDayThreshold = 7`; both call sites read from it.
- **IMPORTANT (agent-native)**: exclusion-group typos in JSON would have silently degraded the conflict pass to a no-op. **Fixed**: new `QuestPoolTests.testProductionPoolExclusionGroupsAreInLockedVocabulary` keyed off a Swift `Set` mirroring the doc.
- **IMPORTANT (agent-native)**: forbidden-vocab arrays lived only in test code; vocab doc didn't list the words. **Fixed**: vocab doc now mirrors the lists and notes the test as runtime source of truth.
- **IMPORTANT (architecture, post-review add)**: cold-start non-strength user could in principle starve a genre. **Fixed**: new `QuestPoolTests.testActivityIsReachableForDefaultColdStartProfile` confirms ≥1 activity slug is eligible for the default profile.
- **IMPORTANT (simplicity)**: `EligibilityFilter.unrestricted` static was unused. **Fixed**: removed.
- **IMPORTANT (simplicity)**: `EligibilityFilter` doc-comment over-explained 5 fields in 12 lines. **Fixed**: halved; per-field semantics now live as terse one-liners + delegated to `QuestSelector.isEligible`.
- **IMPORTANT (simplicity)**: tone-parity Gate-3 comment claimed "fails compilation here" but the assertion is runtime. **Fixed**: comment rewritten to describe what it actually checks (non-empty intent / metric / unit at load time).

### P3 still open

1. **TimeOfDayWindow recorded but non-routing** (architecture-strategist + agent-native + simplicity, all flagged) — every authored 4a slug stores `timeOfDay: "anytime"`. The field is forward-compat for a future time-of-day refresh hook, but until that hook lands, 4b/c authors might assume the selector honors it. Mitigation options: (a) drop `timeOfDay` until a slug consumes it; (b) add a debug-only test that fails if any non-`anytime` value ships before the routing hook is wired. Recommendation: defer to Phase 4b or whenever the routing hook lands, whichever is sooner.

2. **Internal duplication in 30 activity slugs** (simplicity #4) — four "easy short walk" slugs are functionally close (`easy-walk-10.v1`, `cooldown-walk.v1`, `gentle-stroll.v1`, `deload-walk-10.v1`); three 15-min stroll slugs (`recovery-day-walk.v1`, `easy-day-stroll.v1`, `evening-stroll.v1`) are also similar. The intent grid in §4.1 of the Phase 4 plan separates `recovery-walk` from `deload-walk` semantically (post-workout recovery vs scheduled rest day), so the slug count is correct per plan, but copy could be sharpened. Tone-audit (separate review pass) flagged the recovery-walk cluster as the weakest tone-distinction zone — coach voice softens by default in that cluster. Phase 4 polish opportunity, not a blocker.

3. **Diet/sleep stub JSONs are bare `[]` with no schema reference** (agent-native NICE-TO-HAVE) — a future Phase 4b/4c agent must navigate to `activity.json` to learn the per-quest shape. Mitigation: ship a top-of-file comment in the vocab doc pointing to `activity.json` as the canonical template, OR ship a JSON-Schema file. Recommendation: add the pointer to vocab doc on the next Phase 4 PR.

4. **Intent grid hard-coded in two places** (agent-native NICE-TO-HAVE) — `QuestPoolTests.testProductionActivityIntentGridIsFullyCovered` lists the 10 activity intents inline; the diet + sleep grids only live in the plan. When Phase 4b lands, the test must be edited and the plan re-read to reconcile. Mitigation: lift all three grids into a single Swift constant (`ExpectedIntents.activity / .diet / .sleep`) consumed by the test and a future authoring helper. Phase 4b prep candidate.

5. **`sharesGroup` helper has one caller** (simplicity #6) — could be inlined as `!Set($0.exclusionGroups).isDisjoint(with: usedGroups)`. Borderline — keeping it as a named helper improves readability of the conflict pass. No action.

6. **Coach voice softens in recovery-walk cluster** (tone-audit) — `cooldown-walk.v1`, `gentle-stroll.v1`, `easy-day-stroll.v1` lack a strong "names the why" clause that distinguishes coach from gentle. Polish opportunity for content review pass before Phase 5a flag flip. Optional in 4a; can be addressed in any future content-only PR.

7. **`balance-stand-1min.v1` coach voice** mentions "balance with age" — faintly clinical/age-flagging tone vs the rest of the file. Consider rewording on next content pass.

## Proposed Solutions

**Option A: Phase 4b prep PR.**
Bundle items 3, 4 into a small refactor PR before Phase 4b authoring lands. Item 1 (timeOfDay) gets revisited at the same time depending on whether the routing hook lands first.

**Option B: Phase 5a hardening PR.**
Items 6, 7 (content polish on recovery-walk + balance-stand-1min) bundled into a content-only PR before flag flip.

**Option C: Defer items 5, 6, 7 to comment-only / content-only changes; address rest as preconditions for Phase 4b.**

## Recommended Action

(Filled during triage)

## Acceptance Criteria

- [ ] Item 1 (timeOfDay routing) decided: drop, keep with debug guard, or activate.
- [ ] Item 3 (vocab-doc template pointer) added on next Phase 4 PR.
- [ ] Item 4 (intent grid Swift constant) addressed in Phase 4b prep.
- [ ] Items 6, 7 reviewed in any content-only polish PR before Phase 5a.
- [ ] Item 2 (slug-count audit) considered — keep 30, or trim duplicates per plan-author judgment.

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/33
- Phase 4a focused plan: [docs/plans/2026-05-08-feat-quest-pool-phase-4a-activity-plan.md](docs/plans/2026-05-08-feat-quest-pool-phase-4a-activity-plan.md)
- Phase 4 + 5 plan: [docs/plans/2026-05-08-feat-quest-pool-phase-4-and-5-plan.md](docs/plans/2026-05-08-feat-quest-pool-phase-4-and-5-plan.md)
- Master plan: [docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md](docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md)
- Phase 3 polish + deferrals: [todos/050](050-pending-p3-quest-pool-phase3-polish-and-deferrals.md), [todos/051](051-pending-p3-quest-pool-phase3cd-polish-and-deferrals.md)
- Vocab doc: [docs/products/life-clock/quest-pool-vocab.md](docs/products/life-clock/quest-pool-vocab.md)
