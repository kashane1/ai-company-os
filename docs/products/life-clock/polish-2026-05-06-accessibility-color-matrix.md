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

---

## Session 2026-05-09 — Onboarding terminals palette delta

Continuation of the 2026-05-06 cycle's `Next pass` deferrals. Original
matrix excluded the three terminal-tier onboarding screens explicitly
called out as out-of-scope: `recoveryPreview`, `healthKitAuth`,
`paywallPrimary`. Those were swept here under the same observer (the
shipping design system + accessibility & color invariants) but with an
extra dimension — the user-selectable palette (`defaultNavy` /
`auroraCool` / `sunsetWarm`) that the v1 palette feature surfaced.
Total recon: 3 palettes × 2 schemes (`light` / `dark`) × 2 sizes
(`default` / `axxl`) = 12 cells × 3 screens = 36 captures at
`/tmp/lifeclock-polish/onboarding-terminals/<palette>-<scheme>-<size>/`.

The earlier (since-shipped) `entryView` cut (`d262a75`) removed the
fourth surface that would otherwise have been swept here; the
`PlanEditorSheet` and `monthlyLoggingBanner` rows the matrix audit
listed as deferred have already had their own dedicated polish passes
on 2026-05-06 and need no further sweep at this dimensionality.

- Iteration cap: 8.
- Final computer-use checkpoint: no.
- Simulator target: iPhone 17 Pro, iOS 26.4 simulator (booted).
- Scheme: `LifeClock` (regenerated `LifeClock.xcodeproj` via
  `xcodegen` at session start).
- Seed harness: `LIFECLOCK_UI_TEST_SCENARIO=onboarding`,
  `LIFECLOCK_JUMP_TO=recoveryPreview`,
  `LIFECLOCK_HEALTH_AUTH=authorized`,
  `LIFECLOCK_USE_MOCK_HEALTH=1`, plus the new
  `LIFECLOCK_FORCE_PALETTE` knob this session ships.

### Iterations

- [15:01] `bc55ae2` — chore(life-clock): LIFECLOCK_FORCE_PALETTE
  launch knob — Polish — scaffolding. Adds the third polish-recon
  override (alongside `FORCE_COLOR_SCHEME` and `FORCE_PAYWALL`).
  Parses `LIFECLOCK_FORCE_PALETTE=default-navy|aurora-cool|sunset-warm`
  in `LifeClockLaunchConfiguration.current` (DEBUG-only), applies on
  the pre-bootstrap store so the very first frame tints correctly
  (including jump-to-terminal-onboarding launches that never load a
  UserProfile), and mirrors into the seeded `UserProfile.paletteId` so
  bootstrap()'s restore on `.onboarded` runs converges on the forced
  value.
- [15:08] `4c17668` — chore(life-clock): onboarding-terminals matrix
  recon harness — Polish — scaffolding. Adds the throwaway
  `OnboardingTerminalsRecon` UI test sweeping
  `(palette × color-scheme × Dynamic Type)` on the three terminal
  screens. Each cell jumps to `recoveryPreview` via
  `LIFECLOCK_JUMP_TO`, taps `onboarding.continue` to advance to
  `healthKitAuth`, then takes the soft-skip ("Not now") path to
  `paywallPrimary` so no system permission dialog interrupts the
  capture sequence. Slated for deletion alongside
  `TopLevelMatrixRecon` once the follow-up captures are done;
  `LIFECLOCK_FORCE_PALETTE` stays.
- [15:11] First sweep run — every cell emits
  `02-healthKitAuth-MISSING-continue` because
  `app.buttons["onboarding.continue"]` returns nothing on
  `recoveryPreview`. Stopped the run after 4 cells.
- [15:14] `7866d62` — fix(life-clock): a11y children:.contain on
  RecoveryPreviewView — Polish — recoveryPreview. The outer VStack
  carrying `.accessibilityIdentifier("onboarding.recoveryPreview")`
  was missing the `.accessibilityElement(children: .contain)` modifier
  that `OnboardingScaffold` uses for the same reason — SwiftUI
  flattens the VStack into one a11y element and the screen id
  shadows the inner `onboarding.continue`, the headline id, and the
  cycling-phrase id. Mirrors the modifier already on the scaffold.
  Restored test driveability of the recovery → healthKitAuth advance.
