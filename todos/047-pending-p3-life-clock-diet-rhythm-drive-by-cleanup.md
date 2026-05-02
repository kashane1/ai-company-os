---
status: pending
priority: p3
issue_id: 047
tags: [code-review, life-clock, ios, cleanup]
dependencies: []
pr: https://github.com/kashane1/ai-company-os/pull/21
---

# Life Clock — diet rhythm PR review nits

## Problem Statement

The multi-agent review of PR #21 (diet rhythm + whole-food anchor + life-impact framing) found **no P1 issues, no real P2 issues, and three minor P3 cleanups**. None block merge. This todo bundles them as one follow-up.

The P2 finding from security-sentinel ("QuickLog lacks visible disclaimer despite ED-adjacent rhythm prompts") was confirmed as a **false positive** — `DisclaimerBanner()` is already mounted in `QuickLogSheet.swift:171` and renders inside the form, beneath all sections including the new Rhythm picker. Discarded.

## Findings

### Finding 1 — Doc comment overstates disclaimer reuse (P3 cosmetic)

**Source:** security-sentinel
**Location:** `products/life-clock-ios/Sources/Services/LifeClockConfiguration.swift` — comment on `medicalDisclaimer`

The comment claims the disclaimer is "Reused in onboarding, QuickLog, Profile, SafetyNet, Paywall, and Today (V1.2.0)." That's accurate — but the *short* `lifespanShortDisclaimer` is only used on Today. Tighten the comment so future readers don't assume `lifespanShortDisclaimer` propagates to all five sites.

### Finding 2 — Out-of-scope drive-bys in commit (P3, possibly real prior work)

**Source:** code-simplicity-reviewer
**Location:** `products/life-clock-ios/Sources/App/LifeClockStore.swift`

Two changes appear in the commit that aren't documented in the plan or PR body:
- `todayEstimate = clockEngine.calculateBaseline(profile: profile)` added inside `completeOnboarding(...)` (~line 380).
- `setBodyMetrics(heightCm:weightKg:)` new function (~12 lines).

These were pre-existing uncommitted local modifications on the branch base when the work began and got swept into the commit because the file was edited and staged. They may be legitimate parallel work the founder is in the middle of (a body-metrics editor in Profile?). **Action:** confirm with the founder. If real work, move to a separate PR with its own tests; if stale/unwanted, revert via follow-up commit.

### Finding 3 — Confidence-by-evidence ternary in `dietDriver` (P3 speculative)

**Source:** code-simplicity-reviewer
**Location:** `products/life-clock-ios/Sources/Engines/ClockEngine.swift` — within `dietDriver`

The new logic downgrades confidence to `.low` when only rhythm/anchor contribute. This is correct evidence-weighting but **isn't surfaced anywhere user-facing yet** (no UI reads diet-driver confidence specifically). If a future surface needs it, this lights up automatically; if not, it's dead nuance worth ~6 lines.

**Action:** keep for now (it's tested and cheap). Re-evaluate if the engine-confidence surface stays unused after TestFlight.

## Proposed Solutions

### Option A — Fix all three in one follow-up commit (recommended)

- Tighten the disclaimer comment (1 line).
- Either revert the `setBodyMetrics`/baseline drive-bys OR document them with a follow-up plan + tests.
- Leave the confidence ternary for now; remove only if the engine-confidence surface stays unused after TestFlight.

**Effort:** Small (1–2 hours including test verification).

### Option B — Defer all three; merge as-is

P3s, all noise-level. None affect user behavior. Acceptable to ship.

**Effort:** None now; revisit during App Review prep if anything surfaces.

## Recommended Action

(Triage required.)

## Technical Details

**Affected files:**
- `products/life-clock-ios/Sources/Services/LifeClockConfiguration.swift`
- `products/life-clock-ios/Sources/App/LifeClockStore.swift` (drive-by review)
- `products/life-clock-ios/Sources/Engines/ClockEngine.swift` (no change unless confirmed dead)

**No database changes. No migration concerns.**

## Acceptance Criteria

- [x] Disclaimer comment in `LifeClockConfiguration` accurately scopes which constants ship to which surfaces. (Resolved 2026-05-02 — `lifespanShortDisclaimer` doc-comment now states "Today (only)" and points other surfaces to `medicalDisclaimer`.)
- [ ] `setBodyMetrics` and `completeOnboarding` baseline-recompute either (a) have a documented plan, tests, and PR description coverage, or (b) are reverted. **Needs founder confirmation** that these are intentional in-flight work before action.
- [ ] Decision on confidence-by-evidence ternary recorded (keep or remove) with rationale. **Deferred** — explicit recommendation is keep until engine-confidence surface is exercised post-TestFlight.

## Work Log

- **2026-05-02** — Created from PR #21 multi-agent review (security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer). Pattern-recognition and agent-native both passed cleanly. No P1 / P2 findings.
- **2026-05-02** — Resolved Finding 1 (doc comment clarified to scope `lifespanShortDisclaimer` to Today only). Build verified. Findings 2 and 3 deferred pending founder input / TestFlight feedback.

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/21
- Plan: [docs/plans/2026-05-02-feat-life-clock-diet-rhythm-and-copy-pass-plan.md](docs/plans/2026-05-02-feat-life-clock-diet-rhythm-and-copy-pass-plan.md)
- Prior pattern review of plan: deepen-plan agent run on 2026-05-02
