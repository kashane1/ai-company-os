---
status: pending
priority: p3
issue_id: 028
tags: [code-review, quality, simplicity, life-clock, notifications]
dependencies: []
---

# Daily-reminder feature: simplicity polish

## Problem statement

Code review on commit `5b7a403` surfaced a bundle of small simplicity
+ test-coverage findings. None blocks ship; collectively they trim
~55–65 LOC and remove a couple of locale / future-regression bug
classes.

## Findings (numbered, with file:line refs)

### Real simplifications

1. **`cancelAll()` and `cancelTodayUntilTomorrowMorning()` do the same
   thing.** Both call
   `removePendingNotificationRequests(withIdentifiers: [identifier])`.
   The two-method API is "semantic" — the store calls them at
   different sites for clarity — but the runtime behavior is
   identical. Collapse to one method (`cancelPending()`); the store
   keeps its two calling-site comments without two API names.
   `NotificationsService.swift:73-79`. **−10 LOC.**

   *Caveat:* If todo #026 (morning-log suppression) is resolved by
   making `cancelTodayUntilTomorrowMorning` install a one-shot for
   tomorrow, this collapse becomes incorrect — the methods would
   diverge. **Resolve #026 before #028 finding #1.**

2. **Hour `Picker` over `8...22` with custom AM/PM labels** in
   `ProfileView.swift:67-76 + 206-213`. The deepen-pass best-practices
   research already noted that `DatePicker(displayedComponents:
   .hourAndMinute)` handles 12/24-hour locale automatically. Replace.
   The store-side 8…22 clamp stays as defense-in-depth (it's already
   there for App Intents / Shortcuts bypass). Drop
   `reminderHourLabel(_:)`. **−12 LOC, removes a locale bug surface
   (24-hour locales would currently see "20 PM" labels).**

3. **Onboarding `@State` flag reduction.** `OnboardingView.swift:22-24`
   declares three flags: `reminderRequestInFlight`,
   `reminderDecisionMade`, `reminderOptIn`. `reminderOptIn` is
   redundant — at the moment `advance()` runs it is always equal to
   `store.notificationAuthorizationStatus == .authorized`, which the
   store already exposes. Drop the flag, read store state inside
   `advance()` instead. **−5 LOC, one fewer state-sync class.**

4. **Tautological copy-string tests.**
   `NotificationsServiceTests.swift:8-24` pins exact title/body
   strings for each tone. Change copy → tests break for no semantic
   reason; copy regression isn't what tests should pin. The
   `testNoMortalityLexiconInAnyToneCopy` test on lines 31-43 is the
   real invariant — keep that, drop the three exact-string tests.
   **−18 LOC.**

5. **Doc-comment trims.**
   - `NotificationsService.swift:4-10` — 7-line doc paraphrasing what
     `setSchedule` + `cancelTodayUntilTomorrowMorning` already say by
     name. Trim to one line about the local-only / no-APNs constraint
     (the genuine WHY).
   - `LifeClockStore.swift:172-178` (setToneMode) and parallel comment
     in `resetForOnboarding` — the inline comment justifying
     `Task { await reconcileNotifications() }` runs longer than the
     code. Trim to one line.
   **−~10 LOC across the two files.**

6. **Inline `reminderFooterText`.** `ProfileView.swift:198-204`
   declares a computed property for a one-branch ternary. Inline
   into the footer view. **−4 LOC.**

### Test-coverage gap

7. **No test verifies `installForegroundDelegate` is called.** The
   `MockNotificationsService` no-ops it (the protocol method is
   `nonisolated`, can't safely write a counter from a nonisolated
   context without locking). A future refactor that drops the
   `installForegroundDelegate()` call from `LifeClockApp.init`
   would silently regress foreground-banner behavior with no test
   to catch it.

   Fix: switch `MockNotificationsService` from `actor` to `final
   class` with `nonisolated(unsafe) var installCount: Int = 0` +
   a `lock` for the counter, OR add a separate non-mock integration
   test asserting
   `UNUserNotificationCenter.current().delegate === ForegroundDelegate.shared`
   after `LifeClockApp.init` runs.

   **+~8 LOC, prevents a real regression class.**

### Operational hygiene

