# Polish Session — life-clock — 2026-05-10 — under-13-block-and-asc-update

## Mode

`fix-list`. Operator-approved 2026-05-10 from the cluster of recommendations in [09b_AGE_COMPLIANCE.md](09b_AGE_COMPLIANCE.md). Three shipping items from that brief:

1. **Item 1** — Under-13 hard block at DOB picker. COPPA actual-knowledge + FTC Feb 2026 safe harbor. Code change.
2. **Item 2** — ASC age-rating questionnaire updates for the 2025 4+/9+/13+/16+/18+ rewrite. Doc change.
3. **Item 5** — Privacy-policy under-13 statement. Doc change.

Iteration cap: 8. Final-check: yes (visual checkpoint of the new block screen).

Seed: none required for the doc changes; for the code change, a fresh-install boot on iPhone 17 (1A88AF54-4E90-40C2-8DB0-33B905A29951) with the rebuilt app, manually picking an under-13 DOB at `BaselineDOBView`.

## Context (why this session)

The 2026-05-09 session ([polish-2026-05-09-age-gate-thresholds.md](polish-2026-05-09-age-gate-thresholds.md)) audited the age-gate surface and queued five Vision-questions. Operator commissioned a best-practices research synthesis (now [09b_AGE_COMPLIANCE.md](09b_AGE_COMPLIANCE.md)), then resolved Q1 as Option (b) "hard-block under-13 at DOB picker" and deferred Q2/Q3/Q4/Q5 as risk-mitigation rather than compliance. This session implements the resolved Q1 and the two doc updates that ride along with it.

## Iterations

| Time | Commit | Type | Tier | Surface | Result |
|---|---|---|---|---|---|
| 00:30 | `599960b` | feat | Polish | Onboarding routing + AgeGate tests | Under-13 hard block; 6 new tests pin the routing decision (12 → block, exactly-13 → proceed, day-before-13 → block, 17 → proceed, adult → proceed, nil → proceed). |
| 00:42 | `6321c99` | docs | Polish | ASC_CHECKLIST.md | Re-running the age-rating questionnaire on the new 4+/9+/13+/16+/18+ tiers; documented expected answers + the once-per-onboarding mortality-reveal frequency ambiguity. |
| 00:48 | `dd1d1a4` | docs | Polish | PRIVACY_COMPLIANCE.md + 09b_AGE_COMPLIANCE.md | Under-13 + EU posture in the privacy doc; new compliance brief synthesizes the research and documents what's deferred (items 6–12). |
| 00:56 | `40821d7` | chore | Polish | OnboardingCoordinator | `LIFECLOCK_JUMP_TO=under13Block` fixture so polish audits can reach the block screen without driving the wheel DatePicker. |

### `599960b` — feat(life-clock): under-13 hard block at DOB picker

