# Polish Session — life-clock — 2026-05-15 — supportmoment-toast-lighting

## Mode

`fix-list` — consuming premium-feel backlog prompt **PF-P1**
("SupportMomentToast off-convention shadow → lighting convention").

Payload: replace the hand-rolled `.shadow(color: Color.black.opacity(0.18),
radius: 12, y: 6)` at `SupportMomentToast.swift:63` — the only
off-convention lighting site in `Shared/` — with the shared pinned
lighting convention (`.cardLighting()` / `.lightingDepth`). Adopt the
convention exactly; do not invent shadow values. Iteration cap 3.
`final_check: no` (PR-time review sufficient); light+dark screenshots
of the toast required by the success criteria.

## Iterations

- [00:00] (n/a — recon harness) — Verified the toast is a card-shaped
  surface (`RoundedRectangle(cornerRadius:14)` background) presented from
  Today via `.overlay(alignment:.top)`. The shared `Lighting.swift`
  `.cardLighting()` is the exact modifier every Today `.sectionCard()`
  already uses → correct convention adoption, zero new constants.
- [00:18] `360b8bc` — fix(life-clock): SupportMoment toast adopts shared cardLighting convention — Polish — Today (SupportMoment toast overlay)
- [00:24] `d6284b9` — chore(life-clock): throwaway recon to capture SupportMoment toast light+dark — Polish — Today

Build: headless `xcodebuild` to iPhone 17 Pro Max
(`942B6264-62E2-4663-8230-80E9133C824E`, iOS 26 sim) — **BUILD
SUCCEEDED** before and after the fix, and with the recon compiled into
`LifeClockUITests`.

## Stretch decisions (operator review)

None — single-component Polish-tier fix, zero deviation from the pinned
lighting constants.

## Asks

### Resolved this session

None.

### Outstanding (cycle-end batch)

None. The fix adopted the convention exactly (`.cardLighting()` →
`.lightingDepth(referenceSize: 6)` → opacity 0.22 / offset 0.35·0.85 /
radius 0.55× from `Lighting.Constants`). No constant appeared to need
tuning, so no memory-amendment Vision-question was raised.

## Regressions caught

None. The only source change is the one-line shadow-modifier swap on a
single overlay surface. Light + dark recon captures
(`/tmp/lifeclock-toast/{light,dark}/01-toast-over-today.png`) confirm the
toast presents over the Today cards and the depth shadow now reads as a
subtle lift coherent with the surrounding `.sectionCard()` surfaces
(headline, "Why it changed") rather than the prior harsh hand-rolled
drop. Reads as one product in both schemes.

## A11y identifiers added

None needed — the driven entry point (`today.checkInToolbar`) and the
toast (`today.supportMoment`) already carry stable identifiers.

## Vision updates

None.

## Next pass

- The 2026-05-14 toast log's deferred "consider replacing material with
  `DesignTokens.Palette` brand surface for tighter integration" note is
  now partially addressed (lighting is convention-aligned); the
  `.regularMaterial` fill itself is still material, not a brand palette
  surface. A future pass could evaluate whether a `DesignTokens.Palette`
  fill reads better than `.regularMaterial` for the transient overlay —
  but that is a visual-departure judgement (Stretch/Feature), out of
  scope for this fix-list prompt.
- `UITests/SupportMomentToastRecon.swift` is a throwaway recon; delete
  it once PF-P1's PR-time review is complete.

## Verification

- Changed-surface check: `git diff` is a single one-line modifier swap
  in `SupportMomentToast.swift`; no logic change → no iOS test changes
  required. Recon (`SupportMomentToastRecon`) green for both schemes.
- Raw `.shadow` literal confirmed gone (`grep '.shadow(color:'
  SupportMomentToast.swift` → no match); only `.cardLighting()` remains.
