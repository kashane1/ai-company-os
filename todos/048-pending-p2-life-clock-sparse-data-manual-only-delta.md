---
status: pending
priority: p2
issue_id: "048"
tags: [ios, life-clock, healthkit, sparse-data, product]
dependencies: []
---

# Life Clock sparse-data manual-only delta policy

Clarify and implement what Today should do when Apple Health is unavailable, not yet authorized, or currently returning no useful signal, but the user still saves a manual check-in.

## Problem Statement

The sparse-data polish pass exposed a product gap: the app now honestly says when it cannot currently see Apple Health data, but a saved manual check-in still does not move the same-day minute estimate. The user can log diet, alcohol, smoking, and strength, yet Today remains in a "waiting on data" state because `LifeClockStore.refreshFromHealthKit()` only computes a daily delta when a `DailyHealthSnapshot` exists.

This is bigger than copy. It changes the product's stance on whether manual input can temporarily drive the clock when passive signal is dark.

## Findings

- `LifeClockStore.refreshFromHealthKit()` only calls `clockEngine.calculateDailyDelta(...)` inside the `if let snapshot` branch in [products/life-clock-ios/Sources/App/LifeClockStore.swift](/Users/simons/ai-company-os/products/life-clock-ios/Sources/App/LifeClockStore.swift:204).
- `ClockEngine.calculateDailyDelta(...)` requires a concrete `DailyHealthSnapshot`, so manual habit signals currently have no engine path when HealthKit returns `nil`.
- The sparse-data polish pass now lowers confidence to `low` and suppresses the fabricated `0 min` headline, which makes this remaining gap more visible rather than hiding it.
- This affects denied, `notDetermined`, and authorized-but-empty states equally; the app cannot distinguish denial from missing data by design.

## Proposed Solutions

### Option 1: Keep manual-only days non-numeric

**Approach:** Preserve the new sparse headline until passive Apple Health data exists, even if a manual check-in is saved.

**Pros:**
- Strictest interpretation of "confidence is shipped, not hidden"
- Avoids over-weighting self-report
- Minimal engine complexity

**Cons:**
- User action can feel unrewarded on the same day
- Quick Log copy may need more framing so the behavior feels intentional

**Effort:** 1-2 hours

**Risk:** Low

---

### Option 2: Allow bounded manual-only delta

**Approach:** Introduce a manual-only delta path with conservative caps when HealthKit is unavailable for the day.

**Pros:**
- Gives immediate payoff for sparse-data users
- Makes Quick Log feel more consequential

**Cons:**
- Changes core clock semantics
- Needs careful confidence and copy treatment to avoid fake precision

**Effort:** 4-6 hours

**Risk:** Medium

---

### Option 3: Show a temporary "banked for tomorrow" payoff

**Approach:** Keep the headline non-numeric today, but show that manual check-ins were saved and will shape the next justified update once Apple Health signal returns.

**Pros:**
- Honest about current uncertainty
- Still rewards action with visible acknowledgment

**Cons:**
- Adds another intermediate state to Today
- Could feel abstract if not explained clearly

**Effort:** 3-5 hours

**Risk:** Medium

## Recommended Action

To be filled during triage.

## Technical Details

**Affected files:**
- [products/life-clock-ios/Sources/App/LifeClockStore.swift](/Users/simons/ai-company-os/products/life-clock-ios/Sources/App/LifeClockStore.swift:182)
- [products/life-clock-ios/Sources/Engines/ClockEngine.swift](/Users/simons/ai-company-os/products/life-clock-ios/Sources/Engines/ClockEngine.swift:345)
- [products/life-clock-ios/Sources/Features/Today/TodayView.swift](/Users/simons/ai-company-os/products/life-clock-ios/Sources/Features/Today/TodayView.swift:166)
- [products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift](/Users/simons/ai-company-os/products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift:167)

**Related components:**
- `HealthKitServiceProtocol`
- sparse-data copy on Today / History / Profile
- confidence model and headline rendering

**Database changes:**
- No schema change required for Options 1 or 3
- Option 2 may still avoid schema changes if it reuses existing ledger and estimate persistence

## Resources

- Sparse-data polish request from 2026-05-08
- [docs/products/life-clock/vision.md](/Users/simons/ai-company-os/docs/products/life-clock/vision.md)

## Acceptance Criteria

- [ ] Product direction chosen for manual-only days
- [ ] Today behavior matches the chosen policy in denied, `notDetermined`, and empty-authorized states
- [ ] Copy explains the chosen policy without implying unjustified precision
- [ ] Automated coverage exists for the selected behavior

## Work Log

### 2026-05-08 - Sparse-data polish discovery

**By:** Codex

**Actions:**
- Audited denied / `notDetermined` / empty-authorized HealthKit states during the sparse-data polish pass
- Confirmed the current engine computes same-day deltas only when a `DailyHealthSnapshot` exists
- Queued this as a product-scoped follow-up instead of silently changing clock semantics

**Learnings:**
- Honest sparse-data copy makes the underlying manual-only policy gap much more visible
- This decision changes product behavior, not just UI language

## Notes

- This is intentionally queued as Feature-tier work, not bundled into the sparse-data polish patch.