**What changed:**
- New `Under13BlockView` ([DataCollectionScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/DataCollectionScreens.swift)) — terminal screen with hand-raised icon, factual "Life Clock is for ages 13 and up." title, soft fat-finger language ("If you tapped the wrong date…"), and "Re-enter date of birth" CTA. Telemetry emits `screenAppeared("under13Block")` with no value bucket — the underlying DOB never reaches a sink.
- New `OnboardingScreen.afterBaselineDOB(birthDate:asOf:calendar:)` — single source of truth for the routing. `< 13 → .under13Block`. `>= 13` (or nil) `→ .baselineSex`.
- `OnboardingCoordinator` consults the helper from `BaselineDOBView`'s `onContinue`. The `Under13BlockView`'s "Re-enter" affordance clears `draft.birthDate` and pops the path so the next entry re-evaluates cleanly.
- 6 new `AgeGateTests` cases pinning the routing decision. All 16 tests in the suite pass (5 original + 5 from yesterday's session + 6 new).

**Why:** the COPPA actual-knowledge doctrine attaches the moment we collect a DOB resolving to age <13. The FTC February 2026 policy statement explicitly blesses "ask DOB → block" as a safe harbor that does NOT itself trigger verifiable-parental-consent obligations *if the operator acts on the result and does not collect personal info*. This is the cleanest defensible posture for v1, per [09b_AGE_COMPLIANCE.md](09b_AGE_COMPLIANCE.md) §2.

### `6321c99` — docs(life-clock): update ASC age-rating questionnaire to 2025 tiers

**What changed:** Phase 4 of [ASC_CHECKLIST.md](ASC_CHECKLIST.md) re-written for the new 4+/9+/13+/16+/18+ tiers. Old entries referenced the deprecated 12+/17+ system and the pre-fix inconsistency around alcohol/tobacco prompts ("user self-reports; under-18 users don't see these prompts" — true in QuickLog, **false in onboarding before yesterday's commit `35fdd54`**). New table reflects implemented behavior, expected result is **13+**, and includes an ambiguity flag for the once-per-onboarding mortality reveal frequency interpretation.

**Why:** Apple's July 2025 rating overhaul deadline was January 31 2026. Apps that don't re-run the questionnaire lose the ability to ship updates. Operator must complete the live ASC questionnaire before next submission; this doc gives them the answer set.

### `dd1d1a4` — docs(life-clock): under-13 + EU posture in PRIVACY_COMPLIANCE; add 09b age brief

**What changed:**
- [09_PRIVACY_COMPLIANCE.md](09_PRIVACY_COMPLIANCE.md) gains "Users under 13 (COPPA posture)" and "Users in the EU (GDPR-K posture)" sections. The COPPA section enumerates exactly what the under-13 hard block prevents (no HealthKit prompt, no SwiftData write, no telemetry value bucket, no paywall) and includes a suggested paragraph for the public-facing privacy policy URL that Apple's nutrition label points to.
- New [09b_AGE_COMPLIANCE.md](09b_AGE_COMPLIANCE.md) is the companion brief — synthesizes the 2026-05-09 research, documents which items are pre-launch blockers (1, 2, 5) vs deferred risk-mitigation (6–12), and records the operator's accepted residual-risk decisions for each deferred item so they can be re-opened later without re-research.

**Why:** the privacy policy is the user-facing artifact that backs the ASC nutrition label and the in-app block screen. Without it the implementation has no documented justification trail.

### `40821d7` — chore(life-clock): LIFECLOCK_JUMP_TO=under13Block fixture

**What changed:** `applyJumpFixtureIfNeeded()` accepts `under13Block` as a jump target; when used, seeds `draft.birthDate` to a 12-year-old DOB (2014-06-15) so the draft state is consistent with the block screen. All other jump targets keep the existing 1985 adult default.

**Why:** the wheel DatePicker is hard to drive headlessly during polish audits. A jump fixture lets future sessions reach the block screen with one launch flag. Used for the visual checkpoint of this session.

## Stretch decisions (operator review)

None this session. Every item shipped is Polish-tier, scoped to the three pre-launch blockers from [09b_AGE_COMPLIANCE.md](09b_AGE_COMPLIANCE.md).

## Asks

### Resolved this session

- Q1 from [polish-2026-05-09-age-gate-thresholds.md](polish-2026-05-09-age-gate-thresholds.md) — "DOB picker lower bound." Operator chose Option (b) "hard-block under-13" pre-session; this session implemented it.

### Outstanding (cycle-end batch)

None new. The deferred items are catalogued in [09b_AGE_COMPLIANCE.md](09b_AGE_COMPLIANCE.md) §6 with the operator's documented rationale for each deferral. Re-open that doc when adding any off-device data flow.

## Regressions caught

- None. Build green at every commit; AgeGate test suite (16/16) passes; cold-open and under13Block screens both render cleanly.

## A11y identifiers added

- `onboarding.under13Block` (screen)
- `under13Block.title`
- `under13Block.body`
- `under13Block.reenter`

These compound across sessions per the canonical skill rule — future XCUITests can target this screen by id without further source changes.

## Vision updates

No `vision.md` updates this session. The age-compliance posture lives in [09b_AGE_COMPLIANCE.md](09b_AGE_COMPLIANCE.md), which is the right home — `vision.md` covers product/tone questions; this is regulatory.

## Final check

Visual checkpoint via `LIFECLOCK_JUMP_TO=under13Block` on iPhone 17 (1A88AF54). The block screen renders with the persistent OnboardingHeader (mascot + "LIFE CLOCK" title + back chevron when applicable), hand-raised icon, factual title, soft fat-finger body copy, and the "Re-enter date of birth" CTA at the bottom. No console errors / faults / exceptions in the launch window. App terminated cleanly post-screenshot.

Test verification:
- `LifeClockTests/AgeGateTests` — 16/16 passing on iPhone 17 simulator runtime.
- `xcodebuild build` and `build-for-testing` — both green at every commit.
- The pre-existing `SubscriptionStore` Swift 6 actor-isolation warning is unrelated.

## Next pass

Per operator decision (2026-05-10), risk-mitigation items 6–12 from [09b_AGE_COMPLIANCE.md](09b_AGE_COMPLIANCE.md) §6 are deferred. Triggers to re-open:

- Adding any off-device data flow (analytics, backup, sync, server endpoints) — collapses the local-first defense for GDPR-K, makes per-jurisdiction age floors required.
- Adding an in-app DOB-editable profile field for an existing user — re-introduces actual-knowledge exposure post-onboarding.
- App Review rejection citing §1.1.1, §1.4.1, or §5.1.4 — would require items 6, 9, 10 to be reconsidered.
- Any move toward a Kids Category submission — completely different compliance regime.

Until then, the v1 compliance posture is fully documented and shippable.

## PR body (derived from this log)

```
feat(life-clock): under-13 age compliance — hard block + ASC update + privacy posture

## Summary

Implements the three pre-launch compliance blockers from
docs/products/life-clock/09b_AGE_COMPLIANCE.md — the new
companion brief that synthesizes Apple App Review + COPPA + GDPR-K
research into a v1 posture for Life Clock.

* **Item 1 (code):** Under-13 hard block at the DOB picker. New
  `Under13BlockView` + `OnboardingScreen.afterBaselineDOB` routing
  helper, 6 new pinning tests. COPPA actual-knowledge + FTC Feb
  2026 safe-harbor.
* **Item 2 (docs):** ASC age-rating questionnaire re-run for the
  2025 4+/9+/13+/16+/18+ system; expected result 13+.
* **Item 5 (docs):** Under-13 + EU posture sections in
  PRIVACY_COMPLIANCE.md, with a suggested paragraph for the
  public-facing privacy policy.

Plus the chore that lets future polish audits reach the block screen
via `LIFECLOCK_JUMP_TO=under13Block`.

Items 6–12 (parental gate before paywall, EU 16-floor, symmetric
input-side gating, mortality-framing softening, etc.) are deferred
risk-mitigation per operator decision; rationale captured in
09b_AGE_COMPLIANCE.md §6 so they can be re-opened later without
re-research.

## Test plan

- [x] `xcodebuild build` and `build-for-testing` green
- [x] `LifeClockTests/AgeGateTests` 16/16 pass on iPhone 17
- [x] Visual: `LIFECLOCK_JUMP_TO=under13Block` reaches the block
      screen on iPhone 17; copy + icon + CTA render cleanly
- [x] Visual: cold-open render unchanged on iPhone 17
- [ ] Operator: re-run the ASC age-rating questionnaire on the
      live console
- [ ] Operator: copy the suggested under-13 paragraph into the
      public-facing privacy policy URL

## Related

- docs/products/life-clock/polish-2026-05-09-age-gate-thresholds.md
  (yesterday's audit that surfaced the gap)
- docs/products/life-clock/09b_AGE_COMPLIANCE.md (the v1 posture
  brief this PR implements)
```

