# Polish Session — life-clock — 2026-05-08 — vision-notifications-audit

## Mode

`vision-driven`, audit-only. Operator-bounded: "purely audit + propose. Don't ship a notification-scheduling feature autonomously." No source edits in this session — only this log + queued Asks.

Iteration cap 6 (used 0 — audit was code-truth + a single launch screenshot). Final computer-use checkpoint: requested twice, **timed out at request_access**; operator likely AFK. Grounding fell back to source reading + a clean onboarded-scenario boot. See *Final-check status* at end of log.

Seed: `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_HEALTH_AUTH=authorized`, `LIFECLOCK_USE_MOCK_HEALTH=1`, `seedStreak=0`. Today screen captured at [.polish/goldens/notifications-audit/02_today_clean.png](../../../products/life-clock-ios/.polish/goldens/notifications-audit/02_today_clean.png).

## Iterations

None — audit-only. No commits to source.

## What ships today (the current state)

Read-only inventory, sourced from code (paths relative to `products/life-clock-ios/`):

### Architecture

- **One service**, one notification: `NotificationsService` actor at [Sources/Services/NotificationsService.swift](../../../products/life-clock-ios/Sources/Services/NotificationsService.swift). Identifier `daily-reminder`, fully local — `// Local-only daily-reminder service — no APNs, no backend.` The app never asks for push entitlements; everything is `UNUserNotificationCenter` calendar triggers.
- **Single chokepoint** for scheduling: `LifeClockStore.reconcileNotifications()` ([Sources/App/LifeClockStore.swift:652](../../../products/life-clock-ios/Sources/App/LifeClockStore.swift)). Every mutator that affects schedule (bootstrap, setTodayHabits, setToneMode, setHideClock, setDailyReminder, resetForOnboarding, scenePhase=.active) calls it. No drift across mutators by design.
- **Tone-aware copy** baked into the service: `NotificationCopy.body(for: ToneMode)` ([NotificationsService.swift:113](../../../products/life-clock-ios/Sources/Services/NotificationsService.swift)). Re-rendered on `setToneMode` via reconcile.
- **Foreground delegate** installed at app init ([LifeClockApp.swift:29](../../../products/life-clock-ios/Sources/App/LifeClockApp.swift)) so a notification fired with the app open still shows a banner.
- **Interruption level**: `.active`, **not** `.timeSensitive` — comment at [NotificationsService.swift:57-60](../../../products/life-clock-ios/Sources/Services/NotificationsService.swift) cites HIG. Correct call.

### Schedule shape

- **What:** one daily repeating reminder at the user-chosen hour. Calendar trigger, `repeats: true`.
- **When:** default 20 (8 PM). Hour clamped to **8…22** in `setDailyReminder` ([LifeClockStore.swift:613](../../../products/life-clock-ios/Sources/App/LifeClockStore.swift)) — defense-in-depth even though the picker UI also enforces it.
- **Suppression:** if the user logged habits today AND today's reminder hour hasn't passed, the repeating trigger is replaced by a one-shot at tomorrow's hour. Reconcile on next launch / mutator / scenePhase=active restores the repeating shape. Driven by `profile.lastSuppressedDate` ([LifeClockSchema.swift:66-72](../../../products/life-clock-ios/Sources/Models/LifeClockSchema.swift)). Closes the "user logged at 9 AM, still got pinged at 8 PM" bug (#026) cited in the comments.
- **Hard suppression on hideClock:** if `profile.hideClock == true` (the SafetyNet escape valve), `reconcileNotifications` calls `cancelAll()`. ✓ Load-bearing safety behavior.

### Permission flow

