# Polish Session — life-clock — 2026-05-16 — future-profooter-verify

## Mode

`freeform-polish` (verification). Consumes PV-P3 from
[pro-value-backlog-2026-05-15-standard.md](pro-value-backlog-2026-05-15-standard.md)
§ "3. Future-tab proFooter visual verify on full14plus — now unblocked by
Sprint E". VERIFICATION prompt — expected outcome is "closes, no source
change". A token/opacity tweak on a passing surface is forbidden by the
prompt's binding guardrails.

Branch `claude/dazzling-roentgen-dfcc33`, HEAD `e35e3bf` (Sprint E `8a56234`
confirmed in branch history via `git branch --contains`). Sim: iPhone 17
Pro Max UDID `942B6264-62E2-4663-8230-80E9133C824E`. Scheme `LifeClock`.
Headless build (xcodegen generated standalone, never as a scheme preAction,
per `feedback_xcodegen_preaction_cancels_build.md`). **BUILD SUCCEEDED.**

## Iterations

No source-change iterations. This is a verification session; expected and
realized outcome is **zero source commits**. One docs commit (session log +
captures).

## Verification result

**Verdict: PASS — proFooter reads Pro-crafted, not Free-with-extra-rows.
Verification closes clean. No source change.**

### Fixture reproduction (logged for future audits)

`LIFECLOCK_JUMP_TO=futureFull` does seed `full14plus` post-Sprint-E
(`effectiveSeedSnapshots`=21, `effectiveSeedDaysSinceInstall`=30 — confirmed
in `LifeClockLaunchConfiguration.swift:221,237` and on screen: Future shows
"89 years, 2 months / Baseline: 84 years / Last 14 days of signal"). Two
fixture frictions surfaced and were worked around without source change:

1. **Seed is skipped if a `UserProfile` already exists**
   (`LifeClockLaunchConfiguration.swift:469`). A clean
   `simctl uninstall`+`install` is required before each state change or the
   stale prior store survives and `futureFull` never seeds. Logged so the
   next audit does not re-trip this.
2. **The yesterday/weekly wrap-up modal auto-presents over the
   WhatIfSlider** on a freshly-seeded `full14plus` store
   (`pendingYesterday`/`pendingWeekly`, `WrapUpCoordinator.swift:110,143`).
   No suppress knob exists. Worked around with
   `LIFECLOCK_SEED_LAST_LOG_DAYS_AGO=2` (no snapshot lands on "yesterday"
   → `pendingYesterday`→nil; 21 snapshots still ≥14 days so `full14plus`
   holds) + `LIFECLOCK_FIXED_DATE=2026-05-13T14:00:00Z` (Wednesday;
   `config.firstWeekday`=2/Monday so `pendingWeekly`→nil). This is a
   knob-gap, not a defect; see Next pass.

### Pro state (`LIFECLOCK_SIMULATOR_PRO_DISABLED` unset — DEBUG default)

Captures: `research/future-profooter-2026-05-16/pro-01-future.png`,
`pro-01-slider-zoom.png`.

- Slider thumbs render at **full opacity** — solid white thumb + saturated
  blue **filled track** to the thumb position. Matches
  `WhatIfSlider.swift:189` `.opacity(isPro ? 1.0 : 0.35)` → 1.0,
  `.disabled(!isPro)`→enabled, `.allowsHitTesting(isPro)`→true.
- **No `lock.fill` glyphs** on any row (the `if !isPro` block at
  `WhatIfSlider.swift:138–146` is correctly absent).
- **No proFooter** (the `if !isPro { proFooter }` at
  `WhatIfSlider.swift:76–78` is correctly absent).
- Reads as a working, interactive Pro tool — hand-tuned, not "Free with
  extra rows". The Pro surface is *cleaner* than Free (zero gate chrome),
  which is the correct direction for "visible Pro-only craft".

### Free state (`LIFECLOCK_SIMULATOR_PRO_DISABLED=1`)

Captures: `research/future-profooter-2026-05-16/free-05-future-clean.png`,
`free-05-slider-zoom.png`.

- Slider thumbs **dimmed (`.opacity(0.35)`)**, no filled track, locked
  (`.disabled(true)`, `.allowsHitTesting(false)`) — verified visually and
  against `WhatIfSlider.swift:189–191`.
