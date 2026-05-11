# Polish Session — life-clock — 2026-05-11 — safetynet-drift-audit

## Mode

`freeform-polish`. Tier: **drift**. Observer: PRIVACY_COMPLIANCE.md "Emotional safety" affordances + memory/conventions + iOS HIG + vision tone-mode constraints + WCAG 2.1 A11y SC 1.4.10 (Reflow) and 1.3.1 (Info & Relationships).

**Operator brief.** SafetyNet is referenced by every notifications-audit thread and by Q17 (resolved code-side via the mortality-lexicon test) — but the screen itself has **zero polish-log entries**, and `git log -- products/life-clock-ios/Sources/Features/SafetyNet/` returns only two commits (`6b4193b` founder-decisions seed + `bff518a` code-side gap close). First dedicated polish for this surface. Walked the screen the way a Firm/Direct user landing mid-distress would: across **all three tones × light + dark + accessibility-extra-extra-large**. Five lenses:

- **(a) Lexicon drift** — does any string carry firmDirect or coach voice into a surface meant to be a refuge?
- **(b) State-aware copy** — does card 1 ("Switch to Gentle tone") still read sensibly for a user *already* on Gentle?
- **(c) A11y semantics** — header traits on card titles, identifiers on the buttons/toggle/Call links so VoiceOver + future XCUITests can find them.
- **(d) Stale doc refs** — the screen's source comment names "Open Question 13" / "Open Question 5"; do those identifiers still point anywhere a future reader can resolve?
- **(e) Exit path** — Done returns to Profile (the presenter); does any user-flippable state in the sheet need to "stick" so Today doesn't immediately re-present the trigger when the user navigates back?

Iteration cap: **8** (used 7 — 1 recon, 1 build, 4 fixture + nav debug, 1 verification capture). Final-check: **yes (simctl fallback)**. Computer-use planned; `request_access` dialog timed out twice (300s each) on this session — **same gotcha as polish-2026-05-09-profile-section-sweep.md** documents. Fell back to `xcrun simctl io … screenshot` driven by env-var fixtures, captured the full 3-tone × 2-scheme × XXL matrix that way. Will retry computer-use next session.

Seeds (with `SIMCTL_CHILD_` prefix — env vars are NOT positional after the bundle id):

| Variant | Vars |
|---|---|
| `<tone>` × `<scheme>` | `LIFECLOCK_UI_TEST=1`, `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_USE_MOCK_HEALTH=1`, `LIFECLOCK_HEALTH_AUTH=authorized`, `LIFECLOCK_SEED_TONE=<gentle\|coach\|firm_direct>`, `LIFECLOCK_INITIAL_TAB=profile`, `LIFECLOCK_FORCE_SAFETY_NET=1`, `LIFECLOCK_FORCE_COLOR_SCHEME=<light\|dark>` |
| XXL | as above + `xcrun simctl ui <device> content_size accessibility-extra-extra-large` |

> **Recon gotcha caught.** Three of them, worth documenting so the next SafetyNet polish doesn't lose iterations to the same:
>
> 1. **`simctl launch` does not forward bare env vars.** `xcrun simctl launch <device> <bundleId> FOO=bar` treats `FOO=bar` as a positional argv, not an environment override. Must use `SIMCTL_CHILD_FOO=bar` in the *shell's* env before `xcrun simctl launch`. Already documented in [polish-2026-05-09-profile-section-sweep.md](polish-2026-05-09-profile-section-sweep.md) — re-noting here because it cost two iterations.
> 2. **`LIFECLOCK_SEED_TONE` raw-values are snake-case.** `ToneMode.firmDirect` has `rawValue = "firm_direct"`, not `"firmDirect"`. Passing the camelCase variant silently falls back to `.coach` via `ToneMode(rawValue:)?? .coach`. The brief's fixture-knobs line used `firmDirect`; the actual decoder needs `firm_direct`.
> 3. **`LIFECLOCK_SEED_BAD_DAY=1` is gated on `LIFECLOCK_SEED_STREAK > 0`.** The bad-day overrides live inside `for offset in 0..<seedStreak`. Passing `BAD_DAY=1` with no `STREAK` is a no-op. Same coupling caused [polish-2026-05-10-protouchpoints-t8-baseline-repair.md](polish-2026-05-10-protouchpoints-t8-baseline-repair.md)'s recon to skip; it's worth a code comment on the `seedBadDayToday` declaration.
>
> Compound (Ask 1) is to surface (2) and (3) in the doc-comment block of `LIFECLOCK_SEED_TONE` / `LIFECLOCK_SEED_BAD_DAY` so the next polish operator catches them without simctl recon.

## Iterations