- **Onboarding step 5** ([OnboardingView.swift:221](../../../products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift)): copy reads *"Want a one-tap nudge if you haven't logged by 8 PM? Off by default — turn on here, or change it any time in Profile."* Two buttons: *Yes, remind me* / *No thanks*.
- *Yes* → `requestNotificationAuthorization` (presents iOS dialog) immediately. Schedule itself is installed only on Finish, after the profile is created ([OnboardingView.swift:307-308](../../../products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift)) — `if store.notificationAuthorizationStatus == .authorized { await store.setDailyReminder(enabled: true, hour: 20) }`.
- **Default state on first launch:** `dailyReminderEnabled = false` ([LifeClockSchema.swift:64](../../../products/life-clock-ios/Sources/Models/LifeClockSchema.swift)). The app schedules **nothing** unless the user opts in. Consistent with the vision's "passive first, manual second" decided constraint.
- **Profile surface** ([ProfileView.swift:55-98](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift)): Toggle + DatePicker (hour-and-minute display; the store-side clamp is the source of truth, picker tolerates any selection). Footer text:
  - *Default:* "We'll remind you to log if you haven't already by this time. One per day. Reminder time runs between 8 AM and 10 PM."
  - *Auth-denied:* "Notifications are disabled in iOS Settings → Life Clock. Re-enable there to receive reminders."

### Tone copy (already pinned by [NotificationsServiceTests.swift](../../../products/life-clock-ios/Tests/NotificationsServiceTests.swift))

| Tone | Title | Body |
|---|---|---|
| Gentle | Two minutes for yourself? | A quick daily check-in keeps your Life Clock honest. |
| Coach | Daily Check-In | A few quick signals keep your Life Clock honest. |
| Firm/Direct | Check in. | Yesterday is closed. Log it. |

Tests pin two invariants:

1. `testNoMortalityLexiconInAnyToneCopy` — even `firmDirect` notification copy must not contain `die / death / dying / lifespan / year(s) left / mortality / mortal`. Comment is explicit: *"Even Memento Mori (where the user actively chose dramatic in-app framing) gets neutral copy here because the notification meets the user OUTSIDE the app, on a Lock Screen or in front of others."* This is a contextual privacy/dignity rule already in code.
2. Distinct + non-empty across all three tones.

### Wrap-ups (NOT notifications)

- `WrapUpCoordinator` ([Sources/App/](../../../products/life-clock-ios/Sources/App/) — yesterday + weekly) gates **in-app sheets** that present on cold-launch when conditions are met. There is **no** scheduled notification that prompts the user to open the app for a weekly wrap-up. If the user goes 8 days without launching, the weekly wrap-up just waits — and the `weeklyRecencyDays = 14` config means a wrap-up older than two weeks is silently skipped.

## Operator's specific questions, answered against ground truth

**(a) What does the app currently schedule on first launch?**
Nothing. `dailyReminderEnabled` defaults `false`. The user sees the onboarding question at step 5 and must opt in. There is no separate weekly/wrap-up notification. There is no morning notification by default. There is exactly one notification class: `daily-reminder`.

**(b) When do they fire? User-controlled or hardcoded?**
User-controlled hour, hardcoded minute (00). Default 8 PM. Picker-controlled in Profile. Range 8 AM…10 PM (clamp in `setDailyReminder` — picker UI lets the user select any hour but the store rounds into the window). 6 AM cannot happen by construction.

**(c) Is there an in-app "set your morning time" affordance?**
There is a *time* picker in Profile, but the framing is **evening, not morning**: onboarding copy is *"if you haven't logged by 8 PM"*; default 20:00; clamp starts at 8 AM (so the earliest possible "morning" is 8 AM, not 6/7 AM). The shipped app commits to evening logging — the operator's hypothesis "probably morning nudge" is not what's in code. Worth a Vision-question to either ratchet evening into Decided constraints or open a morning option (see Ask 1).

**(d) Do tone modes affect notification copy?**
Yes, fully wired. `NotificationCopy.body(for:)` is called on every `setSchedule`. `setToneMode` triggers `reconcileNotifications` which re-renders the pending request with the new tone's copy. Tested.

**(e) Do they respect SafetyNet soft-mode?**
*Mostly.* Two actual safety paths exist:

1. **Hide the clock** (SafetyNet card 2 → `setHideClock(true)`) → `reconcileNotifications` → `cancelAll()`. The user's notifications stop entirely. ✓
2. **Switch to Gentle tone** (SafetyNet card 1 → `setToneMode(.gentle)`) → notifications re-render in Gentle copy. ✓

But there is no concept of "soft mode" beyond `hideClock OR tone == .gentle`. A user on `firmDirect` who briefly visits SafetyNet but doesn't take either action keeps getting Lock-Screen-visible Firm/Direct copy. The mortality-lexicon test partially handles the dignity concern (no death-language regardless of tone), but a Firm/Direct push at 8 PM that says *"Check in. Yesterday is closed. Log it."* is still notably terser than the Gentle equivalent.

The 6 AM Firm/Direct concern in the operator's prompt is **structurally impossible** today — the 8 AM clamp blocks it. Document this as Decided to lock the invariant in.

## Findings, classified

| # | Finding | Tier | Note |
|---|---|---|---|
| F1 | No weekly wrap-up notification — wrap-ups depend on the user opening the app | Vision-question | See Ask 1 |
| F2 | Default reminder is evening (20:00); operator hypothesis was morning. Vision doesn't ratchet either way | Vision-question | See Ask 2 |
| F3 | No SafetyNet → notification soft-coupling beyond hideClock + tone | Vision-question | See Ask 3 |
| F4 | Onboarding step 5: if iOS dialog returns `.denied`, in-flow has no fallback message — only the post-onboarding Profile footer surfaces this | Polish (out of scope this session) | Logged for next pass |
| F5 | 8…22 hour clamp is undocumented in vision; it's a load-bearing safety invariant (blocks 6 AM Firm/Direct pushes) | Vision-question | See Ask 4 |
| F6 | Default-hour `20` lives in two places: `LifeClockSchema.swift:65` and `OnboardingView.swift:308`. Constant duplication | Polish (out of scope this session) | Logged for next pass |
| F7 | Suppression mechanism (logged today → skip today's fire) is invisible to the user | Polish (out of scope this session) | Logged for next pass |
| F8 | No "you've not opened the app in 5 days" re-engagement nudge | Feature | See Ask 5 |
| F9 | Profile reminder toggle visually no-ops when notification auth is `.notDetermined` | Polish/Stretch (out of scope this session) | Discovered during checkpoint; see Final-check status |

## Stretch decisions

None — audit-only.

## Asks

### Resolved this session

None.

### Outstanding (cycle-end batch)

The operator asked for "options for any gaps as Vision-questions." Five Asks, prioritized.

---

**Ask 1 — Weekly wrap-up notification.** *(F1, Vision-question)*

The app has a weekly wrap-up sheet (`WrapUpCoordinator` → `WrapUpSheet`), but it only fires when the user cold-launches the app. The vision §"Core daily experience" / weekly cadence implies returning weekly is part of the loop, but there's no nudge that pulls them back. Right now, a user who skips the app on Sunday and Monday silently misses the weekly wrap-up forever (14-day recency window). Three concrete options:

- **A — Don't ship.** Weekly wrap-ups are a "found it when you opened the app" surprise, not a scheduled ceremony. Decided constraint: *"Wrap-ups are pull, not push."* Reasoning: aligns with "default is motivating, not punishing"; avoids a Sunday-evening guilt trip.
- **B — One weekly notification, opt-in alongside daily reminder.** Sunday 7 PM (one hour before the daily reminder hour-clamp range starts wrapping). Tone-aware copy. New schema field `weeklyReminderEnabled` (default `false`). Same `NotificationsService` actor, second identifier. New section in onboarding (or rolled into existing daily-reminder step as a checkbox).
- **C — Implicit: when daily reminder fires on a wrap-up-pending day, replace the body.** No new permission, no new schema field. The Sunday 8 PM `daily-reminder` body becomes *"Your week's wrap-up is ready inside."* once per week. Reuses the existing schedule. Risk: changes the implicit contract of "this notification means today, not the week."

Recommendation: **A, then revisit after retention data.** App is pre-revenue; adding a second notification now is a feature-tier ship without engagement evidence. Keep `pull, not push` as the line.

---

**Ask 2 — Morning vs. evening reminder framing.** *(F2, Vision-question)*

Current shipped copy + default commits to *evening logging* ("if you haven't logged by 8 PM"). The operator's prompt assumed a morning nudge. Vision §"Core daily experience" reads the loop as: *open Today → see yesterday's settled hands → see today's delta → take one action → close motivated*. That description fits both timings:

- **Morning interpretation.** The hands are already moved by yesterday's HK data; the user opens to see the trajectory and pick a quest for *today*. The reminder pulls them in to start their day.
- **Evening interpretation.** The user logs *today's* habits before bed; the morning loop is then about reading the result. The reminder pulls them in to close the day.

These are different products in subtle ways. Three options:

- **A — Ratchet evening as Decided.** Add to vision: *"Daily reminder is an evening close-the-day cue. Hour 8…22 is the supported window. Morning reminders are explicitly out of scope in v1."* Lock the picker as-is. Cleanest. Closes the question.
- **B — Open morning + evening as user choice.** Two opt-in toggles, two reminder hours, two notifications. Doubles the schema, doubles the copy variants, opens two paths through SafetyNet behavior.
- **C — Single reminder, expanded clamp (e.g. 6 AM…10 PM), let the user pick either interpretation.** Lowest implementation cost; highest UX-ambiguity cost (the *copy* still says "if you haven't logged by 8 PM" — needs a rewrite to be timing-neutral, e.g. "We'll nudge you at this time if you haven't logged today.")

Recommendation: **A.** The product is shipping evening; ratchet that. If morning becomes a research-backed need later, B is reachable.

---

**Ask 3 — SafetyNet → notification soft-coupling.** *(F3, Vision-question)*

Today's tone-to-notification mapping is 1:1 with the user's in-app tone. A user on Firm/Direct who briefly opens SafetyNet but doesn't change tone or hide the clock keeps getting "Check in. Yesterday is closed. Log it." on their Lock Screen. The mortality-lexicon test prevents the worst (no death-language ever), but Firm/Direct copy is *colder* than Gentle and that coldness travels outside the app.

Three options:

- **A — Status quo.** The user explicitly chose Firm/Direct in onboarding; overriding outside the app is paternalistic. The mortality test is the only contextual override needed.
- **B — Lock all notification copy to Gentle regardless of in-app tone.** Strongest dignity guarantee; weakest faithfulness to user's chosen voice. The Firm/Direct user gets a softer Lock Screen, harder in-app.
- **C — Add a Profile/SafetyNet toggle: "Use gentler copy in notifications".** Default off. One row under the daily-reminder DatePicker. Gives the anxious-prone user an explicit lever without changing in-app tone. Smallest change with the highest user-control payoff.

Recommendation: **A or C.** B is too paternalistic. Status quo is defensible because the mortality test already encodes the contextual rule. C is the most operator-minded if Lock-Screen dignity matters per-user.

---

**Ask 4 — Document the 8…22 clamp as a Decided constraint.** *(F5, Vision-question, lower stakes)*

The clamp `max(8, min(22, hour))` in `setDailyReminder` is load-bearing — it makes the 6 AM Firm/Direct push the operator worried about *structurally impossible*. Today this lives in code only. Proposal: add to vision Decided constraints:

> **Daily reminder hour is bounded to 8…22.** Source: `setDailyReminder` clamp. Reasoning: prevents a Firm/Direct nudge from arriving at a sleeping or vulnerable hour, even if a future App Intent or Shortcut bypasses the picker UI. Widening this window is a Vision-question.

No code change needed; this is an operator pen-stroke on `## Decided constraints` in vision.md.

---

**Ask 5 — Re-engagement nudge after N days of no opens.** *(F8, Feature)*

Right now: a user toggles off the daily reminder, or never opts in, and the app never speaks again until they open it. Local notifications can do dynamic-rescheduling re-engagement (e.g. "you haven't checked in for 5 days"). Trade:

- **Pro:** habit apps live or die on retention; this is table-stakes for App Store competitors.
- **Con:** crosses from "passive nudge to log" into "marketing nudge to open" — the line the vision is careful about.

Two options:

- **A — Don't ship.** Stay on the "agency, not fate" / "passive first" line. The user who turned off reminders meant it.
- **B — Ship as a separate opt-in.** "Tap to re-engage me after a week of no opens." Off by default. Not bundled into the daily reminder consent. Tone-aware copy that reads like *"Your clock is waiting"* (Coach), *"Whenever you're ready"* (Gentle), *"It's been a week. Log."* (Firm/Direct — but the mortality-lexicon test still applies).

Recommendation: **A for v1.** Add to Decided constraints: *"v1 does not re-engage users who stopped opening the app. Scheduled local notifications are limited to the user-opted-in daily reminder."* Revisit after retention data.

## Regressions caught

None — no source edits.

## A11y identifiers added

None — no source edits.

## Vision updates

- Open Questions appended (proposed): five entries below, in vision.md numbering convention. **The skill cannot edit Decided constraints**, but with operator approval after these Asks resolve, three of the five Asks could collapse into Decided entries (Asks 1, 2, 4, 5).

```
15. Notifications — should weekly wrap-ups push, or stay pull-only?
    See polish-2026-05-08-vision-notifications-audit.md Ask 1.
    Recommendation: pull-only (A) until retention data exists.

16. Notifications — morning vs. evening reminder framing.
    Current shipped behavior commits to evening (default 20:00, copy
    "if you haven't logged by 8 PM"). See polish-2026-05-08-vision-
    notifications-audit.md Ask 2. Recommendation: ratchet evening (A).

17. Notifications — should reaching SafetyNet imply softer Lock-Screen
    copy independent of in-app tone? See polish-2026-05-08-vision-
    notifications-audit.md Ask 3. Recommendation: status quo (A) or
    explicit user toggle (C).

18. Notifications — should v1 ship a re-engagement nudge for users
    who stop opening the app? See polish-2026-05-08-vision-notifications-
    audit.md Ask 5. Recommendation: don't ship (A) until retention data.

(Operator-only: ratchet 8…22 clamp into Decided constraints, per Ask 4.)
```

- Decided constraints proposed (operator-only edit, do NOT add this session):
  - **Daily reminder hour is bounded to 8…22.** Source: `setDailyReminder` clamp. Reasoning: prevents Firm/Direct nudges arriving at sleeping/vulnerable hours, even if a future App Intent or Shortcut bypasses the picker UI.
  - **Notifications meet the user outside the app and follow the dignity rule:** no mortality lexicon regardless of in-app tone, pinned by `NotificationsServiceTests.testNoMortalityLexiconInAnyToneCopy`.
  - **Wrap-ups are pull, not push.** No scheduled notification surfaces wrap-ups; they appear on cold-launch when conditions are met. (Conditional on Ask 1 resolving as A.)
  - **v1 ships exactly one notification class: the user-opted-in daily reminder.** No re-engagement nudges, no weekly push, no streak-resurrection prompts. (Conditional on Asks 1 + 5 resolving as A.)

## Final-check status

Vision-mode requires a final computer-use checkpoint. Status: **complete** (operator granted access mid-session after initial timeouts; resumed and finished).

Captured goldens (local-only — `.polish/` is gitignored):

| File | What it shows | Confirms |
|---|---|---|
| `.polish/goldens/notifications-audit/02_today_clean.png` | Today screen, onboarded scenario, +0 min | Build path + seed scenario work |
| `.polish/goldens/notifications-audit/03_profile_daily_reminder_off.png` | Profile → Daily reminder section, toggle OFF | Default-off state. Footer reads exactly *"We'll remind you to log if you haven't already by this time. One per day. Reminder time runs between 8 AM and 10 PM."* — the 8 AM clamp is surfaced to the user, supports Ask 4 |
| `.polish/goldens/notifications-audit/04_profile_safety_entry.png` | Profile bottom: "If this app is making you anxious" entry | SafetyNet is reachable; subtitle reads *"Switch to Gentle tone, hide the clock, or get crisis-resource phone numbers. Always available — no questions asked."* — the soft-mode lever is the user's choice, not implicit |
| `.polish/goldens/notifications-audit/05_safetynet_top.png` | SafetyNet sheet, three cards visible | The two notification-affecting levers (Switch to Gentle, Hide projected age and anchor date toggle) are both present and visually equal-weight; "Use Gentle now" is a primary button, "Hide" is a Toggle. Confirms Ask 3's status-quo option. |

Two notable side-discoveries during the drive:

- **Locked badges include "Future nudge" — "Enabled the daily reminder."** Visible in the Locked group on Profile. The app already gamifies enabling reminders (Consistency category badge). This is consistent with the audit's claim that the shipped path is opt-in; the badge incentivizes opt-in without making it default.
- **Daily reminder toggle did not flip when tapped** in the onboarded scenario. The bound setter calls `setDailyReminder(enabled: true, hour: …)`, which writes `dailyReminderEnabled = true` to SwiftData and calls `reconcileNotifications` — but with `notificationAuthorizationStatus == .notDetermined`, the reconcile early-returns through `cancelAll()`. The persisted `true` should still bind back to the Toggle, but visually the Toggle stayed off across multiple taps.
  - **Possible read:** the `Binding.set` callback's `Task { await store.setDailyReminder(...) }` runs asynchronously; the toggle visual has nothing to bind to until `profile.dailyReminderEnabled` updates and SwiftUI re-renders. If the iOS auth dialog should fire here but doesn't (because the request is gated to onboarding step 5), the user sees a no-op toggle. Worth a separate Polish/Stretch finding.
  - **Filed as F9 — out of scope this session, queued for next pass.** The audit was about scheduling logic, not the toggle's UX. But this is the kind of thing the simulator visit catches that source reading would not.

### F9 — Daily reminder toggle visually no-ops when notification auth is `.notDetermined` *(filed for next pass, Polish or Stretch)*

The Profile toggle's setter unconditionally calls `setDailyReminder`. If the user reaches Profile with `.notDetermined` (e.g. they answered "No thanks" in onboarding and now want to opt in), tapping the toggle:

1. Sets `profile.dailyReminderEnabled = true` in SwiftData
2. Calls `reconcileNotifications` → reads `notificationAuthorizationStatus == .notDetermined` → calls `cancelAll()` (early-return path)
3. No iOS permission dialog presents
4. The Toggle visual *should* re-render to ON via the binding, but in our drive it stayed OFF — needs further investigation. Either way, the user gets no signal that the toggle requires permission.

Suggested fix shape (for next session, with operator approval): the Profile toggle's `set` block should call `requestNotificationAuthorization` when status is `.notDetermined`, then `setDailyReminder`. The same hour-default (`?? 20`) applies. Onboarding step 5 already does this — Profile should mirror.

## Next pass

- After operator answers Asks 1–5, the **Decided constraints ratchet** is the most valuable follow-up — converting recommendations into vision lock-in.
- If Ask 5 resolves as B (ship re-engagement), open a separate `simulator-driven-polish` session in `freeform-polish` mode — that's a feature ship and needs the full loop, not an audit.
- F4 (onboarding-step-5 denied-state inline message), F6 (consolidate `dailyReminderHour` default constant), F7 (surface the suppression behavior — e.g. Profile footer line "Logged today? We'll skip tonight's reminder"), F9 (Profile toggle should request notification auth when `.notDetermined`) are queued **Polish/Stretch-tier** items, currently out of scope per "purely audit + propose."