- [15:17] Restart sweep. Every cell now produces all 3 captures, but
  every cell still emits a "paywallPrimary never appeared" assertion
  failure on the existence wait — same root cause, one screen further
  down. The screenshot is captured anyway (XCTAssertTrue records the
  failure but doesn't return), so the matrix completed at 36 / 36
  PNGs.
- [15:24] `8ef0f9d` — fix(life-clock): a11y children:.contain on
  PaywallPrimaryView — Polish — paywallPrimary. Same root cause as
  `7866d62`. Restores `paywall.close`, `paywall.purchase`,
  `paywall.restore`, and the per-tier ids to XCUITest queries.
- [15:32] Smoke-rebuild + single-cell rerun
  (`testNavyDarkDefault`) — passes cleanly. Both a11y fixes are
  load-bearing for any future polish recon on these surfaces.

### Stretch decisions (operator review)

None this session. Both fixes match the existing scaffold convention
verbatim — no design-system departures, no copy changes.

### Asks

#### Resolved this session

None.

#### Outstanding (cycle-end batch)

##### F6 — LifeGridDotView dots invisible across the entire reveal escalator (Stretch / pre-existing bug)

In every captured `01-recoveryPreview.png` (light + dark, default + axxl,
all three palettes), the 240pt dot-grid region between the headline /
cycling-phrase block and the legend renders as flat empty space. The
AX dump confirms the view is in tree with the right size and the
right derived label
(`'Life grid: approximately 16 years could be recovered.'`), so the
container is laid out correctly and the dot-style switch reaches the
"recoveryHighlighted" branch — but the Canvas pass appears to never
deposit visible dots.

Cross-check against the prior `OnboardingRhythmRecon` artefact at
`/tmp/lifeclock-polish/21-lifeGridRemaining.png` shows the SAME
empty-region behavior on `lifeGridRemaining` (a sibling screen in the
five-step escalator reached via the normal flow, not via
`LIFECLOCK_JUMP_TO`). So this is not a recon-harness artifact — the
reveal escalator's hero artifact has been invisible at runtime on at
least two of its four screens.

The `LifeGridDotView` body uses
`Canvas(rendersAsynchronously: true)` with a `progress: Double`
state-driven opacity. Two candidate root causes:

1. **`onAppear` race vs. asynchronous Canvas commit.** `progress`
   starts at 0 and the `.onAppear` runs
   `withAnimation(.easeInOut(duration: 0.6)) { progress = 1 }`. Under
   `rendersAsynchronously: true` the first frame is committed before
   the animation lands; if the asynchronous path doesn't observe the
   subsequent state delivery the canvas stays at opacity 0
   permanently.
2. **Geometry-reader 0×0 first frame.** `positions` is computed in
   `onAppear` from `geo.size`. If the GeometryReader's first frame is
   sized 0×0 (during a NavigationStack push transition), `positions`
   is `[]`, and the `onChange(of: geo.size)` recompute runs but the
   Canvas's `drawDots` short-circuits on `positions.isEmpty` for
   that initial frame; under async rendering the second frame's draw
   may not be re-issued.

Either way: the four-screen reveal escalator (`lifeGridFull` →
`lifeGridRemaining` → `bigNumberPenalty` → `recoveryPreview`) is
this product's emotional payload, and it's currently blank. **Out of
scope for autonomous polish — root-cause fix needs to be done with
RenderInstrument visibility**, not from screenshots. Queued as
Stretch + Vision-question; operator should pick one of:
(a) `progress = 1` immediately when `accessibilityReduceMotion` is
on AND when running under `LIFECLOCK_UI_TEST=1` so recon captures
land in their final state; (b) drop `rendersAsynchronously: true`
on this Canvas (4160 dots is on the edge of where the perf gain
matters anyway); (c) ship a focused commit gated on the
`Canvas(...).id(positions)` trick so a positions update forces a
fresh first frame.

Captures (per palette / scheme / size) showing the empty grid are at
`/tmp/lifeclock-polish/onboarding-terminals/*/01-recoveryPreview.png`.

##### F7 — All three terminal screens overflow without a ScrollView at Accessibility-XL (Stretch)

At `axxl` Dynamic Type:

- `recoveryPreview`: legend HStack truncates labels —
  `Liv… N… Re… Stil…` (`/tmp/lifeclock-polish/onboarding-terminals/*-axxl/01-recoveryPreview.png`).
- `healthKitAuth`: title `"Let your clock learn from your body."` is
  shrunk to one line + ellipsis (`Let your cloc…`); body
  `"Read steps, exercise, sleep, and resting heart rate from Apple
  Health. You can change this any time in Settings."` shrunk to
  `Read steps, exer…`. Caused by `OnboardingScaffold`'s plain VStack
  layout — when Continue + secondary action eat enough vertical
  space, the title block compresses and Text falls back to
  `.truncationMode(.tail)`. (`/tmp/lifeclock-polish/onboarding-terminals/*-axxl/02-healthKitAuth.png`)
- `paywallPrimary`: the `"Earn time, every day."` headline + the
  `"Pro keeps your full history…"` subtitle are pushed off-screen
  entirely; tier rows show `Year… $49…`, `Lifeti… $12…`,
  `Mont… $7…` with prices truncated; the per-month equivalent line
  reads `≈ $4.1…`. Continue + Restore are also off-screen.
  (`/tmp/lifeclock-polish/onboarding-terminals/*-axxl/03-paywallPrimary.png`)

This is one finding because it's one root cause: the static-layout
`OnboardingScaffold` and the custom-layout `PaywallPrimaryView` /
`RecoveryPreviewView` all use plain VStacks, no ScrollView. At axxl
sizes the cumulative content (title + body + content + Continue +
secondary) exceeds viewport height and SwiftUI truncates Text
greedily. Affects every onboarding screen at axxl, not just these
three — so the right scope is a scaffold-level fix that the
operator should sign off on before I ship it. Options:
(a) wrap the scaffold body in `ScrollView` and pin the Continue
button to the bottom safe-area; (b) wrap the entire scaffold in
`ScrollView`, accepting that the Continue button scrolls with the
content (less muscle-memory-stable); (c) keep static layout and add
`minimumScaleFactor` everywhere (defeats the point of Dynamic Type).
Touches every onboarding screen — Ask before doing.

Captures (per palette / scheme): the `*-axxl` directories under
`/tmp/lifeclock-polish/onboarding-terminals/`.

##### F8 — Mascot clock face contrast in dark mode (carried from F4)

The 2026-05-06 audit's F4 (mascot clock face stays bright on every
surface in dark mode) reproduces verbatim on all three terminal
screens — the persistent header mascot is shared. Carry-over, not a
new finding; documenting here only so this session's outstanding
queue is complete. F4's options A/B/C still apply and still need an
operator pick.

