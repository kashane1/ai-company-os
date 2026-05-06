# Polish Session — life-clock — 2026-05-06 — accessibility-color-matrix

## Mode

`freeform-polish`. Operator goal: re-screenshot every top-level
post-onboarding screen in four configurations — light + default text,
light + accessibility-XL text, dark + default text, dark + accessibility-XL
text — and fix anything that clips, falls below contrast, breaks the
lighting convention, or shrinks touch targets below 44pt at the largest
text size. Visual identity must survive every flip; if it doesn't, queue
as Stretch with both screenshots.

Iteration cap: 8. Final computer-use checkpoint: no.

Scope: Today, History, Profile. WrapUp + SafetyNet are state-gated
(engine-driven and ideation-flag-driven respectively) — out of scope
for this session; flagged in Next pass. QuickLog sheet was scoped in
initially but dropped after the Profile-tab capture path triggered an
intermittent test-runner termination ("application is not running")
on the 4-screen-per-cell driver — see `## Regressions caught`.
Onboarding + Paywall got dedicated polish passes on 2026-05-05.

Seed: `LIFECLOCK_UI_TEST_SCENARIO=onboarded`,
`LIFECLOCK_SEED_STREAK=5`, `LIFECLOCK_SEED_QUESTS_COMPLETED=2`,
`LIFECLOCK_HEALTH_AUTH=authorized`, fixed clock at
`Date(timeIntervalSince1970: 1_800_000_000)`. Color scheme + text size
driven from new launch knobs (see `chore(life-clock): top-level matrix
recon harness …`).

## Iterations

- [01:05] `ced2e91` — chore(life-clock): top-level matrix recon
  harness for color/text-size polish — Polish — scaffolding. Adds the
  DEBUG-only `LIFECLOCK_FORCE_COLOR_SCHEME` env var wired into the
  root view's `.preferredColorScheme(_:)`, plus a throwaway
  `TopLevelMatrixRecon` UI test (4 cells × {Today, History, Profile})
  dumping PNG + AX-tree per cell to `/tmp/lifeclock-polish/`. Initial
  driver attempted to also capture QuickLog after the tab dance; that
  path raced an "application is not running" termination on the first
  matrix run. Dropped the 4th screen and added a longer settle on the
  Profile tab (heavier Form render). Second run passed all 4 cells
  cleanly. The launch-config hook is keepable; the recon test itself
  can be deleted at session end.
- [01:30] Baseline matrix captured: 12 PNGs + AX dumps. Goldens copied
  to `products/life-clock-ios/.polish/goldens/<cell>/`.
- [02:06] `30c33e7` — fix(life-clock): drop redundant 'today' from
  coach delta prefix — Polish — Today. AX dump for `today.headline`
  showed `label: 'Progress today today'` in every cell. `TodayView`
  renders `"\(prefix) today"`; `ToneMode.coach.deltaPositivePrefix`
  was `"Progress today"`, double-anchoring the day. Other tones
  (gentle: "Progress gained", firmDirect: "Banked") already paired
  cleanly with the literal " today" suffix. Trimmed coach to
  "Progress" so all three tones produce one-anchor copy.
- [02:08] `7083351` — fix(life-clock): inline title on Today at
  accessibility text sizes — Polish — Today. "Today's progress" /
  "Today's reckoning" overflowed the large title slot at axxl and
  ellipsized to "Today's prog…" in both light-axxl and dark-axxl.
  Conditioning `navigationBarTitleDisplayMode` on
  `dynamicTypeSize.isAccessibilitySize` swaps to inline at axxl
  (where it shrinks to fit) and keeps the large title at default
  sizes. Profile + History titles already fit and are unchanged.
