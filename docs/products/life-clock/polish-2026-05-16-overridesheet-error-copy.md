# Polish Session — life-clock — 2026-05-16 — overridesheet-error-copy

## Mode

`fix-list` — PF-P7 (OverrideSheet error-state copy → on-brand, tone-aware,
actionable). Payload: replace the hardcoded
`errorMessage = "No data for this day yet."` in the `snapshotMissing`
catch with a tone-aware, actionable string; add a
`ToneMode.overrideNoSnapshotMessage` key with gentle/coach/firmDirect
variants that name the condition AND a next step, mirroring the existing
`overrideNotEntitledMessage` precedent in the same file. Iteration cap 3.
No computer-use checkpoint (copy + tone-key change; PR-time review
sufficient).

## Iterations

- [00:35] `<sha-1>` — fix(life-clock): tone-aware OverrideSheet snapshot-missing copy — Polish — OverrideSheet / ToneMode / ToneModeTests

Single logical fix — the tone-key addition, the OverrideSheet wiring, and
the regression tests are one atomic concern (a new tone-aware copy slot
and its only call site). Combined into one commit per the canonical
"one logical fix per commit" rule.

### What changed

- `Sources/App/ToneMode.swift` — added `overrideNoSnapshotMessage`
  computed property directly below `overrideNotEntitledMessage`, mirroring
  its exact structure (doc comment → `switch self` → three cases). Copy:
  - gentle: "Nothing was logged for this day, so there's nothing to
    adjust yet. Pick a day with data to make a correction."
  - coach: "No data logged for this day — there's nothing to override
    yet. Pick a day with data."
  - firmDirect: "No data this day. Nothing to adjust. Pick a day with
    data."
  Each variant names the condition (no data logged) AND the next step
  (pick a day with data), closing the `empty-state-flat` anti-signal.
- `Sources/Features/History/OverrideSheet.swift:76` —
  `errorMessage = "No data for this day yet."` →
  `errorMessage = store.toneMode.overrideNoSnapshotMessage`. Mirrors the
  sibling `overrideNotEntitledMessage` line at :72 exactly — same
  mechanism, no new pattern invented.
- `Tests/ToneModeTests.swift` — 4 new tests pinning the contract:
  all-tones-non-empty, pairwise-distinct, names-condition-and-next-step,
  and a no-flat-literal regression pin. Mirrors the existing
  `testHistoryEmptyStateBody_*` test family's structure.

### Register note

`microcopy-spec.md:29` classifies the override sheet as a correction
surface ("tone-aware but quieter — uses `coach` register copy even when
tone is `firmDirect`"). PF-P7's binding instruction is to mirror the
`overrideNotEntitledMessage` precedent, which itself ships a distinct,
short firmDirect variant. The two are reconciled by keeping the firmDirect
variant terse and neutral (no mortality lexicon, no drama, no value
judgment) — it reads as a quiet correction-surface line, not a dramatic
beat. This satisfies both the prompt's mirror-the-precedent instruction
and the spec's quieter-register intent.

## 3-tone variation evidence (success criterion)

The PF-P7 success criteria ask for a 3-tone screenshot grid confirming
variation. **The live UI path is not statically reachable**, so the grid
is delivered as a deterministic test instead — stronger evidence than a
screenshot for a pure copy/tone change:

- `OverrideService` throws `snapshotMissing` only when no `SnapshotRecord`
  exists for `dayStart` (`OverrideService.swift:43-44, 95-96`).
- `DayDetailView.swift:40-46, 61-68` renders an `EmptyStateView` and does
  NOT render the override-field rows when `snapshot == nil`. The
  `editingField` sheet that presents `OverrideSheet` is therefore
  unreachable on a no-snapshot day through normal navigation. The
  `snapshotMissing` catch in `OverrideSheet.save()` is a defensive
  race-path (snapshot deleted between row tap and Save) — which is
  exactly why PF-P7 itself frames this as "a catch branch" carried as a
  micro-residual and sets `final_check: no`.
- No debug/test touchpoint exists to force-present `OverrideSheet` on a
  missing snapshot, and building one would be scope-creep beyond a
  copy + tone-key change for a defensive branch.

Deterministic substitute: `testOverrideNoSnapshotMessage_TonesDifferPairwise`
proves all three tone variants are pairwise distinct, and
`testOverrideNoSnapshotMessage_AllTonesNameConditionAndNextStep` proves
each names the condition and the next step. Both pass (full suite: 32/32
ToneModeTests green). This is the 3-tone variation grid in test form, and
unlike a screenshot it regression-pins the contract for every future run.

## Sibling catch-branch literals (scope review)

PF-P7 permits reviewing `"Out of range."` and `"Couldn't save."` for the
same treatment IF cheap. **Reviewed; deferred.** They are NOT trivially
the same pattern:

- `OverrideSheet.swift:74` — `"Out of range. \(field.bounds)."`
  interpolates a per-field `field.bounds` string. A tone-aware variant
  would need to thread the interpolated bounds through every tone case
  (3 cases × interpolation), not a flat literal swap — different shape
  from the parameterless `overrideNotEntitledMessage` precedent.
- `OverrideSheet.swift:65` — `"Enter a number."` and
  `OverrideSheet.swift:78` — `"Couldn't save. Try again."` are flat but
  are input-validation / generic-failure strings, not empty-state copy;
  they don't carry the `empty-state-flat` anti-signal PF-P7 targets, and
  bundling them would broaden scope past the prompt's stated fix.

Recommend a follow-up prompt if the operator wants the full
OverrideSheet error family tone-aware; flagged here, not scope-crept.

## Asks

### Resolved this session

- None.

### Outstanding (cycle-end batch)

- None blocking. Optional follow-up noted above (tone-aware treatment of
  the remaining OverrideSheet error literals — `"Out of range."`,
  `"Enter a number."`, `"Couldn't save."`).

## Regressions caught

- None. No screens visited (UI path unreachable by design); change is
  copy + a new tone key + tests. Full ToneModeTests suite re-run green
  (32/32) — no behavioral regression in the tone catalog.

## A11y identifiers added

- None. No elements driven via accessibility tree this session (UI path
  unreachable; verified via test instead).

## Vision updates

- None.

## Next pass

- Optional: a dedicated prompt to make the remaining OverrideSheet error
  literals tone-aware (the bounds-interpolated `"Out of range."` is the
  non-trivial one — needs a parameterized tone method).
- If a debug touchpoint to present `OverrideSheet` in arbitrary states is
  ever added for another reason, retrofit a real 3-tone screenshot grid
  for the visual record.