- Tinted **`lock.fill`** glyph on every row (`WhatIfSlider.swift:141–144`,
  `.foregroundStyle(.tint).opacity(0.5)`).
- proFooter: code-verified at `WhatIfSlider.swift:96–123` (the proFooter
  itself is below the fold and could not be scrolled into frame — screen
  was locked, computer-use unavailable, `simctl io screenshot` has no
  scroll/tap; see Constraint below). The footer is a `Button` →
  `onLockedTap()`; title "Unlock the simulator" (`.semibold`), concrete
  body, sparkles + chevron, `accessibilityIdentifier(
  "future.whatIfSlider.proFooter")`.
- **Tap route verified at source**: `FutureView.swift:243–247`
  `onLockedTap` sets `paywallScrollTarget = .whatIfSimulator`,
  `paywallPresented = true`; `FutureView.swift:41–44` `.sheet` presents
  `PaywallSheet(scrollTo: paywallScrollTarget)` with
  `.environment(subscriptions)` re-injected at the sheet boundary —
  honors `feedback_observable_environment_sheets.md`. Routes to
  `PaywallSheet(scrollTo: .whatIfSimulator)` exactly as PV-P3 specifies.

### Pro-only-craft scoring

The Free surface is the *same* six-row layout deliberately de-emphasized
(dim thumb + lock glyph + below-fold concrete upgrade footer routing to a
section-targeted paywall anchor). The Pro surface strips ALL gate chrome
and presents a full-opacity, filled-track, interactive control. The
differentiation is purposeful and hand-tuned — **not** "Free with extra
rows" (in fact Pro has *fewer* rows: no footer). **Craft test: PASS.**

## Stretch decisions (operator review)

None. No Stretch follow-up filed — the surface reads Pro-crafted, so per
the PV-P3 contract the verification closes with no follow-up.

## Constraint encountered (not a finding)

The macOS screen was locked for the entire session, so the computer-use
final checkpoint (Pro-touchpoint depth verification) could not run — the
Simulator window is not visible to the compositor while locked, and
clicks/scrolls are unavailable. Per the session Environment contract, fell
back to `simctl io screenshot` (framebuffer, lock-independent) for all
captures, and verified the below-the-fold proFooter content + the
locked-tap → `PaywallSheet(scrollTo:.whatIfSimulator)` route at the source
level (`WhatIfSlider.swift:96–123`, `FutureView.swift:41–44,243–247`). The
on-screen Pro/Free thumb-opacity and lock-glyph differentiation WAS
visually captured and is the load-bearing "visible Pro-only craft"
evidence; only the footer pixels (not its behavior/content) are
source-verified rather than screenshot-verified. This is a harness
limitation, not a product gap.

## Asks

### Resolved this session

None.

### Outstanding (cycle-end batch)

None. (No Feature / Vision-question tier findings. The verification's
expected good outcome — closes clean, no source change — was realized.)

## Regressions caught

None. No source touched; no golden refresh needed. The Future-tab Pro/Free
WhatIfSlider behaves exactly as `WhatIfSlider.swift` + `FutureView.swift`
specify at HEAD `e35e3bf`.

## A11y identifiers added

None added (verification-only). Confirmed already-present, reusable for
future loops: `future.whatIfSlider`,
`future.whatIfSlider.proFooter`,
`future.slider.<dim>` / `future.slider.<dim>.lock`, `future.screen`.

## Vision updates

None. (PV-P3 is a pure verification; no vision.md interaction.)

## Next pass

- **Knob-gap (recommend filing against `LifeClockLaunchConfiguration.swift`):**
  there is no fixture knob to suppress the auto-presenting yesterday/weekly
  wrap-up when seeding `full14plus`. This session worked around it with
  `SEED_LAST_LOG_DAYS_AGO=2` + a non-Monday `FIXED_DATE`, but a dedicated
  `LIFECLOCK_SUPPRESS_WRAPUP=1` knob would make every future Future-tab /
  WhatIfSlider audit one launch instead of a fixed-date puzzle. Surfaced
  here, not auto-implemented (out of scope for a verification prompt).
- If a future session can run with an unlocked screen, do the computer-use
  pass to screenshot the proFooter pixels + perform the real locked-row tap
  → paywall transition (here verified at source + via the visible
  thumb/lock differentiation). No behavior concern — purely closing the
  pixel-evidence gap on the footer block.
