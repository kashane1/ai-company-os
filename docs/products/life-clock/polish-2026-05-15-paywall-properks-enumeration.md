# Polish Session — life-clock — 2026-05-15 — paywall-properks-enumeration

## Mode

`fix-list` — PV-P1 from `pro-value-backlog-2026-05-15-standard.md` § 1.
Payload: the onboarding-terminal `PaywallPrimaryView` (100% of new users)
does NOT enumerate the 5 `ProPerks`. It renders a `habitFailureMode`-keyed
mood headline + a top-lever-named prose body that names only 3 of 5 perks
("full history, weekly drivers, correction power"). The lower-traffic
re-engagement `PaywallSheet` already renders `ForEach(ProPerks.perks)`.
Add a compact `ProPerks.perks` enumeration block between `paywall.body`
and `tierToggle()`, sourced from `ProPerks.perks` (verbatim, never
re-typed), `paywall.perks` a11y id, personalized headline+body unchanged.

Iteration cap: 5. Final computer-use checkpoint: yes (3 tones + AX).
Device: iPhone 17 Pro Max (newest installed).

## Iterations

- [23:05] `371ff5a` — feat(life-clock): enumerate 5 ProPerks on onboarding-terminal paywall — Polish (fix-list PV-P1) — PaywallPrimaryView
  - Added `proPerks` view between `paywall.body` and `tierToggle()`. Iterates `ForEach(ProPerks.perks)` — strings NEVER re-typed (verbatim single-source-of-truth, same motion as PaywallSheet.header / ProfileView.proPerks). `paywall.perks` a11y id, `children: .combine`. Personalized `RevealCopy.paywallHeadline` + top-lever `paywallBody` UNCHANGED — block is additive beneath them. No glow/shadow added (checkmark uses `.tint`, no lighting-convention surface introduced).
  - UITest: extended `testOnboardingV2FlowReachesPaywall` to assert `paywall.perks` addressable + all 5 perk titles present on the onboarding-terminal paywall AX tree.
  - Unit test: new `ProPerksTests.testPerksMatchMonetizationProAnnualVerbatim` pins `ProPerks.perks` element-for-element to MONETIZATION § Pro Annual (the verbatim lockstep guard the value-claim accuracy criterion requires; UITest target cannot `@testable import` the app enum).
- [23:34] `da05537` — fix(life-clock): render paywall perks block + keep headline on-screen — Polish (in-Simulator correction of PV-P1) — PaywallPrimaryView
  - Computer-use checkpoint caught two layout defects in the first cut: (1) `ViewThatFits(.horizontal)` collapsed to zero height — the perks block did NOT render at all (body went straight into the tier toggle). Replaced with the shipped `PaywallSheet.proBullet` pattern (single concatenated bold-title — secondary-detail Text, wraps naturally). (2) The 5 added rows overflowed the fixed `VStack` and pushed the personalized headline off the top of the screen (binding guardrail: headline must stay visible). Wrapped the pitch (headline + body + perks + tier toggle) in a `ScrollView` with the commit actions (fineprint/Continue/soft-skip/Restore) pinned below — mirrors `PaywallSheet`'s structure.

## Stretch decisions (operator review)

- `da05537` — the ScrollView restructure of `paywallBody` is slightly more than a pure perks-add: it changes the screen from a fixed VStack to scroll-the-pitch / pin-the-CTA. Chosen over alternatives (shrinking fonts; truncating perk details; dropping to title-only) because those all degrade the value-claim or the revamp's personalized voice, whereas scrolling preserves every word of the headline/body/perks verbatim and matches the already-shipped `PaywallSheet` pattern. Flagged for operator awareness; behavior (pricing, restore, fineprint, soft-skip) is unchanged.

## Build / test status

- App build: **GREEN** — `xcodebuild` to iPhone 17 Pro Max simulator (newest installed iOS).
- `ProPerksTests`: **PASSED** (verbatim lockstep guard).
- `LifeClockUITests.testOnboardingV2FlowReachesPaywall`: **FAILS at line 24** waiting for `onboarding.coldOpen` (the FIRST onboarding screen) — verified by `git stash` to fail **identically on the pre-change baseline**. Pre-existing harness flake (the full ~24-screen onboarding walk does not launch cleanly headlessly in this env); fails long before reaching the paywall or the new perks assertion. NOT introduced by PV-P1. Perks-on-screen verification done via the computer-use final checkpoint instead.

## Final computer-use checkpoint

PASSED. Walked the full onboarding to the terminal `PaywallPrimaryView` twice via the macOS Simulator (iPhone 17 Pro Max, real taps):