- [02:09] `d15d7db` — fix(life-clock): menu picker for Profile tone
  mode — Polish — Profile. Default Form Picker renders the selected
  case as inline trailing text and truncates at axxl ("Default /
  Average" → "Defaul...erage"). `.pickerStyle(.menu)` keeps the
  selection on its own line as a tappable dropdown trigger that
  wraps to two lines at large sizes ("Default / / Average") instead
  of truncating. Color-palette picker on the same screen retained
  default style (its options are all single short words).
- [02:13] Recapture matrix. All 4 cells passed; 12 PNGs refreshed.
  Verified: `today.headline` AX label is now "Progress today" (one
  anchor); large title returns intact at default text sizes; inline
  title at axxl shows "Today's progress" / "Today's reckoning" un-
  truncated; Profile tone picker shows "Default /\nAverage" in two
  lines instead of truncating. Goldens diff-clean for History across
  all four cells (no incidental regressions).

## Stretch decisions (operator review)

None this session — every fix matched a recorded design system or
copy convention. Coach-tone-prefix change preserved the contract
that `TodayView` joins with " today" literally; inline-title swap
preserves the iOS large-title default at non-AX sizes; menu picker
swap preserves the selection display per Apple HIG.

## Asks

### Resolved this session

None.

### Outstanding (cycle-end batch)

#### F4 — Mascot clock face stays bright in dark mode (Vision-question)

The mascot clock — bezel-rimmed, white face with red/blue dial paint
— renders identically in light and dark mode. Light surface, lighting
convention (0.22 / 0.35,0.85 / 0.55×) on a near-white bezel. In dark
mode it reads as a luminous object floating on a black background,
which can be deliberate (the clock IS the point of the product) but
also breaks the surrounding hierarchy: every other surface darkens,
the mascot doesn't.

- **Option A — keep as-is.** Treat the clock as a self-illuminated
  artifact. Argues from product soul: the clock is a "lit dial" the
  user is greeted by; dark mode is a frame, not an inversion.
- **Option B — invert face + bezel in dark mode.** Bezel becomes
  near-black (lighting offset still on the same side at 0.22), face
  becomes a darker tone with the dial paint dialed up in chroma so
  +/- min reads as glow. Most visually integrated.
- **Option C — bezel-only invert.** Keep the white face (it carries
  brand identity) but pull the bezel into dark mode tones so the
  clock sits inside the surrounding cards instead of floating.

Both `dark-default/01-today.png` and `dark-axxl/01-today.png`
(post-fix recapture) show the unchanged-from-light mascot. No
contrast violation; this is identity, not legibility. Pick one to
go to a follow-up session, or accept A as `Decided constraints`.

#### F5 — Tab-bar bleed at axxl shows scrolling content underneath

In light-axxl + dark-axxl Today captures the floating tab bar lets
ScrollView content fade through underneath ("Projected healthsp…"
peeking under the tabs). This is iOS 26's standard floating-tab-bar
behavior — material blur, not a render bug — but at axxl the bleed
is noticeable because the clock card no longer fits above the tab.

Reading: cosmetic, system-conformant. No fix unless we want a
hard-edge solid tab background at AX sizes. Flagging for operator
visibility; default = leave alone.

## Regressions caught

- **QuickLog 4th-screen capture (light-default, baseline run):** the
  one-test-method-per-cell driver tapped Today → History → Profile →
  Today → Check-In. Profile tap captured the springboard and the test
  runner reported "application is not running". Reduced cell scope to
  3 screens and added a 3s settle after Profile.tap; second run
  passed cleanly. Suspect the driver was racing the QuickLog sheet
  presentation animation faster than the previous Profile teardown.
  Filed as known recon-driver limitation, not an app bug.
- **History/Today/Profile across cells:** intentional diffs only — title
  display mode swap (Today axxl), copy ("Progress today today" → "Progress
  today"), Profile picker reflow. No unintended diffs.

## A11y identifiers added

None this session. Every element the recon driver touched
(`tabBars.buttons["Today"|"History"|"Profile"]`,
`buttons["today.checkInToolbar"]`,
`otherElements["checkIn.screen"]`,
`staticTexts["Profile"]`) already had a stable handle.

## Vision updates

- Open Questions appended: **none yet** — pending operator response on
  F4. If A is chosen, it becomes a `Decided constraints` line; if B/C,
  it goes to a follow-up session.
- Decided constraints proposed: **none** (operator-only edit).

## Next pass

- Resolve F4 (mascot-in-dark-mode) once operator picks A/B/C; either
  ratchet to `Decided constraints` or schedule a follow-up polish
  session.
- WrapUp + SafetyNet matrix capture — both are state-gated; the
  recon harness needs `LIFECLOCK_FORCE_WRAPUP=yesterday|weekly` and
  a SafetyNet flag to drive these surfaces deterministically.
- QuickLog sheet matrix capture — re-attempt with a fresh-launch
  test method per cell instead of the tab-dance approach (avoids
  the Profile-tap teardown race).
- Onboarding + Paywall matrix audit — last paywall pass was
  pre-2026-05-05; worth a fresh axxl/dark sweep before App Store
  submission.
- Recon-driver cleanup: delete `TopLevelMatrixRecon.swift` once the
  follow-up captures are done; keep `LIFECLOCK_FORCE_COLOR_SCHEME`
  permanently.
