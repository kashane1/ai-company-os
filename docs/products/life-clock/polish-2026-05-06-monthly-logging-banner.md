# Polish Session — life-clock — 2026-05-06 — monthly-logging-banner

## Mode

`vision-driven`. Operator picked Option D (calendar-month reset, "N days
so far this month", milestone copy at start / 25% / 50% / 75%) from the
Open Question #7 research batch in
[polish-2026-05-06-vision-kind-streak-missed-days.md](polish-2026-05-06-vision-kind-streak-missed-days.md).
Operator decisions:

- Late installers: stay strict. No special copy.
- Milestone day: persistent (same copy all day).
- No month-progress pill, just the count.
- Drop `goodDays` entirely.

Iteration cap: 6. Final computer-use checkpoint: not run (operator did
not request; tests + UITest-driven goldens cover the rendering).

## Iterations

- [07:30] Built `MonthlyLoggingCalculator` + `MonthlyLogging` value type
  (`daysLogged` / `dayOfMonth` / `daysInMonth` / `monthName` /
  `milestone`). Milestone math uses `ceil(threshold × daysInMonth)`
  with a floor at day 2 so day 1 stays reserved for `.start`. Pure
  function over `Calendar + asOf + habits`; no `Date()` calls.
- [07:34] Wired into `LifeClockStore` — `dietStreaks` →
  `monthlyLogging`, `streakCalculator` →
  `monthlyLoggingCalculator`. The rebuild surface in
  `refreshDerivedSlices` swaps the call. Window stays at
  `fetchHabitsBack(60)` — generous enough to cover the current month
  and a buffer for boundary handling.
- [07:36] `CompletionBadgeProgress.dietLoggingStreakDays` →
  `monthlyLogDays`. Badge entry copy updated:
  `nutrition.streak` → `nutrition.month`, "Food log streak" → "Days
  logged this month", flame glyph → calendar glyph. Thresholds
  preserved (3 / 7 / 14 / 30) — they still encode the "log a useful
  fraction of the month" spectrum.
- [07:39] Replaced `dietStreakBanner` with `monthlyLoggingBanner` in
  `TodayView`. Always renders when `daysLogged ≥ 1` (no 2-day floor —
  the banner is no longer waiting for a streak identity to form).
  Secondary line is the tone-mode milestone copy on milestone days,
  the neutral line otherwise.
- [07:42] Added monthly-banner copy to `ToneMode` —
  `monthlyLoggingNeutralLine` and
  `monthlyLoggingMilestoneLine(_:daysLogged:monthName:)`. Three tones
  × four milestones. Coach + Gentle share the start-day copy ("May
  starts now. Every logged day counts."); Firm/Direct gets a
  separate punchier line ("May. Day one. Log it."). Days-count
  pluralization handled by a single helper.
- [07:43] Wrote `MonthlyLoggingCalculatorTests` — 14 cases covering:
  empty habits, current-month-only filter, missed-day robustness
  (the day 4 + 8 scenario from the research; 8 days survive),
  same-day dedup, rough-day count, unknown-quality skip, and
  milestone math for 28- / 30- / 31-day months. Plus a ToneMode
  smoke test that asserts every (tone, milestone) pair returns
  non-empty copy.
- [07:44] Updated `CompletionBadgeEngineTests` — single field-name
  change.
- [07:45] Deleted `Sources/Engines/DietStreakCalculator.swift`,
  `Tests/DietStreakCalculatorTests.swift`,
  `Sources/Debug/KindStreakResearchView.swift`. Removed the
  `LIFECLOCK_RESEARCH=kind-streak` hook in `LifeClockApp.swift` —
  research scaffold from yesterday's session is gone.
- [07:46] Build green. Full test target green. Targeted tests:
  `MonthlyLoggingCalculatorTests` (14) + `CompletionBadgeEngineTests`
  (2) — 16/16 pass in 0.65s.
- [07:50] Built throwaway `UITests/MonthlyBannerCaptureRecon.swift` —
  one test method per representative day (start / quarter / half /
  threequarter / neutral). Each launches with
  `LIFECLOCK_FIXED_DATE` + `LIFECLOCK_SEED_STREAK`, swipes the Today
  scroll up 7×, asserts `today.monthlyLogging` AX id, and writes the
  PNG to `/tmp/lifeclock-monthly/`.
- [07:55] First run of the recon hit a `Locale.current`-derived
  formatter that returned month name as `M05` instead of "May" inside
  the UITest sandbox. Pinned the formatter to `Locale(identifier:
  "en_US")` in the calculator — banner copy is English-only by
  product decision, so the override is honest.
- [08:40] Goldens captured at
  `products/life-clock-ios/.polish/goldens/today-monthly-{start,quarter,half,threequarter,neutral}.png`.
  Goldens for screens the loop did not touch (`onboarding`, `paywall`)
  were not regenerated — none of those views' code changed.
- [08:41] Deleted `MonthlyBannerCaptureRecon.swift` per its docstring
  ("safe to delete afterwards"). `xcodegen generate` re-emits the
  project without it.
- [08:42] Updated `vision.md`: marked Open Question #7 resolved and
  appended the "monthly count, no streak" line to `Decided
  constraints / Product`.

## Stretch decisions (operator review)

- **Pluralization.** "1 day" vs "N days" handled in two places: the
  banner headline and the milestone copy. Both flow through the same
  English-correct branch — `daysLogged == 1 ? "1 day" : "N days"` —
  rather than a `Plural` formatter. Worth tone-mode review on first
  use.
- **Calendar glyph.** Replaced the flame glyph (which connoted
  streak) with `"calendar"` SF Symbol. Matches the "the calendar is
  the only thing that resets" framing.
- **Quality silently dropped.** The old banner's `goodDays` secondary
  was the only place "great vs okay vs rough" surfaced as a meta
  signal. The Time Ledger and quest engine still differentiate, but
  the daily banner does not. Operator confirmed this in the brief.

## Asks

### Resolved this session
- vision Open Question #7 → **option D**, this session's
  implementation is the answer. Logged in `vision.md` Decided
  constraints, dated 2026-05-06.

### Outstanding (cycle-end batch)
- None.

## Regressions caught
- None. Diff is scoped to `Sources/{Engines,App,Features/Today}` plus
  the matching test files. No untouched-screen golden diffs reviewed
  because no other golden was regenerated this session — the calculator
  / store / today banner are the only changed surfaces.

## A11y identifiers added
- `today.monthlyLogging` — replaces `today.dietStreak` (same slot,
  semantically renamed).

## Vision updates
- Open Question #7 marked resolved.
- New `Decided constraints / Product` entry: "Streak treatment is
  'monthly count, no streak.'" (2026-05-06).

## Next pass
- Tone-mode review on first real use — the milestone copy is the most
  load-bearing new copy in the daily loop and may want refinement
  after a real month rolls over.
- Memory ratchet candidate: the "missed days never decrement" rule is
  general. If it survives the next month with no operator
  re-litigation, save as a feedback memory.
- Consider adding a small `monthlyLogDays`-driven achievement to
  Profile — "First full month logged (28+)" as a Pro-tier flex —
  later pass.

## Files touched

```
A  Sources/Engines/MonthlyLoggingCalculator.swift
D  Sources/Engines/DietStreakCalculator.swift
M  Sources/Engines/CompletionBadgeEngine.swift   (field rename + badge copy)
M  Sources/App/LifeClockStore.swift              (calc/state rename)
M  Sources/App/LifeClockLaunchConfiguration.swift (comment update)
M  Sources/App/ToneMode.swift                    (banner + milestone copy)
M  Sources/Features/Today/TodayView.swift        (banner replacement)
M  Sources/App/LifeClockApp.swift                (drop research hook)
A  Tests/MonthlyLoggingCalculatorTests.swift
D  Tests/DietStreakCalculatorTests.swift
M  Tests/CompletionBadgeEngineTests.swift        (field rename)
D  Sources/Debug/KindStreakResearchView.swift
A  products/life-clock-ios/.polish/goldens/today-monthly-{start,quarter,half,threequarter,neutral}.png
M  docs/products/life-clock/vision.md            (Q7 resolved + constraint)
A  docs/products/life-clock/polish-2026-05-06-monthly-logging-banner.md (this file)
```