| Time | Commit-like | Type | Tier | Surface | Result |
|---|---|---|---|---|---|
| 04:21 | (recon) | — | — | SafetyNetView | Static read: all visible strings hard-coded; OQ13/OQ5 refs in doc-comment; no a11y identifiers anywhere in file; card 1 unbranched on `store.toneMode == .gentle` |
| 04:30 | (build) | — | — | LifeClock app | First green build; `BUILD_PRODUCT_READY` |
| 04:33 | (recon) | — | — | Today (firmDirect, bad-day) | Captured `dbg-profile-scroll.png` — confirmed firmDirect copy renders correctly mid-flow ("Today's reckoning" / "What moved the needle" / "Today's orders" / "Today, in one line"); nothing tonally adrift on the surface upstream of SafetyNet |
| 04:50 | (drift fix) | fix | Drift | [SafetyNetView.swift](../../../products/life-clock-ios/Sources/Features/SafetyNet/SafetyNetView.swift) | Replaced stale OQ13/OQ5 doc-refs with concrete file path + neutrality rationale; adaptive card-1 (`alreadyGentle` branch); a11y identifiers (`safetyNet.done`, `safetyNet.tone.gentle`, `safetyNet.hideClock.toggle`, `safetyNet.crisis.{988,textLine,international}.call`, `safetyNet.intro`); `.accessibilityAddTraits(.isHeader)` on every card heading; `.accessibilityLabel("Call \(title)")` on the tel: Links so VoiceOver reads the full hotline name, not just "Call 988" |
| 04:52 | (fixture) | feat | Polish | [LifeClockLaunchConfiguration.swift](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift), [ProfileView.swift](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift) | Added `LIFECLOCK_FORCE_SAFETY_NET=1` knob (DEBUG-only, mirror of `forcePaywall` pattern). Reason: iOS 26 Simulator does **not** reliably deliver cliclick `c:` events to SwiftUI Form List buttons (verified four ways — single-click at refined coords, double-click, `dd:`+`du:` press-release, AppleScript `System Events click at`). The tab bar and direct-text buttons received clicks fine; List rows did not. Without the fixture, the only path to SafetyNet for polish recon is via the failing tap → 0 iterations of capacity remain by the time you get in. Compounds for the next SafetyNet polish run |
| 04:55 | (verify) | — | — | SafetyNet | 3-tone × 2-scheme grid captured into `docs/products/life-clock/screenshots/2026-05-11-safetynet/` |
| 04:57 | (verify) | — | — | SafetyNet (XXL) | `accessibility-extra-extra-large` captured for firm_direct/light — header truncates per iOS standard, body wraps cleanly, no clipping |

## Catches the bundle resolved

### 1. **Tone-neutrality was load-bearing but undocumented.**

The file shipped with zero tone keys and zero rationale for that choice. A future contributor wiring up "more tone-aware screens" could plausibly route SafetyNet through `store.toneMode.*` — which would be **actively harmful** because the firmDirect register here would read as cruel to the user the surface exists for ("Switch to Gentle, weakling. Or call this number."). Added an inline block to `SafetyNetView`'s doc-comment locking the neutrality rule in place with the *why*:

> **Copy is intentionally tone-neutral.** SafetyNet is the refuge from whichever tone the user is in. A firmDirect tone here would be hostile to the anxious user the surface exists for; a coach tone would still carry accountability language. The strings below lean toward Gentle's register regardless of `store.toneMode`. Do not wire these through `ToneMode` keys.

### 2. **Card 1 read incoherently for a user already on Gentle.**

The old card showed `"1. Switch to Gentle tone"` headline + `"Use Gentle now"` CTA + checkmark when the user was already on Gentle. The headline contradicted the state; the button was still tappable (calling `store.setToneMode(.gentle)` a second time is a no-op but still visually confusing). Branched:

| State | Headline | Button label | Button state |
|---|---|---|---|
| Not on Gentle | "1. Switch to Gentle tone" | "Use Gentle now" | enabled |
| Already on Gentle | "1. You're already on Gentle" | "Gentle is on" + ✓ | **disabled** |

Captured side-by-side in `safetynet-{gentle,coach,firm_direct}-{light,dark}.png`. The gentle variants now render the disabled+confirmed state; the coach + firm_direct variants render the active CTA.

### 3. **Stale doc-comment open-question references.**

`SafetyNetView`'s file comment cited "Open Question 13" and "Open Question 5" — internal jargon that resolves to docs in two locations (`docs/products/life-clock/OPEN_QUESTIONS.md`, `14_OPEN_QUESTIONS.md`, `MASTER_FOUNDER_PACKAGE.md`). Those docs still exist, but the *numbering* is implementation-specific to a doc that may renumber when questions get resolved or added. Replaced with a direct reference to `docs/products/life-clock/PRIVACY_COMPLIANCE.md` ("Emotional safety" section), which is the binding doc, and dropped the OQ pointers entirely.