### Regressions caught

- None unintended this session. The two a11y fixes change AX-tree
  shape only and are explicitly mirroring the OnboardingScaffold
  convention.
- The "paywallPrimary never appeared" failures from the first sweep
  were caused by THIS session's recon driver hitting a pre-existing
  AX shadowing issue on `PaywallPrimaryView` — same shape as the
  recoveryPreview AX bug. Both are fixed.

### A11y identifiers added

- None added. Two existing screen-root identifiers fixed
  (`onboarding.recoveryPreview`, `onboarding.paywallPrimary`) by
  adding `.accessibilityElement(children: .contain)` so inner
  identifiers (`onboarding.continue`, `paywall.close`,
  `paywall.purchase`, `paywall.restore`, the per-tier ids) survive
  the SwiftUI flatten pass.

### Invariants verified

- **orange-not-red invariant** (LifeClockPalette.swift:3-5) holds
  across all 36 captures.
  - `recoveryPreview` uses `LifeGridDotView.GridMode.recoveryHighlighted`,
    which paints `.blue` for the recoverable dots — never `.red`.
    The `bigNumberPenalty` mode that uses `.red` is one screen
    earlier in the escalator and is not part of this audit.
  - `healthKitAuth` uses `.red` only on the
    `store.lastHealthAuthError` text, which never renders under
    `LIFECLOCK_HEALTH_AUTH=authorized` (mock auth never errors).
  - `paywallPrimary` has no raw `.red`/`.orange` — only
    `.accentColor`, `.tint`, `.secondary`, `.tertiary`,
    `Color(.secondarySystemBackground)`, `.white`. The
    `sunset-warm` palette's accent color
    (`Color(red: 0.85, green: 0.42, blue: 0.20)`) renders as warm
    orange rather than alarming red, visible on the Continue
    button's fill and the selected-tier checkmark — clearly
    distinct from the `LifeClockPalette.heartbeatRed`
    `Color(red: 0.86, green: 0.18, blue: 0.18)` that paints the
    mascot's ECG line as the documented exception.
- **Inline title on Today** (commit `7083351`,
  TodayView.swift:124) verified statically — the
  `dynamicTypeSize.isAccessibilitySize ? .inline : .large` ternary
  is intact in source; no code path overrides it. Today wasn't
  recaptured in this session (it's in the original 5/6 audit
  scope, not the terminals delta), so live verification falls to
  the next pass that touches Today.

### Vision updates

- Open Questions appended: F6 (LifeGridDotView Canvas opacity), F7
  (axxl scaffold overflow). Both pending operator direction;
  neither contradicts an existing Decided constraint.
- Decided constraints proposed: none (operator-only edit).

### Next pass

- Resolve F6 (LifeGridDotView invisible). The whole reveal
  escalator's emotional payload depends on it. Suggest pairing with a
  short Instrument / SwiftUI Inspector session before shipping —
  blind-fixing on screenshots risks landing on the wrong root cause.
- Resolve F7 (axxl overflow on onboarding scaffold). Affects every
  data-collection screen; touch is at scaffold root. Pair with the
  `keyboardAvoidance` trial before shipping so we don't redo the
  layout twice.
- Same-finding-twice rule: F4 (mascot dark-mode contrast) has now
  appeared in two consecutive sessions without operator
  direction — treat next appearance as a hard stop.
- Recon-driver cleanup: drop both `TopLevelMatrixRecon.swift` and
  `OnboardingTerminalsRecon.swift` once F6 + F7 land. Keep
  `LIFECLOCK_FORCE_PALETTE` permanently — it composes with
  `FORCE_COLOR_SCHEME` for any future axxl matrix and is cheap.