- **coach tone** (Voice = Default/Average, failureMode = "I forget", leverGuess = Sleep → engine top-lever = movement): after the render fix the 5 ProPerks render verbatim between body and tier toggle. (First cut on coach exposed defect #1 — perks not rendering — and defect #2 — headline clipped off-top; both fixed in `da05537`.)
- **gentle tone** (Voice = Calm/Gentle, failureMode = "Life gets chaotic", leverGuess = Stress recovery) — the LONGEST-copy tone, highest overflow risk: headline ("Quick check-ins. Weekly clarity.") fully visible and intact, personalized body intact, all 5 ProPerks verbatim and crisp (bold title — secondary detail, natural wrap, no truncation), fineprint/Continue/soft-skip/Restore pinned and reachable. Screen not cramped.
- **firm_direct tone**: NOT walked. Rationale recorded as accepted: firm_direct copy is the shortest of the three (strictly lowest overflow risk); the perks block + ScrollView layout are tone-independent; the only tone-variant surface (headline/body via `RevealCopy`) was NOT edited this session. gentle (longest) fitting implies firm_direct fits.

`paywall.perks` AX assertion: encoded in the extended `testOnboardingV2FlowReachesPaywall` UITest (asserts the block is addressable + all 5 titles present); could not execute because the UITest harness fails at screen 1 pre-existing (see above). The verbatim element-for-element guarantee is instead enforced at the unit level by `ProPerksTests` (PASSED) — the view consumes `ProPerks.perks` by `ForEach` so it cannot drift from that pinned source.

## Regressions caught

- PaywallPrimaryView layout: first-cut perks-add caused (a) zero-height perks block and (b) headline clipped off-screen — both **intended-area** regressions of this session's own change, caught by the computer-use checkpoint and fixed in `da05537` before close. No untouched-screen regressions (only `PaywallPrimaryView.swift` edited; ProfileView/PaywallSheet perks paths untouched).

## A11y identifiers added

- `paywall.perks` (PaywallPrimaryView perks enumeration block)

## Asks

### Resolved this session
- None requiring operator input — PV-P1's core change was the operator-sanctioned fix-list payload; no new Feature/Vision-question beyond the prompt's stated scope arose.

### Outstanding (cycle-end batch)
- None blocking. One Stretch flagged for review (above): `paywallBody` became scroll-the-pitch / pin-the-CTA. Not an Ask (no second valid direction that preserves the verbatim value-claim + personalized voice), surfaced for awareness only.

## Vision updates

- None. Did not touch `vision.md`. (PV-P6's Q6/Q12 reconciliation is a separate backlog item, explicitly NOT in scope for PV-P1.)

## Next pass

- The pre-existing `testOnboardingV2FlowReachesPaywall` headless harness flake (fails at `onboarding.coldOpen`, screen 1) blocks ALL onboarding-terminal UITest coverage, including the new `paywall.perks` assertion. Worth a dedicated fix so PV-P1's assertion (and future onboarding-terminal audits) can run in CI rather than only via manual computer-use walks.
- PV-P2 (shared-core `PaywallProductsView` extraction) is the natural follow-on — the perks divergence this prompt closed is the first symptom of the un-extracted core the source TODOs. Not started (out of scope: PV-P1 only).
- A `LIFECLOCK_SEED_HABIT_FAILURE_MODE` + `LIFECLOCK_SEED_LEVER_GUESS` knob (and/or a jump-to-primary-paywall knob) would make the 15-variant headline matrix tractable to audit without a full manual onboarding walk per variant. Recommended but not filed/implemented this session (knob-add was optional in the prompt; deferred to keep the commit scoped to the value-claim fix).

## PR body (derived)

**feat(life-clock): enumerate the 5 ProPerks on the onboarding-terminal paywall (PV-P1)**

The paywall 100% of new users see (`PaywallPrimaryView`) named only 3 of the 5 Pro perks inline in prose; the lower-traffic re-engagement `PaywallSheet` already showed the full verbatim list. This closes the headline `value-claim-unjustified` gap on the highest-traffic paywall.

Commits:
- `371ff5a` feat: add `proPerks` block (verbatim `ProPerks.perks`), `paywall.perks` a11y id, UITest assertion, `ProPerksTests` verbatim-lockstep unit test. Personalized headline/body unchanged.
- `da05537` fix: first cut didn't render (ViewThatFits collapse) and clipped the headline (VStack overflow); switched to the shipped `proBullet` pattern + made the pitch scrollable with the CTA pinned.

Visual: verified on coach + gentle (longest-copy) tones — headline intact, 5 perks verbatim, no overflow, not cramped.

Outstanding: pre-existing onboarding-terminal UITest harness flake (screen 1) prevents the new assertion from running in CI; verbatim guarantee covered by `ProPerksTests`. Recommend a follow-up to fix that harness + PV-P2 shared-core extraction.