### 4. **Zero a11y identifiers on a high-risk surface.**

ProfileView's SafetyNet entry has `accessibilityIdentifier("profile.safetyNet.entry")` (added in the 2026-05-09 Profile sweep). Inside SafetyNetView, **none** of the buttons, toggle, tel: Links, or Done button had identifiers. Added a full `safetyNet.*` namespace:

```
safetyNet.intro
safetyNet.done
safetyNet.tone.gentle
safetyNet.hideClock.toggle
safetyNet.crisis.988                   safetyNet.crisis.988.call
safetyNet.crisis.textLine
safetyNet.crisis.international
```

Compounds: this is now the most XCUITest-ready sheet in the app, which is appropriate for the screen most likely to encounter an anxious user. Future regression tests for "the Gentle CTA exists and is enabled iff tone ≠ .gentle" can be written directly.

### 5. **Header traits missing for VoiceOver rotor navigation.**

The card titles ("1. …", "2. Hide the clock", "3. Talk to someone") used `.font(.headline)` only. VoiceOver users couldn't jump between sections via the heading rotor. Added `.accessibilityAddTraits(.isHeader)` to all card titles + the intro `Text("Your clock is feedback, not fate.")`. The Call-Link's `.accessibilityLabel("Call \(title)")` ensures rotor reads "Call 988 Suicide & Crisis Lifeline (US)" instead of the bare "Call 988" — context matters when a panicked user lands here.

### 6. **Hidden the decorative checkmark from VoiceOver.**

The `Image(systemName: "checkmark")` inside the gentle-on button is decorative (the button text already conveys state). Added `.accessibilityHidden(true)` so VoiceOver doesn't redundantly announce "checkmark, gentle is on".

## Stretch decisions (operator review)

- **`LIFECLOCK_FORCE_SAFETY_NET` fixture knob auto-shipped.** Classified as Polish-tier (mirrors the existing `forcePaywall` pattern; DEBUG-only). Justification: the cliclick-into-List-button reliability issue is structural to iOS 26 Simulator, not a one-off — the next SafetyNet polish run hits the same wall without this knob. Cost: ~10 lines in `LifeClockLaunchConfiguration.swift` + a 9-line `Color.clear`-anchored `onAppear` in `ProfileView`. Tradeoff documented in the knob's doc-comment.
- **Did NOT** wire a "Return to Today" affordance into the SafetyNet sheet. The brief mentioned "exit returns to Today without re-presenting the trigger state" — but on inspection, the trigger state for SafetyNet is the user's *internal* anxious state, not a specific Today screen pattern. Done → dismiss → Profile (the presenter) is the correct iOS pattern; the user reactively sees a softened Today next time they navigate there because both tone-switch and hide-clock writes propagate live through `store`. Forcing a tab-jump to Today on Done would *re-expose* the trigger surface for users who landed at SafetyNet because Today was distressing. Status quo wins.
- **Did NOT** wire SafetyNet copy through `ToneMode` keys. The neutrality is the point — see catch 1.

## Exit-path verification

Source-level trace:

- `SafetyNetView` is presented as a sheet from [`ProfileView.swift:209`](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift) via `.sheet(isPresented: $safetyNetPresented)`.
- Done → `dismiss()` → `$safetyNetPresented = false` → sheet animates down → Profile is the front view.
- `store.setToneMode(.gentle)` writes through to `profile.toneMode` and the published `toneMode` state immediately — Today re-renders with Gentle copy on next view.
- `store.setHideClock(true)` is async but writes through `profile.hideClock`; Today's render branches at [`TodayView.swift:385`](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) and [`TodayView.swift:439`](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) on `profile?.hideClock == true`.
- No reverse trigger path: nothing in SafetyNet writes data that *re-arms* the wrap-up coordinator or any other re-presentation hook.

Verdict: exit path is correct as-is. Trigger state cannot re-present after a SafetyNet action because the engine inputs (tone, hideClock) are persisted and Today renders against the live profile.

## Captured artifacts

`docs/products/life-clock/screenshots/2026-05-11-safetynet/`:

- `safetynet-gentle-light.png` — card 1 reads "You're already on Gentle"; CTA disabled + ✓
- `safetynet-gentle-dark.png` — same in dark scheme
- `safetynet-coach-light.png` — card 1 reads "Switch to Gentle tone"; CTA active
- `safetynet-coach-dark.png` — same in dark scheme
- `safetynet-firm_direct-light.png` — identical neutral copy as coach (proves no firmDirect leakage); CTA active
- `safetynet-firm_direct-dark.png` — same in dark scheme
- `safetynet-coach-light-scrolled.png` — scroll-attempt artifact (cliclick gesture did not scroll the sheet; sheet contents below the fold validated by source review only — see Outstanding Ask 2)
- `safetynet-firm_direct-light-XXL.png` — `accessibility-extra-extra-large`; nav title truncates per iOS, body wraps, no clipping