8. **Cold-launch double-reconcile.** On cold launch, both `.task` (via
   `bootstrap → reconcileNotifications`) AND
   `.onChange(of: scenePhase) { .active }` fire. Both call reconcile.
   Idempotent at the iOS API layer (remove-then-add same identifier),
   but wasteful. Gate the scenePhase observer with a `hasBootstrapped`
   flag, or skip the first `.active` transition.
   `LifeClockApp.swift:42-48`. **+~3 LOC, removes wasted work.**

9. **Reconcile inside save guard.** `setDailyReminder` and
   `setHideClock` use `try? modelContext.save()` then `await
   reconcile`. If the save throws (rare), `try?` swallows it and
   reconcile still proceeds with the in-memory mutation that didn't
   persist. State desync until next mutator. Wrap save in `do/catch`
   and skip reconcile on failure. **+~6 LOC across two methods.**

## Proposed solutions

### Option 1 (recommended): Apply findings 2–9 as a follow-up commit

Sequence:

1. Land #026 first (the real correctness fix; it changes the shape
   of `cancelTodayUntilTomorrowMorning`).
2. Then this todo: apply #1 (collapse to single `cancelPending`),
   #2 (DatePicker), #3 (drop `reminderOptIn`), #4 (drop tautological
   string tests), #5 (doc-comment trims), #6 (inline footer text),
   #7 (foreground-delegate test), #8 (de-dup cold-launch reconcile),
   #9 (save-guarded reconcile).

- Pros: Cleans up the feature before the next big change lands;
  prevents the simplicity findings from compounding.
- Cons: Two PRs / two commits in a row touching adjacent code.
- Effort: Small–medium. ~1 hour total.
- Risk: Negligible — pure cleanup + one new test.

### Option 2: Cherry-pick only #2 + #3 + #4 + #7

Skip the doc-comment / inline / save-guard items (5, 6, 8, 9). Lower
LOC delta but addresses the user-visible bug class (locale labels)
and the test-coverage gap.

### Option 3: Defer indefinitely

Cumulative cleanup debt; the next reminder-adjacent feature copies
the verbose pattern.

## Recommended action

Option 1, **after** #026 lands. Several of these findings (especially
#1) interact with the morning-log fix.

## Technical details

**Affected files:**
- `products/life-clock-ios/Sources/Services/NotificationsService.swift`
- `products/life-clock-ios/Sources/App/LifeClockStore.swift`
- `products/life-clock-ios/Sources/App/LifeClockApp.swift`
- `products/life-clock-ios/Sources/Features/Profile/ProfileView.swift`
- `products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift`
- `products/life-clock-ios/Tests/NotificationsServiceTests.swift`
- `products/life-clock-ios/Tests/LifeClockStoreTests.swift`

## Acceptance criteria

- [ ] `cancelAll`/`cancelTodayUntilTomorrowMorning` collapsed to one
      method (after #026 is resolved).
- [ ] Hour `Picker` replaced with `DatePicker(displayedComponents:
      .hourAndMinute)`; `reminderHourLabel(_:)` removed.
- [ ] `reminderOptIn` flag removed; `advance()` reads
      `store.notificationAuthorizationStatus` directly.
- [ ] Three exact-string copy tests removed; mortality-lexicon test
      stays.
- [ ] Doc comments on `NotificationsService` header,
      `setToneMode`/`resetForOnboarding` reconcile-Task lines trimmed.
- [ ] `reminderFooterText` inlined.
- [ ] `MockNotificationsService` records `installForegroundDelegate`
      calls; new test asserts the delegate is installed in
      `LifeClockApp.init`.
- [ ] scenePhase observer skips the first `.active` transition (or
      gates on `hasBootstrapped`).
- [ ] `setDailyReminder` and `setHideClock` skip reconcile on save
      failure (`do/catch` instead of `try?`).
- [ ] All existing tests still pass; CI grep gates clean.

## Work log

- 2026-04-30 — Created during `/workflows:review` of commit `5b7a403`.
  Source: code-simplicity-reviewer + data-integrity-guardian on the
  actual implementation diff (not the deepened plan).

## Resources

- Plan: `docs/plans/2026-04-30-001-feat-life-clock-daily-reminder-plan.md`
- Commit: `5b7a403`
- Related todo: `026-pending-p2-life-clock-morning-log-doesnt-suppress-today-reminder.md`
  (resolve first; #028 finding #1 depends on it).
