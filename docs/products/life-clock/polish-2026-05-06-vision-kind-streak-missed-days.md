# Polish Session — life-clock — 2026-05-06 — vision-kind-streak-missed-days

## Mode

`vision-driven`. Observer is `vision.md`, specifically Open Question #7
("Streak treatment. The product is anti-streak-shaming, but streaks
compound retention. Is there a *kind* streak that survives a missed
day without shame?").

This is a **research** session, not implementation. No treatment was
shipped. Output is a Vision-question batch with three options for the
operator to pick from. Iteration cap: 6. Final computer-use checkpoint:
skipped (operator opted out for exploratory research).

## Iterations

- [01:08] Mapped current streak code: `DietStreakCalculator`,
  `dietStreakBanner` in `TodayView`, `longAbsenceCard` in
  `HistoryView`. Confirmed there are no widget targets — "home-widget-
  style surfaces" do not exist in v1.
- [01:17] Authored `Sources/Debug/KindStreakResearchView.swift`
  (`#if DEBUG`-gated) rendering the four panels: baseline + Option A /
  B / C. Wired through `RootView` behind
  `LIFECLOCK_RESEARCH=kind-streak`. Regenerated the Xcode project
  with `xcodegen` to pick up the new file.
- [01:24] Headless build to iPhone 17 Pro (iOS 26.3) succeeded.
- [01:29] First capture (`section_overview.png`) confirmed the view
  reaches the screen end-to-end with onboarded fixture +
  authorized HealthKit mock.
- [01:33] Refactored the research view to support
  `LIFECLOCK_RESEARCH_SECTION=baseline|a|b|c|all` so each option
  renders fullscreen with no scroll. Rebuilt.
- [01:40] Captured all four sections cleanly:
  `section_baseline.png`, `section_a.png`, `section_b.png`,
  `section_c.png`. Each shows the simulated 10-day journey
  (day 4 + day 8 missed) under that treatment.

No commits in this session. Code under `Sources/Debug/` is research
scaffolding — `#if DEBUG`-gated, never touches the user-facing flow,
and is reachable only by setting `LIFECLOCK_RESEARCH=kind-streak`.

## Findings — current behavior with a missed day

Mapped the surfaces an operator would expect to surface a "streak":

1. **`Today` screen — `dietStreakBanner`**
   ([TodayView.swift:342](../../products/life-clock-ios/Sources/Features/Today/TodayView.swift)).
   Two streaks are computed by
   [DietStreakCalculator](../../products/life-clock-ios/Sources/Engines/DietStreakCalculator.swift):
   `loggingDays` (any non-`unknown` diet log) and `goodDays`
   (`great`/`okay` only). The banner only renders at `loggingDays >= 2`.
   **Critical detail:** the calculator zeroes both streaks if the
   gap from the most recent log to "today" exceeds one day — so a
   single missed day with no log resets to 0 the next time the user
   logs. There is no grace window.

2. **`History` screen** has a `longAbsenceCard`
   ([HistoryView.swift:89](../../products/life-clock-ios/Sources/Features/History/HistoryView.swift))
   that surfaces only when there are older snapshots but no
   qualifying yesterday data. This is the *closest existing
   acknowledgement of an absence* and uses warm copy
   ("Welcome back / Time has kept moving. So can you.") via the
   tone-mode strings. It does NOT mention streaks.

3. **Widgets / lock-screen / home-screen** — none.
   `find Sources -name "*Widget*"` returns nothing. No widget
   targets in `project.yml`. So "any home-widget-style surface" is
   currently a non-question; this Open Question is exclusively
   about Today + History.

**Net behavior with the day 4 + day 8 skip pattern:**

| Day | What user sees on Today |
|---|---|
| 3 | 🔥 "3-day diet log streak" — banner appears for the first time |
| 4 | (App not opened — no observation) |
| 5 | **Banner gone.** No mention of the missed day. No "welcome back". `loggingDays` = 1 (today) |
| 6 | Still no banner — `loggingDays` only crosses the 2-day floor again at day 6 evening, day 7 |
| 7 | 🔥 "3-day diet log streak" — fresh streak rebuilt |
| 8 | (App not opened) |
| 9 | **Banner gone again.** Identical silent reset |
| 10 | 2-day streak banner returns |

This is consistent with the "Default is motivating, not punishing"
constraint — there is genuinely zero shame, because the app says
nothing on the return day. But it also means the user gets *no
recognition* for showing back up after a skip, and the cumulative
"streak" identity dies twice in 10 days. That trade is the heart of
Open Question #7.

Screenshot: [section_baseline.png](research/kind-streak/section_baseline.png)
shows the five-panel journey under the current implementation —
two days where the banner is replaced by an empty placeholder.

## Three proposed treatments

### Option A — No streak at all
Screenshot: [section_a.png](research/kind-streak/section_a.png)

Remove the streak banner from `Today` entirely. Replace with a
rolling "X of last 7 days logged" line that lives only on the
`History` tab. The Today screen never asserts a streak.

- ✅ Maximally anti-shame. No fragile chain to break. Aligns 100%
  with "Default is motivating, not punishing."
- ✅ Honest — the rolling count never mis-states cumulative
  consistency.
- ⚠️ Loses the daily retention pull a streak provides. RevenueCat /
  retention literature is consistent: streaks compound returns.
  Removing them costs measurable D7/D30.
- ⚠️ Doesn't acknowledge a return after a skip — the user just
  sees a slightly lower count.

### Option B — Rest-day grace
Screenshot: [section_b.png](research/kind-streak/section_b.png)

Keep the streak. Streak survives ONE missed day per rolling 7 days,
consumed silently as a built-in rest day. After a skip the banner
reads `"{N}-day streak · 1 rest day used"` with a small moon glyph.
A second skip inside 7 days resets — but the reset copy is gentle:
"Fresh start. Day 1 of the next run."

- ✅ Closest to a classic streak — preserves the retention mechanic.
- ✅ The "rest day" framing reads as care, not failure. Consistent
  with the trainer voice in the tone spec.
- ✅ Adds a recoverable mechanic without inventing a new concept.
- ⚠️ Still has a hard reset on the second miss inside 7 days.
  Operator must decide whether the "Fresh start" copy is enough or
  whether even this should be replaced with something rolling.
- ⚠️ Adds rule complexity — two skips in 7 days is the kind of
  thing users have to learn or be surprised by.

### Option C — Rolling rhythm
Screenshot: [section_c.png](research/kind-streak/section_c.png)

Replace the cumulative streak with a rolling "{N} of last 7 days"
ring-and-number on `Today`. A skip drops the count by 1 but the
thread doesn't reset. Reads as a habit cadence rather than a
fragile chain.

- ✅ No reset, no shame, ever. Same anti-streak-shaming property
  as Option A but keeps a daily-loop reward visible.
- ✅ The ring visualization is dopamine-positive and shipping-
  visible — fills as the week progresses.
- ✅ Doesn't claim a streak the user isn't actually on.
- ⚠️ Loses the dopamine of a *rising* number — once a user is at
  7/7, there's no further growth, just maintenance.
- ⚠️ "{N} of last 7 days" is a less iconic concept than "streak".
  Cultural recognition is weaker.

## Stretch decisions (operator review)

None — this is a Vision-question batch only. No code lands.

## Asks
### Resolved this session
- None.

### Outstanding (cycle-end batch)
- **Vision Q7 — pick a kind-streak treatment.** Three options
  surfaced above with screenshots. The framing ranges from
  "no streak at all" (A) to "recoverable streak with grace" (B)
  to "rolling rhythm" (C). Operator chooses; the next session
  drops the research scaffolding and ships the chosen option as
  a real change in `dietStreakBanner` + the appropriate spot in
  `History`. If none of the three feel right, the live mockup
  view can be modified and re-screenshot in another short pass.

## Regressions caught
- None. No source files outside `Sources/Debug/` and a single
  guarded block in `LifeClockApp.swift` were modified, and all
  modifications are `#if DEBUG`-gated — release builds carry
  zero added surface.

## A11y identifiers added
- `research.kindStreak` (on the research root). Not added to any
  user-facing surface.

## Vision updates
- Open Question #7 expanded with the three named options and
  pointers to the screenshots. See `vision.md`.
- Decided constraints proposed (operator-only edit): none yet —
  pending the operator's pick.

## Next pass
- Operator picks one of A / B / C (or asks for a fourth).
- Next session: implement the chosen option in `Today`'s real
  `dietStreakBanner`, update copy strings via `ToneMode` so all
  three tones render the chosen treatment cleanly, refresh
  goldens, write tests for the calculator changes (especially
  for B's rest-day accounting), append the answer to `Decided
  constraints` in `vision.md`.
- Either way, delete `Sources/Debug/KindStreakResearchView.swift`
  and the `RootView` env-var hook once the decision is recorded —
  research scaffolding shouldn't outlive its purpose.

## How to re-render

```bash
xcodebuild -project LifeClock.xcodeproj -scheme LifeClock \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -configuration Debug build

DEV=$(xcrun simctl list devices booted | awk '/iPhone 17 Pro/ {print $4}' | tr -d '()')
for SECTION in baseline a b c; do
  xcrun simctl terminate $DEV io.aicompanyos.products.lifeclock 2>/dev/null
  SIMCTL_CHILD_LIFECLOCK_RESEARCH=kind-streak \
  SIMCTL_CHILD_LIFECLOCK_RESEARCH_SECTION=$SECTION \
  SIMCTL_CHILD_LIFECLOCK_UI_TEST=1 \
  SIMCTL_CHILD_LIFECLOCK_UI_TEST_SCENARIO=onboarded \
  SIMCTL_CHILD_LIFECLOCK_USE_MOCK_HEALTH=1 \
  SIMCTL_CHILD_LIFECLOCK_HEALTH_AUTH=authorized \
  xcrun simctl launch $DEV io.aicompanyos.products.lifeclock
  sleep 5
  xcrun simctl io $DEV screenshot section_${SECTION}.png
done
```