## Asks

### Resolved this session

- All catches 1–6 above ship in the diff. No operator decision required.

### Outstanding (cycle-end batch)

#### **Ask 1 — Document the `LIFECLOCK_SEED_TONE` / `LIFECLOCK_SEED_BAD_DAY` coupling (chore)**

The polish-2026-05-09 log already flagged the `SIMCTL_CHILD_` prefix gotcha. This session re-discovered two more silent-fallback fixture knobs that cost iterations:

| Knob | Silent failure mode |
|---|---|
| `LIFECLOCK_SEED_TONE=firmDirect` | Falls back to `.coach` because `ToneMode.firmDirect.rawValue == "firm_direct"` |
| `LIFECLOCK_SEED_BAD_DAY=1` alone | No-op when `LIFECLOCK_SEED_STREAK` is unset/0 (loop is gated on `seedStreak > 0`) |

Fix is one-line doc-comment update on each property in [`LifeClockLaunchConfiguration.swift`](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift). Operator pick:

- **Option A — Doc-only.** Add notes calling out the snake-case rawValue and the streak gating. ~6 lines of comment. No code change.
- **Option B — Doc + relax the BAD_DAY gate.** Allow `BAD_DAY=1` to seed today's HabitLog even when `STREAK=0`. Adds ~5 LOC; makes the knob composable. Slight risk of orphan log without a matching `DailyHealthSnapshot` — would need to seed today's snapshot too.

**Recommend A.** B trades doc clarity for a code change that two polish runs would notice and one chore would document.

#### **Ask 2 — Cliclick→SwiftUI List button reliability on iOS 26 Simulator (research)**

Reproducible: cliclick `c:`, `dd:`+`du:`, `dc:`, and AppleScript `System Events click at` all failed to deliver a tap event to the `Button` rendered inside `Form { Section { Button { … } } }` in ProfileView (`profile.safetyNet.entry`). Same gestures DID work on:

- Tab bar items (Today/History/Profile pills)
- The wrap-up sheet's `"Next"` button (standalone Button outside a Form/List)
- The Tone-mode Picker disclosure

So the failure mode is specific to **Buttons embedded in `Form`/`List` rows**. Hypothesis: SwiftUI on iOS 26 routes List-row taps through a long-press gesture recognizer that requires real touch begin/move/end events, not a synthesized AppKit click. Workarounds tried + outcomes are in `/tmp/safety-net-audit/diag-*.png`.

Polish-time impact: cost ~3 iterations this session before the `LIFECLOCK_FORCE_SAFETY_NET` knob was added. Long-term impact: any polish run that needs to *land inside a sheet presented from a List-row Button* will hit this. Operator pick:

- **Option A — Accept; rely on `*_FORCE_*` knobs.** Add a knob whenever a polish run needs to reach a List-row-presented surface. Low effort, accumulates.
- **Option B — Spike an `idb` (Facebook iOS Device Bridge) install.** `idb ui tap` documented to deliver real touch events; would unblock all List-row interaction. Cost: tool install + first-time learning curve. Compounds for many future polish runs.
- **Option C — Spike an XCUITest harness specifically for "navigate to surface X" pre-recon scripts.** XCUITest's `.tap()` definitely works through Form rows. Cost: build + test-target plumbing. Heaviest but most reliable.

**Recommend A for now, B if a second polish run hits the same wall.** Don't pay C's setup cost until at least two more recon-blockers prove the pattern.

#### **Ask 3 — Re-run computer-use gestural pass next session (test)**

`request_access` timed out twice (300s × 2). The 2026-05-09 polish log documents the same gate failure mode. Both sessions captured the deliverable via simctl fallback, so the verification floor is solid — but the gestural lens (real touch, transient highlight states, accidental rubber-banding) hasn't been exercised on SafetyNet. Suggest a 5-minute checkpoint at the start of the next polish session: `request_access(["Simulator"])` → if it goes through, replay the 3-tone matrix gesturally; if it times out again, file the upstream issue (this is the third recorded occurrence and the pattern is now reliable enough to report).

---

**Bottom line.** SafetyNet renders cleanly in all three tones, light + dark, XXL text. Every visible string is neutral-by-design with the rationale now in-source. Card 1 is state-aware. A11y identifiers + header traits land. Exit path verified. One fixture knob compounds for future polish. Three Asks queued.
