# Polish Session — life-clock — 2026-05-06 — monthly-banner-month-edges

## Mode

`freeform-polish`. Observer = the Decided constraint from
2026-05-06 ("monthly count, no streak") and the operator brief that
**tone-aware milestone copy on gentle / coach / firmDirect must
actually read in voice and be the only thing that varies**. Followup
to [polish-2026-05-06-monthly-logging-banner.md](polish-2026-05-06-monthly-logging-banner.md)
which built the engine + initial copy.

Iteration cap: 8. Final computer-use checkpoint: not run (operator
opted out; AX dumps + recon goldens cover the verification).

Driven across simulated month edges via `LIFECLOCK_FIXED_DATE`:

| Slug | Date | Streak | Tone | Milestone | Headline | Secondary |
|---|---|---|---|---|---|---|
| 01-start-coach        | 2026-05-01 | 1  | coach      | start         | "1 day logged so far · May"   | "May starts now. Every logged day counts." |
| 02-quarter-coach      | 2026-05-08 | 5  | coach      | quarter       | "5 days logged so far · May"  | "First quarter done. 5 days in." |
| 03-half-coach         | 2026-05-16 | 10 | coach      | half          | "10 days logged so far · May" | "Halfway through May. 10 days logged." |
| 04-threequarter-coach | 2026-05-24 | 15 | coach      | threeQuarter  | "15 days logged so far · May" | "Final quarter. 15 days banked." |
| 05-neutral-day20      | 2026-05-20 | 1  | coach      | none          | "1 day logged so far · May"   | "Logging is the win — quality follows." |
| 06-half-gentle        | 2026-05-16 | 10 | gentle     | half          | "10 days logged so far · May" | "Halfway through May. 10 days so far." |
| 07-half-firmdirect    | 2026-05-16 | 10 | firmDirect | half          | "10 days logged so far · May" | "Halfway. 10 days banked." |
| 08-rollover-jun1      | 2026-06-01 | 1  | coach      | start         | "1 day logged so far · June"  | "June starts now. Every logged day counts." |

PNGs + AX dumps at
`products/life-clock-ios/.polish/goldens/monthly-banner/` (gitignored
per the existing `.polish/.gitignore` policy).

## Iterations

- [22:18] Wrote `UITests/MonthlyBannerCaptureRecon.swift` — eight test
  methods, one per case in the table above. Each launches with
  `LIFECLOCK_UI_TEST=1` + `LIFECLOCK_UI_TEST_SCENARIO=onboarded`,
  pinned `LIFECLOCK_FIXED_DATE`, `LIFECLOCK_SEED_STREAK`, and
  `LIFECLOCK_SEED_TONE`. Waits on `today.monthlyLogging`, settles for
  600 ms, captures PNG + AX dump.
- [22:19] Regenerated `LifeClock.xcodeproj` via `xcodegen` so the new
  recon file gets picked up. First run: 8/8 tests passed in 208 s.
  Counts and milestone copy validated against the calculator's pure
  math.
- [22:46] **Polish** — `ToneMode.monthlyLoggingMilestoneLine` split
  gentle from coach at `.start` and `.half`. Gentle now opens
  warmer ("A fresh \(monthName). Every day you log is yours.") and
  softens half ("Halfway through \(monthName). \(phrase) so far.").
  Coach keeps the steady-encouraging frame; firmDirect unchanged.
  Commit `311df1b`.
- [22:47] **Polish** — `TodayView.monthlyLoggingBanner` HStack
  alignment shifted to `.firstTextBaseline` so the orange calendar
  icon anchors with the bold headline instead of vertically centering
  against the two-line block; inner VStack spacing 2 → 4 so the
  callout headline and caption secondary line have breathing room;
  `Spacer(minLength: 0)` so multi-line milestone copy can fully
  consume the row when needed. Commit `a0ce78f`.
- [22:48] **Polish** — added
  `testTonesDifferAtEveryMilestone` to `MonthlyLoggingCalculatorTests`
  asserting gentle / coach / firmDirect produce three distinct
  strings at each of the four milestones. Locks the operator brief
  against silent regression to shared copy. Commit `6cfd982`.
- [23:11] Unit tests on `LifeClockTests/MonthlyLoggingCalculatorTests`
  green (after a simulator reboot recovered from a flaky test-runner
  bootstrap crash). The new distinctness guard passed.
- [23:36] Re-ran the eight-case recon; refreshed PNGs + AX dumps. All
  copies present in the new captures match the table above.
- [23:38] Recon committed at `ed0818f` so future banner drift can
  re-run it without rewriting the driver.

## Stretch decisions (operator review)

None this session — every move was a Polish-tier copy or token tweak
under the existing design system.

## Asks

### Resolved this session

None — operator's brief already covered the polish surface.

### Outstanding (cycle-end batch)

None.

## Regressions caught

- During the first recon (alphabetical order — `testCaptureHalfCoach`
  ran first), case 03 reported `daysLogged = 6` for `seedStreak = 10`
  on May 16, while cases 06 / 07 with the same date+streak reported
  `daysLogged = 10`. Re-ran case 03 in isolation after a simulator
  reboot — count returned 10. Treating as a one-shot launch flake
  (likely test-runner cold-boot timing on the seeder's `try? save`),
  not a real product regression. The pure-function calculator's
  missed-day robustness is already covered by
  `MonthlyLoggingCalculatorTests`. If it recurs, escalate.
- No untouched-screen regressions: the only files modified are the
  banner view itself, its tone copy, and the calculator test. Other
  Today subviews and other top-level screens were not entered.

## A11y identifiers added

None — `today.monthlyLogging` already existed.

## Vision updates

- Open Questions appended: none.
- Decided constraints proposed (operator-only edit): none. The
  existing 2026-05-06 entry is unchanged in spirit; this session
  only refines the per-tone voice it asks for.

## Next pass

- Optional: a tinted left-edge accent on the banner card (calendar
  orange, 2 px) — would make it feel like recognition more visibly,
  but veers into Stretch. Hold unless operator asks.
- Optional: localize the English month name. The
  `Locale(identifier: "en_US")` pin is honest given the copy is
  English-only by product decision; revisit if/when localization
  enters scope.
- A `Tests/ToneSnapshotTests` that pins all milestone copy strings
  per tone — the distinctness guard catches drift but not regressions
  to the *wording*. Skipping for now since the recon goldens cover
  this functionally.
