---
status: pending
priority: p2
issue_id: 026
tags: [code-review, life-clock, notifications, ux-correctness]
dependencies: []
---

# Morning-log doesn't suppress today's reminder

## Problem statement

The cancel-then-reconcile suppression model in `setTodayHabits` works
**only when the user logs after the reminder hour**. Trace:

1. Reminder hour = 20:00 (8 PM). User logs at 09:00.
2. `setTodayHabits` calls `cancelTodayUntilTomorrowMorning()` — removes
   pending request.
3. `setTodayHabits` calls `reconcileNotifications()` — which calls
   `setSchedule(enabled: true, hour: 20, tone: …)`.
4. `setSchedule` adds a fresh `UNCalendarNotificationTrigger(dateMatching:
   {hour:20, minute:0}, repeats: true)`.
5. iOS computes the next match: **today 20:00** (now is 09:00, hasn't
   passed yet). Notification fires tonight.
6. User: "I already logged this morning, why is the app nagging me?"

This breaks the implicit contract of every habit-tracker reminder
("I just did the thing, don't ping me about it again today").

Severity: P2 — real UX defect, should-fix before TestFlight goes
external. Not a crash, not data loss, but the kind of behavior that
gets called out in beta feedback and erodes trust in the founder-pack
"agency over fear" stance.

## Findings

From data-integrity-guardian on commit 5b7a403:

> `setTodayHabits` cancels then immediately re-`reconcile`s, which
> calls `setSchedule` and re-adds the repeating trigger. iOS fires
> the next match. If the user logs at e.g. 09:00 and the reminder
> hour is 20:00, today's 20:00 fire is NOT suppressed — they log,
> then still get pinged tonight. The "cancel-on-log" design only
> succeeds when log time > reminder hour.

The plan's design assumed evening-loggers (who hit `setTodayHabits`
after the day's hour has passed). Morning-loggers, who are arguably
the more disciplined habit-tracker user, fall through.

## Proposed solutions

### Option 1: Persist `lastSuppressedDate` on UserProfile + branch in `setSchedule`

Add `var lastSuppressedDate: Date? = nil` to `UserProfile`.
`setTodayHabits` sets `profile.lastSuppressedDate = startOfDay(now)`
and saves. `reconcileNotifications` reads this and passes a
`suppressTodayIfBefore: Date?` argument into `setSchedule`. If
`now < hour` AND `lastSuppressedDate == today`, schedule a
*non-repeating* one-shot for tomorrow's hour instead of the
repeating trigger. The next morning, reconcile sees
`lastSuppressedDate < today` and reverts to repeating.

- Pros: Persists across launches. Handles edge case where user logs in
  morning, kills app, comes back at 7:55 PM — schedule was already
  fixed, so still no notification tonight. Mirrors the `paletteId` /
  `toneMode` field-level pattern for additive migration.
- Cons: One more SwiftData field; one more branch in setSchedule.
  ~25 LOC.
- Effort: Small.
- Risk: Low — additive migration with property-level default
  (matches the established team pattern).

### Option 2: Have `cancelTodayUntilTomorrowMorning` directly install a one-shot for tomorrow

Skip the reconcile call from `setTodayHabits`. Instead, the cancel
method removes the repeating trigger AND installs a non-repeating
trigger fixed at tomorrow's hour. Next bootstrap or next mutator
reconciles, which removes the one-shot and re-installs the repeating
trigger (whose next match is by then tomorrow anyway).

- Pros: No new SwiftData field. Lighter weight.
- Cons: Stateful — relies on "next reconcile happens before tomorrow's
  hour." If the app is killed and not reopened until late tomorrow
  evening, the repeating trigger isn't re-installed and the one-shot
  has already fired (or expired) — user gets no ping that day. Edge
  case; matters for users who log heavily and then ignore the app for
  multiple days.
- Effort: Smaller (~10 LOC).
- Risk: Medium — "next reconcile before tomorrow's hour" is an
  assumption that holds for daily-active users but quietly fails
  otherwise.

### Option 3: Document the limitation and ship as-is

Update the Profile footer copy: "We'll remind you to log if you
haven't already by this time **(unless your reminder hour has already
passed today)**." Plus add the `lastSuppressedDate` field as a
follow-up.

- Pros: Zero code change.
- Cons: Punts a real UX defect into footer copy that 90% of users
  won't read. Not the bar this product is aiming for.
- Effort: None.
- Risk: TestFlight feedback flags it; we end up doing Option 1
  anyway, but later.

## Recommended action

(Filled during triage — leaning Option 1 for correctness durability.)

## Technical details

**Affected files:**
- `products/life-clock-ios/Sources/Models/LifeClockSchema.swift`
  (add `lastSuppressedDate`)
- `products/life-clock-ios/Sources/Services/NotificationsService.swift`
  (extend `setSchedule` signature)
- `products/life-clock-ios/Sources/App/LifeClockStore.swift`
  (`setTodayHabits` writes the date; `reconcileNotifications` reads it)
- `products/life-clock-ios/Tests/LifeClockStoreTests.swift`
  (new test: morning-log + still-pre-hour case asserts schedule call
  receives `suppressTodayIfBefore: hour`)

## Acceptance criteria

- [ ] `UserProfile.lastSuppressedDate: Date?` field added with
      property-level default `nil`.
- [ ] `setTodayHabits` sets `lastSuppressedDate = startOfDay(now)`
      via the injected EngineClock.
- [ ] `reconcileNotifications` passes `suppressTodayIfBefore` into
      `setSchedule` when `now < hour` AND
      `startOfDay(lastSuppressedDate) == startOfDay(now)`.
- [ ] `setSchedule` installs a non-repeating one-shot for tomorrow's
      hour when `suppressTodayIfBefore != nil` AND iOS would otherwise
      fire today.
- [ ] New test: log at 09:00 with reminder hour 20:00 → mock receives
      `setSchedule(... suppressTodayIfBefore: today)` not the plain
      repeating-only call.
- [ ] CI grep gates still pass; no new `Date()`/`Calendar.current`
      outside `EngineClock` (the suppression date math uses the
      injected clock).

## Work log

- 2026-04-30 — Created during `/workflows:review` of commit `5b7a403`.
  Source: data-integrity-guardian agent on the actual implementation.

## Resources

- Plan: `docs/plans/2026-04-30-001-feat-life-clock-daily-reminder-plan.md`
- Commit: `5b7a403`
- Related past learning:
  `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`
  (property-level default for the new field)
