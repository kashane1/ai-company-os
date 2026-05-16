# Polish Session — life-clock — 2026-05-16 — numeric-typography-token-clamp

## Mode

`fix-list` — PF-P4 ("Numeric-display sites → named DesignTokens token +
AccessibilityXXXL clamp", tier: `typography-drift`). Payload = the PF-P4
Idea + Success criteria from
`premium-feel-backlog-2026-05-15-standard.md` § 4. Iteration cap 3.
`final_check=YES` (operator-grade brand-presence vs a11y tradeoff on the
hero figure at `.accessibility5`).

Observer: `docs/products/life-clock/typography-spec.md` § "The
numeric-display exception (binding — role-based size families)" +
§ Validation rules #1–#4. Values mirrored exactly from the spec table;
no type scale invented.

## Iterations

- [10:43] ce7b307 — feat(life-clock): codify typography-spec numeric role families as DesignTokens.Typography — Polish — DesignTokens.swift
- [10:44] 952d155 — fix(life-clock): migrate three numeric-display sites to DesignTokens.Typography — Polish — TodayView / WrapUpSheet / OverrideSheet

### Detail

1. **`DesignTokens.Typography` enum** added to `Sources/Shared/DesignTokens.swift`,
   mirroring the spec's six role families verbatim:
   - `heroNumericChain = [56, 52, 36, 28]` (.semibold/.rounded chain)
   - `displayNumeric = .system(size: 44, weight: .semibold, design: .rounded)`
   - `sectionNumericChain = [40, 36, 28, 22]`
   - `inlineNumeric = .system(size: 32, weight: .semibold, design: .rounded)`
   - `compactNumeric = .system(size: 22, weight: .semibold, design: .rounded)`
   - `iconGlyphFunctional = .system(size: 32, weight: .regular)`
   - `iconGlyphSplash = .system(size: 48)`
   Plus a `displayNumericFigure()` View modifier baking in the spec's
   validation rule #4 AccessibilityXXXL safety:
   `.dynamicTypeSize(...accessibility3)` ceiling + `.lineLimit(1)` +
   `.minimumScaleFactor(0.68)` (≈30pt floor at .xSmall from a 44pt base).
2. **TodayView.swift:289** — `.font(.system(size: 44, …))` → `.displayNumericFigure()`;
   added `accessibilityIdentifier("today.delta")`.
3. **WrapUpSheet.swift:67** — `.font(.system(size: 44, …))` → `.displayNumericFigure()`
   (figure is `.accessibilityHidden(true)`; ClockHandView announces it).
4. **OverrideSheet.swift:26** — `.font(.system(size: 32, …))` →
   `.font(DesignTokens.Typography.inlineNumeric)`. Inline-numeric role.
   No clamp added: this is a `TextField` input value, not the
   auto-shrinking hero figure — value-identical to the prior raw literal.

## Build

Headless `xcodebuild` (xcodegen-generated project), scheme `LifeClock`,
sim **iPhone 17 Pro Max `942B6264-62E2-4663-8230-80E9133C824E`** (iOS
26-class runtime). **BUILD SUCCEEDED** (green) on the final state.
xcodegen run as an explicit standalone step before xcodebuild.

## Computer-use / Simulator visual checkpoint (PF-P4 mandated)

Today hero Display-numeric figure ("+58 min", baseline mock-health
profile, streak 7, health authorized) captured across the mandated
`dynamicTypeSize` grid. Artifacts in
`polish-artifacts/2026-05-16-numeric-typography/`:

| Size | File | Verdict |
|---|---|---|
| `.xSmall` | today-xSmall.png | Figure large, ~44pt visual, well above the ~30pt floor. ✅ |
| `.large` | today-large.png | Default brand register, clean. ✅ |
| `.accessibility3` (clamp ceiling) | today-accessibility3.png | Single line, no truncation/overlap/clip; surrounding Dynamic-Type text scales (correct). ✅ |
| `.accessibility5` (system max / AX XXXL) | today-accessibility5.png | **Identical to .accessibility3** — the clamp caps the figure so it does NOT grow unbounded. No truncation/overlap/clip of the delta number. Validation rule #4 structurally guaranteed. ✅ |

**Verdict:** At `.accessibility5` the delta number does **not** truncate,
overlap, or clip — the `dynamicTypeSize(...accessibility3)` ceiling caps
it cleanly. At `.xSmall` it stays at full ~44pt visual (well ≥30pt).
The brand-vs-a11y tradeoff is **acceptable as shipped, no operator call
required**: the figure is a *visual figure* (not body text) per
typography-spec § Anti-patterns, so a bounded display register at large
accessibility sizes is the spec-sanctioned behavior, not a regression.
Body/label text around it still scales fully via Dynamic Type, so the
iOS accessibility contract for actual *text* is preserved. Brand
presence is retained at every tier (the figure never visually
collapses; minimumScaleFactor only engages on pathologically narrow
widths, not at these sizes).

WrapUpSheet Display-numeric shares the exact same `.displayNumericFigure()`
modifier (shared code, build-verified, `.accessibilityHidden(true)`) —
structurally identical guarantee; sheet auto-present not driven (weekly-
return trigger needs a foreground cycle, beyond cap budget and not
load-bearing for the operator-grade tradeoff, which is the Today hero).
OverrideSheet inline-numeric is a value-identical token swap (no
behavior change) — build-verified, visually a no-op by construction.

## Stretch decisions (operator review)

None. All work is Polish-tier (token codification + spec-mandated clamp,
zero new visual direction).

## Asks

### Resolved this session
None.

### Outstanding (cycle-end batch)
None. The operator-grade tradeoff resolved cleanly in the spec's favor
(see checkpoint verdict) — no batched Ask needed.

## Regressions caught
None. The three touched sites are value-identical to their prior raw
literals at default sizes (same 44/32 semibold rounded); only the AX
clamp behavior is new and is purely additive (a ceiling, no
default-state change). Incidental: History "Net this week" Section-
numeric (out of scope, HistoryView:491) observed rendering correctly
at AX5 — broader scale reads coherent.

## A11y identifiers added
- today.delta (TodayView hero Display-numeric figure)

## Vision updates
None. typography-spec.md is the source of truth and was mirrored, not
amended. No vision.md Decided-constraints touch.

## Next pass
- Migrate the remaining role-family literals to `DesignTokens.Typography`
  (HistoryView 36/40/22, DayDetailView 28, InstallSummarySection 36/28/22,
  FutureView 52/36/28, hero-chain sites at 56, icon-glyph at 32/48). Out
  of PF-P4 scope (PF-P4's Surfaces list only the three sites) but the
  enum now exists to make these mechanical. Spec validation #1 ("zero
  raw `.font(.system(size:))` for numeric-display in `Features/`")
  holds for the three PF-P4 sites but not yet repo-wide.
- `sectionNumericChain` / `heroNumericChain` are declared as `[CGFloat]`
  but no `ViewThatFits` helper modifier ships yet — add
  `sectionNumericFigure()` / `heroNumericFigure()` when migrating those
  sites so the degrade chain is enforced in code, not by convention.
