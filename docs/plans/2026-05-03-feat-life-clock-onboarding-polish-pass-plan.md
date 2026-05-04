---
title: Life Clock onboarding polish pass — input UX, legend, skip, multi-dial preview, locked header with reactive hands
type: feat
status: active
date: 2026-05-03
origin: docs/brainstorms/2026-05-01-life-clock-reveal-onboarding-anchor-dial-brainstorm.md
---

# Life Clock onboarding polish pass

## Enhancement summary

**Deepened on:** 2026-05-03 via parallel research + review agents.

**Research agents used:** codebase-prior-art (Explore), SwiftUI-persistent-header
(general), Observable-perf-and-debounce (general), HealthKit-skip-UX (general),
multi-dial-onboarding-UX (general), sensitive-input-and-legend-a11y (general),
architecture-strategist (review), code-simplicity-reviewer (review).

### Key changes after research

1. **Phase 1 simplified.** Spike a `ZStack`-over-`NavigationStack` layout
   first (header above stack, body inside) — preserves swipe-back on
   non-terminal screens and is the architecture-strategist's recommended
   less-invasive path. Custom `OnboardingShell` is the fallback only if the
   spike's identity stability fails. **Old plan committed to the rewrite
   prematurely.**
2. **Drop the `draft.bind(_:engine:)` helper** (architecture + simplicity
   both flagged this). Replace with a single shell-level
   `.onChange(of: draft.<inputs>)` reactor that fires the debounced
   recompute. Engine stays out of the model; one policy in one place.
3. **Three dials, not four.** Cut Stress; ship Activity / Food / Sleep.
   Multi-dial UX research and the simplicity reviewer agree — four sliders
   sit at working-memory ceiling and don't fit Dynamic Type XL on smaller
   iPhones.
4. **Soft-skip pattern on HealthKit**, not equal-weight Skip. Primary
   "Connect Apple Health" button; secondary low-emphasis "Not now" link
   beneath. Apple HIG + Cal AI / MyFitnessPal precedent.
5. **No placeholder on the age TextField.** "e.g. 62" introduces anchoring
   bias on a sensitive value — research-cited (Tversky-Kahneman + NN/g).
   The screen's question itself is the prompt.
6. **Legend uses progressive disclosure.** Full legend on the first
   multi-color screen (`bigNumberPenalty`); `info.circle` popover on
   `recoveryPreview`; no legend on the single-color remaining screen
   (label inline). Each legend container groups as one
   `.accessibilityElement(children: .combine)` — single VoiceOver swipe.
7. **Drop the two-beat auto-advance title** on the merged
   `lifeGridRemaining` screen — pick one title ("This is what's still
   ahead"), no timer, no state machine. Simplicity win.
8. **`ageAtDeath` stays `Int`**, not `Int?`. Gate Continue on a local
   parseable-string flag instead of nil-typing the value through
   `materialize()` and the bucket helper.
9. **Spring is the brand motion.** Match `LifeClockMascotView.swift:127`
   (`.interpolatingSpring()`) for hand updates. Shell-level body
   transition uses `.easeInOut(duration: 0.3)` per Apple HIG 2025 and
   established 0.25–0.35s onboarding-micro-transition band.
10. **Debounce stays, but at the reactor**, 80ms via cancellable
    `Task.sleep` (Swift 6 idiomatic). Slider thumb binds to the raw
    `@Observable` property synchronously; only the *engine recompute* is
    debounced. Avoids the "stuck thumb" failure mode.
11. **Add `deprecatedScreens` mapping** in `OnboardingScreen.swift` so
    historical funnel data joins old `lifeGridFull` events to the merged
    `lifeGridRemaining` step. Cheap analytics-continuity guarantee.
12. **Split Phase 4a (the `lifeGridFull` merge) into its own PR**, landed
    *before* Phase 1. Isolates the analytics-contract change from the
    structural change — easier blame, easier revert.
13. **`OnboardingShell` (if needed) is generic** `<Content: View>` — never
    `AnyView`. `AnyView` defeats SwiftUI diffing and partially undoes the
    identity-stability win we'd be paying for.

### New considerations discovered

- **Demo-gaming risk** on the multi-dial pre-question screen: users may
  drag the dials to "make the mascot happy" rather than to reflect their
  state. The brainstorm already mitigates this (the same dimensions get
  re-asked as honest single-question screens later) — call it out
  explicitly so it stays mitigated post-launch.
- **Color-blind palette tuning.** Apple `Color.green` / `Color.red`
  default pair fails deuteranopia/protanopia (~8% of men). The grid
  already encodes filled-vs-outlined, which satisfies WCAG 1.4.1 — but
  consider swapping `.green` → `.teal` or `.red` → `.orange` for the dot
  fills if cheap, both test well on Coblis simulators (Okabe-Ito 2008,
  WWDC 2022 "Crafting accessible experiences").
- **No existing debounce primitive in this codebase.** Async timing today
  is imperative (`DispatchQueue.main.asyncAfter`, `Timer`). Introducing a
  one-shot cancellable `Task` pattern in the shell is fine but document
  it in the file header so future work doesn't fork another approach.

## Overview

Five targeted fixes to the v2 reveal-onboarding flow shipped under the
[reveal-onboarding-anchor-dial brainstorm](docs/brainstorms/2026-05-01-life-clock-reveal-onboarding-anchor-dial-brainstorm.md).
The flow is structurally good (cold-open → previews → reactive demo →
collection → escalator → reveal+dial → recovery → HealthKit → paywall) but
five rough edges are hurting first-impression polish:

1. Parents' age-at-passing input forces a +/- stepper — slow and emotionally
   bad for someone who lost a parent young.
2. The "N more years of …" recovery screen shows colored dots without
   explaining what the colors mean; an earlier screen *talks* about dots
   without showing any.
3. The HealthKit screen has no skip — only a "Connect" CTA.
4. The pre-question reactive demo has a single Activity slider; the user
   leaves the screen without seeing the app respond to anything else.
5. The mascot + "Life Clock" wordmark are *re-rendered* on every screen
   transition (they live inside `OnboardingScaffold`), so the clock hands
   reset visually instead of feeling like one continuous, reactive object.
   Hands also only animate on Continue — not on per-input mutations.

This plan addresses all five together because #5 is a structural change
that requires touching every screen anyway, so the smaller fixes ride
along cleanly.

## Problem statement / motivation

The v2 onboarding already nails the brand — clock-as-mascot, dot-grid life
metaphor, reactive estimate. But the per-screen polish doesn't match the
ambition:

- **Stepper friction.** A user whose mother died at 42 has to tap "−" 38
  times. The Stepper was a quick MVP choice
  ([DataCollectionScreens.swift:676](products/life-clock-ios/Sources/Features/Onboarding/Screens/DataCollectionScreens.swift)).
- **Dots without orientation.** `LifeGridFullView` and `LifeGridRemainingView`
  describe dots as weeks; by the time `RecoveryPreviewView` colors them
  blue/red/green there's no key, and the user has been 3–4 screens between
  "you'll see dots" and "here are your dots."
- **No HealthKit out.** `HealthKitAuthView` only renders Connect/Continue.
  A user who isn't ready will tap Connect to dismiss, then hit Don't Allow,
  which is worse than a clean Skip.
- **Single-dial demo undersells.** `ReactiveSliderView` only demos Activity.
  The product covers food, sleep, stress, social — none of which the
  pre-question demo previews.
- **Header lives inside each screen.** `OnboardingScaffold` renders
  `OnboardingHeader` at line 57 of
  [DataCollectionScreens.swift](products/life-clock-ios/Sources/Features/Onboarding/Screens/DataCollectionScreens.swift),
  so every NavigationStack push tears it down and rebuilds it. Visually the
  hands "snap" between screens. Per-input mutations don't update the hands
  at all — `recomputeEstimate` only fires from the scaffold's Continue
  button (line 75).

## Proposed solution (high-level)

Five coordinated changes, sequenced so #5 (the structural one) lands first
and the rest plug into the new container:

| # | Change | Surface |
|---|--------|---------|
| 1 | Persistent header + reactive-on-input hands | `OnboardingCoordinator`, `OnboardingScaffold`, all screens |
| 2 | Multi-dial reactive demo | `ReactiveSliderView` |
| 3 | Numeric text input for parent age-at-passing | `FamilyLongevityForm` |
| 4 | Color legend on dot screens; merge first dots screen with the recovery dots screen | `LifeGridFullView` + `LifeGridRemainingView` + `RecoveryPreviewView`, `LifeGridDotView` |
| 5 | Skip option on HealthKit screen | `HealthKitAuthView` |

## Technical approach

### Phase 1 — Persistent header with reactive hands (structural)

**Goal:** the mascot + wordmark stay visually fixed across all onboarding
screens; only the body region transitions; the clock hands respond to *any*
input mutation, not just Continue.

**Approach (revised after deepen-plan):** spike the **less-invasive
ZStack-over-NavigationStack** layout first. Header lives in a parent VStack
*above* the existing `NavigationStack`. Because the header is never inside
the stack's view hierarchy, SwiftUI assigns it stable identity for the
whole onboarding lifetime — one `onAppear`, zero rebuild on push/pop. We
keep the existing `NavigationStack(path:)` and the swipe-back gesture for
non-terminal screens (still killed on dial Confirm via `path = [...]` per
[OnboardingCoordinator.swift:122](products/life-clock-ios/Sources/Features/Onboarding/OnboardingCoordinator.swift)).

If the spike reveals identity instability (e.g., the header *does* re-render
because the parent VStack invalidates when the embedded NavigationStack
pushes — empirically uncommon but possible with shared `@Observable`
ancestor state), fall back to the custom `OnboardingShell` (ZStack +
`.id(currentScreen)` + `.transition(...)`) as the second option. **Do not
build the custom shell first.**

#### Sketch — preferred layout

```swift
struct OnboardingCoordinator: View {
    @State private var path: [OnboardingScreen] = []
    @State private var draft = OnboardingDraft()
    var body: some View {
        VStack(spacing: 0) {
            OnboardingHeader()                        // single instance
                .padding(.horizontal, 24)
            NavigationStack(path: $path) {
                ColdOpenView(onContinue: { path.append(.welcome) })
                    .navigationDestination(for: OnboardingScreen.self,
                                           destination: destination)
                    .toolbar(.hidden, for: .navigationBar)
            }
        }
        .onChange(of: draftInputsKey) { _, _ in
            scheduleRecompute()                       // shell-level reactor
        }
        .environment(draft)
    }
}
```

`draftInputsKey` is a computed property combining the input fields whose
mutations should drive the mascot (smoking, alcohol, strength, cardio,
sleep, diet, body comp, family, stress, social). One `.onChange`, one
debounced reactor — no per-binding wrapping, no engine reference inside
the draft.

#### `products/life-clock-ios/Sources/Features/Onboarding/OnboardingShell.swift` (new)

New top-level container:

```swift
struct OnboardingShell: View {
    @Environment(OnboardingDraft.self) private var draft
    let currentScreen: OnboardingScreen
    let body: AnyView  // current screen's body, header-stripped

    var body: some View {
        VStack(spacing: 0) {
            OnboardingHeader()  // single instance, lives here
                .padding(.horizontal, 24)
            ZStack {
                self.body
                    .id(currentScreen)
                    .transition(.asymmetric(
                        insertion: .opacity.combined(with: .move(edge: .trailing)),
                        removal:   .opacity.combined(with: .move(edge: .leading))
                    ))
            }
            .animation(.easeInOut(duration: 0.28), value: currentScreen)
        }
    }
}
```

#### `products/life-clock-ios/Sources/Features/Onboarding/OnboardingCoordinator.swift`

Replace the `NavigationStack(path:)` body with a single `OnboardingShell`
that observes a `@State currentScreen: OnboardingScreen`. Back-nav becomes
a coordinator-managed stack (already present as the `path` array) — pop is
`path.removeLast()` driven by a back chevron rendered inside the shell's
body region (small affordance, top-leading of the body slot, hidden on
`coldOpen`). This loses NavigationStack's swipe-back gesture. **Acceptable
trade-off** — onboarding is a forced linear flow and we already kill back
navigation after the dial Confirm at `OnboardingCoordinator.swift:122`.

#### `products/life-clock-ios/Sources/Features/Onboarding/Screens/DataCollectionScreens.swift`

Strip `OnboardingHeader` from `OnboardingScaffold` (currently line 57).
Same for the bare `OnboardingHeader` calls in
[RevealEscalatorScreens.swift:31](products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift)
(`AnalyzingView`). After this change, no screen renders the header
directly — the shell owns it.

#### Reactive hands on every input

Today the mascot reads `draft.lastDelta`, which is only updated when
`OnboardingScaffold` calls `draft.recomputeEstimate(...)` from its Continue
button. We need:

1. **One shell-level reactor, not N per-binding wrappers.** Drop the
   originally-proposed `draft.bind(_:engine:)` helper (architecture +
   simplicity reviewers both flagged it as a layering violation — model
   shouldn't reference engine, and threading it through every screen is
   premature abstraction). Instead, attach a single `.onChange(of:)` at
   the coordinator that watches a composite key derived from the
   draft's input fields:

   ```swift
   // OnboardingCoordinator
   private var draftInputsKey: Int {
       var hasher = Hasher()
       hasher.combine(draft.smokingStatus)
       hasher.combine(draft.alcoholFrequency)
       hasher.combine(draft.strengthFrequencyPerWeek)
       hasher.combine(draft.cardioMinsPerWeek)
       hasher.combine(draft.sleepGoalHours)
       hasher.combine(draft.dietQualityBaseline)
       hasher.combine(draft.heightCm)
       hasher.combine(draft.weightKg)
       hasher.combine(draft.parentMotherAlive)
       hasher.combine(draft.parentMotherAgeAtDeath)
       hasher.combine(draft.parentFatherAlive)
       hasher.combine(draft.parentFatherAgeAtDeath)
       hasher.combine(draft.perceivedStressScore)
       hasher.combine(draft.lonelinessScore)
       return hasher.finalize()
   }
   ```

   Sliders bind directly to the raw `@Observable` property (sync — thumb
   tracks the finger; never debounce the slider's own value or you get a
   "stuck thumb" failure mode per the SwiftUI-perf research).

2. **Debounced recompute via cancellable `Task`** (Swift 6 idiomatic; no
   Combine bridge needed):

   ```swift
   @State private var recomputeTask: Task<Void, Never>?

   private func scheduleRecompute() {
       recomputeTask?.cancel()
       recomputeTask = Task { @MainActor in
           try? await Task.sleep(for: .milliseconds(80))
           guard !Task.isCancelled else { return }
           draft.recomputeEstimate(using: ClockEngine(clock: store.clock))
       }
   }
   ```

   80ms (not the original 120ms) is the lower-jank-risk window from the
   debounce research: short enough that the mascot reads as "settling,"
   long enough to coalesce slider-drag bursts.

3. **Mascot animation curve.** Don't introduce a new curve — match the
   existing brand motion at
   [LifeClockMascotView.swift:127](products/life-clock-ios/Sources/Shared/LifeClockMascotView.swift):
   `.animation(reduceMotion ? nil : .interpolatingSpring(), value: minutesDelta)`.
   The mascot already does the right thing when `minutesDelta` changes;
   no view-side animation work needed beyond ensuring the debounced
   pipeline ends up writing to `draft.lastDelta`.

4. **Body transition (only if we fall back to the custom shell).** Use
   asymmetric slide+fade at 0.3s `.easeInOut`, which matches Apple HIG
   2025 onboarding-micro-transition norms (0.25–0.35s band) and the
   `LifeGridDotView.swift:65–71` precedent of `.easeInOut(0.6s)` for grid
   work. Reserve `.scale` — HIG says it reads as modal/alert.

**Reduce-Motion respect:** when
`@Environment(\.accessibilityReduceMotion)` is true, the shell's transition
collapses to `.identity` and the mascot's hand animation is replaced with
an immediate snap. Mirrors the pattern already in
[LifeGridDotView.swift:65](products/life-clock-ios/Sources/Shared/LifeGridDotView.swift).

### Phase 2 — Multi-dial reactive demo

**File:** `products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift`
(`ReactiveSliderView`, lines 204–251).

Replace the single Activity slider with **three** dials (revised from
the original four — see Enhancement summary item 3) covering the major
domains the app actually adjusts (read directly from
[`ClockEngine.lifestyleAdjustmentYears`](products/life-clock-ios/Sources/Engines/ClockEngine.swift)):

- **Activity** (existing — strength + cardio combined)
- **Food** (`dietQualityBaseline`)
- **Sleep** (`sleepGoalHours`)

Three keeps the aggregate mentally tractable (Miller / Cowan working-memory
ceiling), fits Dynamic Type XL on iPhone SE-class screens without scrolling,
and matches NN/g's "Sliders: Definition and Best Practices" recommendation
for low-effort exploratory inputs. Stress is collected later in the honest
single-question screens — keeping it out of the demo also reduces the
demo-gaming risk (users dragging dials to make the mascot happy rather
than to reflect their state).

Each dial is bounded; aggregate the four normalized values (each ∈ [0,1])
into the same demo year-band that drives the mascot today
(`EngineRevealPresenter.mascotDelta`). Demo-only — no draft writes, no
engine call. The big number above the dials still animates as you drag any
of them, so the user sees the clock and the number react to four different
inputs before they answer a single question.

**Layout:** three native vertical `Slider`s, each ~44pt tall with caption-2
endpoint labels ("Sedentary / Active", "Junk / Whole foods", "5 hrs / 9
hrs"). Headline number + Continue stay at the bottom. Native `Slider` is
accessible by default (`adjustable` trait + announced value); avoid radial
dials — they regress for VoiceOver and Dynamic Type users per NN/g + Apple
HIG accessibility guidance.

**Accessibility:** each slider gets its own `accessibilityIdentifier`
(`onboarding.reactiveSlider.activity`, `.food`, `.sleep`) so the existing
UI test that pokes the slider can be expanded screen-by-screen.

**Demo-gaming guardrail:** the same dimensions are re-asked as honest
single-question screens later in the flow (`strength`, `cardio`, `diet`,
`sleep`). This is already in the brainstorm; surface it in the screen's
implementation comment so future work doesn't accidentally collapse the
demo and the data-collection screens into one.

### Phase 3 — Numeric text input for parent age-at-passing

**File:** `products/life-clock-ios/Sources/Features/Onboarding/Screens/DataCollectionScreens.swift`
(`FamilyLongevityForm`, line 676).

Replace:

```swift
Stepper("Age at passing: \(ageAtDeath)", value: $ageAtDeath, in: 20...110)
```

with (revised — no placeholder, simpler typing):

```swift
@State private var ageString: String = ""

HStack {
    Text("Age at passing")
    Spacer()
    TextField("", text: $ageString)                    // no placeholder
        .keyboardType(.numberPad)
        .multilineTextAlignment(.trailing)
        .frame(maxWidth: 80)
        .textFieldStyle(.roundedBorder)
        .accessibilityIdentifier("onboarding.familyAgeAtDeath")
}
```

**Why no placeholder.** "e.g. 62" introduces anchoring bias on a sensitive
value (Tversky-Kahneman 1974; Baymard 2022 form-design replication;
NN/g — "Placeholders in Form Fields Are Harmful," Sherwin 2014). The
screen's own question ("How old was she?" / "How old was he?") carries
the entire prompt. Use a single-line caption *above* the field if extra
guidance is needed — never inside the input.

**Why `String` binding, not `Int?`.** Simpler than threading `Int?`
through `materialize()`, the bucket helper, and telemetry. Continue is
gated on whether `Int(ageString)` parses to a value in 0…120; on tap, the
parsed Int is written to `draft.parentMotherAgeAtDeath` (still `Int?`
because the draft semantics already support "no answer"). Localization
note: with `.numberPad` and an `Int(_:)` initializer this is fine for
Latin numerals; if we later support Arabic-Indic / Devanagari input (the
device's locale-numeral setting), swap to `TextField(value:format:.number)`
with an `Int?` binding which delegates to `NumberFormatter`. Not blocking
for v1.

**Continue gate.** Disabled when `preferNotToSay` is off AND `alive ==
false` AND `Int(ageString)` doesn't parse to 0…120. Both gates together
(disabled-Continue + "Prefer not to say" toggle) — they answer different
questions per NN/g and the UK GDS Service Manual ("incomplete" vs
"declined"). Keep both.

**Telemetry:** `ParentLongevityBucket.bucket(for:)` continues to be called
only when an Int is parsed, before `onContinue()`. No telemetry shape
change.

### Phase 4 — Dot-screen legend + merge the orphan introduction

**Files:**
- `products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift`
  (`LifeGridFullView`, `LifeGridRemainingView`, `RecoveryPreviewView`,
  `BigNumberPenaltyView`)
- `products/life-clock-ios/Sources/Shared/LifeGridDotView.swift` (add a
  legend sub-view)
- `products/life-clock-ios/Sources/Features/Onboarding/OnboardingScreen.swift`
  (drop one enum case)

#### 4a. Merge `LifeGridFullView` into `LifeGridRemainingView` (lands as its own PR, before Phase 1)

Today the flow is:

```
… → lifeGridFull ("This is your life. Each dot is a week.")
  → lifeGridRemaining ("This is what's still ahead.")
  → bigNumberPenalty (red dots — first colored dots the user sees)
  → engineRevealAndDial
  → recoveryPreview ("N more years of …" — blue dots)
```

The `lifeGridFull` step is just an intro that says "dots = weeks" without
showing meaningful color state. Merge it into `lifeGridRemaining`,
single title, no auto-advance (revised — the originally-proposed two-beat
title with 2.5s auto-advance is unnecessary state-machine complexity for
one extra sentence, per the simplicity reviewer):

```swift
// LifeGridRemainingView (new copy)
title:    "This is what's still ahead."
bodyText: "Each dot is a week your habits get to shape."
```

Drop `case lifeGridFull` from `OnboardingScreen.swift`. Because raw values
are analytics contracts (file-header comment lines 7–11), add a
`deprecatedScreens` mapping so historical funnel data stays joinable:

```swift
// OnboardingScreen.swift (new)
extension OnboardingScreen {
    /// Old screens removed in later flow revisions. Funnel dashboards
    /// should join old `lifeGridFull` events to the merged screen.
    static let deprecatedScreens: [String: OnboardingScreen] = [
        "lifeGridFull": .lifeGridRemaining,
    ]
}
```

Mirror the mapping in the telemetry sink so a one-time analytics-version
event is emitted on first run after upgrade. Net screen count goes from
25 → 24.

**Sequencing:** ship this as its own PR *before* the Phase 1 structural
change. Two reasons: (a) isolates the analytics-contract change from the
shell rewrite — easier to revert if a dashboard breaks; (b) reduces
Phase 1's surface area to "structure only."

#### 4b. Progressive-disclosure legend on colored grids

Revised after deepen-plan: full legend on the first multi-color screen
only; lighter affordance on repeats. NN/g progressive-disclosure guidance
(refreshed 2023) — repeating the full legend on every screen trains users
to ignore it.

| Screen | Legend treatment |
|---|---|
| `lifeGridRemaining` (single color: green vs gray) | No legend block. Inline caption suffices: "Filled green = lived." |
| `bigNumberPenalty` (first multi-color screen) | Full `LifeGridDotLegend` row beneath the grid. |
| `recoveryPreview` | `info.circle` button beside the title — tap shows the legend in a popover. |

**Move the legend lookup onto `GridMode`** (architecture-strategist —
prevents grid + legend drift):

```swift
// LifeGridDotView.swift (extension on GridMode)
extension LifeGridDotView.GridMode {
    var legendItems: [(color: Color, label: String)] {
        switch self {
        case .full: return []
        case .remainingHighlighted: return [
            (.green, "Lived"),
            (.gray.opacity(0.5), "Still ahead"),
        ]
        case .bigNumberPenalty: return [
            (.green, "Lived"),
            (.red, "At risk"),
            (.gray.opacity(0.5), "Still ahead"),
        ]
        case .recoveryHighlighted: return [
            (.green, "Lived"),
            (.blue, "Recoverable"),
            (.gray.opacity(0.5), "Still ahead"),
        ]
        }
    }
}

struct LifeGridDotLegend: View {
    let mode: LifeGridDotView.GridMode
    var body: some View {
        HStack(spacing: 16) {
            ForEach(mode.legendItems, id: \.label) { item in
                HStack(spacing: 6) {
                    Circle().fill(item.color).frame(width: 8, height: 8)
                    Text(item.label).font(.caption2).foregroundStyle(.secondary)
                }
            }
        }
        .accessibilityElement(children: .combine)        // single VO swipe
    }
}
```

**Color-blind notes** (deepen-plan):

- WCAG 1.4.1 ("Use of Color," Level A) is already satisfied — the existing
  dot view encodes filled-vs-outlined for lived-vs-remaining
  ([LifeGridDotView.swift:115-149](products/life-clock-ios/Sources/Shared/LifeGridDotView.swift)).
  Color is redundant, not load-bearing.
- The default `Color.green` / `Color.red` pair fails deuteranopia /
  protanopia (~8% of men). Two cheap mitigations to consider during
  implementation: swap green → `.teal` or red → `.orange` for fill colors.
  Both test well on Coblis (Okabe-Ito 2008; WWDC 2022 "Crafting accessible
  experiences"). Not blocking but recommended.
- Verify 1.4.11 "Non-text Contrast" (3:1) on the 8pt legend swatches
  against the background — small graphical objects sit near the threshold.

### Phase 5 — Soft-skip on HealthKit screen

**File:** `products/life-clock-ios/Sources/Features/Onboarding/Screens/DataCollectionScreens.swift`
(`HealthKitAuthView`, line 825).

Pattern: primary filled "Connect Apple Health" CTA + low-emphasis
secondary "Not now" link beneath. **Not** equally weighted (Apple HIG +
Cal AI / MyFitnessPal precedent — the priming step should feel voluntary,
not symmetric). Forcing the system sheet by hiding the soft-exit drives
the worst outcome: a permanent "Don't Allow" that requires the user to dig
through Settings to reverse.

```swift
VStack(spacing: 12) {
    Button("Connect Apple Health") { /* existing connect flow */ }
        .buttonStyle(.borderedProminent)
        .accessibilityIdentifier("onboarding.healthKitAuth.connect")

    Button("Not now") {
        telemetry.value.choiceMade("healthKitAuth", key: "decision",
                                   valueBucket: "skipped")
        onContinue()                                // bypass system sheet
    }
    .buttonStyle(.plain)
    .foregroundStyle(.secondary)
    .font(.callout)
    .accessibilityIdentifier("onboarding.healthKitAuth.skip")
}
```

Caption beneath: *"You can connect Apple Health any time from Profile."*
This restores a v1 behavior dropped in v2 (see
[OnboardingView.swift:206](products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift)).

**Critical:** the skip path must NOT call `requestHealthAuthorization`. A
denied system prompt persists; a soft-skipped state lets us re-prompt later
on the relevant feature surface (a second-chance prompt in Profile or the
first time the user opens a feature that needs HealthKit data).

**Telemetry taxonomy** (per the deepen-plan event-naming research):
existing `healthKitAuth` screen now records one of `granted` / `denied` /
`skipped` (soft) / `deferred` (re-prompt path, future). Snake-case
`namespace_object_action` already matches the codebase's existing
`screenAppeared` / `screenAdvanced` / `choiceMade` shape — no contract
change beyond adding the new bucket value.

**App Review note.** Guideline 5.1.1 requires a clear
`NSHealthShareUsageDescription` and that prompts explain the use; rejection
patterns cluster on poor description strings, not on Skip-button parity.
Confirm the existing usage description string is current before submission.

## System-wide impact

### Interaction graph (Phase 1, the structural one)

- **Today:** `OnboardingCoordinator.body` → `NavigationStack(path:)` →
  per-screen `OnboardingScaffold` → renders own `OnboardingHeader` →
  reads `draft.lastDelta` (only updated on Continue).
- **After:** `OnboardingCoordinator.body` → `OnboardingShell` (single
  header instance) → body slot swaps based on `currentScreen` enum →
  scaffolds no longer render header → all bindings go through
  `draft.bind(_:engine:)` so per-input mutations update `lastDelta` →
  shell's mascot animates continuously.

### Error / failure propagation

- Engine recompute is rules-based and synchronous (see
  `ClockEngine.calculateBaseline` and `lifestyleAdjustmentYears`); no new
  failure modes.
- HealthKit Skip path: must NOT call `requestHealthAuthorization`. Verify
  that downstream code (`store.refreshFromHealthKit`) handles the
  unauthorized state — it already does (the v1 flow allowed skipping).

### State lifecycle risks

- Phase 1 changes the coordinator's path representation. Verify that the
  dial-confirm path-clear at `OnboardingCoordinator.swift:122`
  (`path = [.recoveryPreview]`) is preserved under the new model — i.e.,
  Confirm still makes the dial unreachable via back-nav. The custom
  back-chevron must check and disable on `recoveryPreview` and beyond.
- Phase 3 changes `ageAtDeath` to `Int?`. `materialize()` and the
  telemetry call site already handle nil paths correctly; verify the
  bucket helper is only called when a value exists.

### API surface parity

- Telemetry rawValue contract: dropping `case lifeGridFull` is a breaking
  change for downstream analytics. Coordinate with whoever owns the funnel
  dashboards (likely just the founder for now) before merging.
- `OnboardingScreen` is `CaseIterable` and the file-header comment notes
  that order matters for `next(after:)`. There is no actual `next(after:)`
  helper in the current code (advances are explicit per-screen) so
  re-ordering is safe — but confirm during implementation.

### Integration test scenarios

Cross-layer scenarios that unit tests with mocks won't catch:

1. **Header continuity under Reduce Motion.** Toggle Reduce Motion on,
   walk from `coldOpen` → `paywallPrimary`, assert the mascot view's
   identity is stable (one onAppear, no onDisappear) across the journey.
2. **Mascot reactivity through every input.** UI test: advance to
   `smoking` screen, tap each option in turn, assert the mascot's
   `accessibilityValue` (or a debug-only minutes-delta hook) changes
   without tapping Continue.
3. **HealthKit skip path.** Skip on `healthKitAuth`, finish onboarding,
   assert `store.healthAuthorizationKnown == false` and that the Profile
   screen shows the "Connect Apple Health" prompt.
4. **Stepper → numeric input migration.** UI test: select "Passed away",
   focus the new TextField, type "42", assert continue is enabled and
   `parentMotherAgeAtDeath == 42` after Continue. Also verify clamp
   behavior on overflow ("999" → 120).
5. **Dot legend visible on all four colored modes.** Snapshot tests on
   `LifeGridRemainingView`, `BigNumberPenaltyView`, `RecoveryPreviewView`,
   and the merged intro state — legend row present and labels match the
   lookup table.

## Acceptance criteria

### Functional

- [ ] Mascot + "Life Clock" wordmark do not animate in/out between any
      two adjacent onboarding screens (visually verified on simulator
      side-by-side).
- [ ] Mascot's clock hands move *during* slider drags, picker selections,
      and TextField edits — not just on Continue.
- [ ] `ReactiveSliderView` shows four labeled dials (Activity, Food, Sleep,
      Stress); the headline number and mascot react to all four.
- [ ] Family-mother / family-father screens use a numeric `TextField` with
      `.numberPad`; Continue is disabled until a value is entered or
      "Prefer not to say" is on.
- [ ] HealthKit screen has a visible "Skip for now" affordance; tapping
      it advances to the paywall without calling
      `requestHealthAuthorization`.
- [ ] Every screen that renders `LifeGridDotView` with a colored mode also
      renders a legend row directly beneath it.
- [ ] `lifeGridFull` is removed; `lifeGridRemaining` opens with the
      "Each dot is a week" beat then auto-advances copy to "This is what's
      still ahead" after ~2.5s.

### Non-functional

- [ ] No new screen takes >16ms to first render at 60fps on iPhone 13
      (Instruments → SwiftUI template; test on the multi-dial demo
      specifically since it has four reactive sliders).
- [ ] Reduce Motion: shell transitions collapse to identity; mascot
      animation snaps; legend still renders.
- [ ] VoiceOver: each new dial gets a unique label/value/identifier; the
      legend row is announced as a single accessibility element with the
      lookup-table labels joined.

### Quality gates

- [ ] All existing onboarding UI tests pass after `OnboardingScreen.lifeGridFull`
      is dropped (search for and update any references).
- [ ] New UI tests cover the five integration scenarios above.
- [ ] `xcodebuild test -scheme LifeClock -destination 'platform=iOS Simulator,name=iPhone 16'`
      green.

## Sequencing & resource estimate

Revised after deepen-plan: split Phase 4a out as its own PR (lands first)
to isolate the analytics-contract change from the structural rewrite.

1. [x] **Phase 4a (merge `lifeGridFull` + `deprecatedScreens` mapping)** — own
   PR, ~1 hr. Lands first; analytics dashboards verified before Phase 1.
2. **Phase 1 (header-above-stack spike → fallback shell + shell-level
   reactor + debounced recompute)** — ~½ day. Highest-risk change; touches
   the coordinator and every scaffold call site.
3. **Phase 4b (legend on GridMode + progressive-disclosure rendering)** —
   ~45 min.
4. **Phase 2 (three-dial demo)** — ~45 min (down from four).
5. **Phase 3 (numeric input + String binding + parse gate)** — ~45 min.
6. **Phase 5 (soft-skip on HealthKit)** — ~15 min.

Total: ~1 day of implementation + UI test work, split across 2 PRs.

## Alternatives considered

- **Keep `NavigationStack`, render the header in `.toolbar(.principal)`.**
  Rejected: principal slot height-capped (~44pt large-title, ~96pt with
  large-title); 120pt mascot won't fit. Apple HIG explicitly scopes
  principal to titles / segmented controls.
- **Header in a `.safeAreaInset(edge: .top)` at the NavigationStack root.**
  Closer to working, but documented identity flakiness with `@Observable`
  ancestor state during fast transitions (HwS / Apple Forums 2024,
  partially fixed iOS 18 but still not guaranteed). Pass on it.
- **(NEW — preferred) Header in a parent VStack *above* the
  `NavigationStack`.** Header is never inside the stack's view hierarchy,
  so SwiftUI assigns it stable identity for the whole flow. Preserves
  swipe-back on non-terminal screens and avoids the custom-shell rewrite.
  Spike this first per architecture-strategist; only fall back to the
  custom `OnboardingShell` (ZStack + `.id` + `.transition`) if the spike
  shows the header re-rendering anyway.
- **Drop `NavigationStack` entirely → custom `OnboardingShell` (ZStack +
  `.id(currentScreen)` + asymmetric slide+fade transition).** Cleanest
  identity story and matches the forced-linear flow shape, but biggest
  blast radius. Reserve as the fallback if the parent-VStack spike fails.
- **Three sliders instead of four** — accepted (was rejected in v1 of this
  plan). Multi-dial onboarding research and the simplicity reviewer agree:
  four sits at working-memory ceiling and crowds Dynamic Type. Stress is
  collected later in honest single-question screens.

## Risks

- **Funnel-analytics break** from dropping `lifeGridFull`. Low blast
  radius today (analytics dashboards aren't widely consumed) but document
  in the PR description.
- **Animation jank on older devices** from the new per-input recompute
  pipeline. Mitigated by the 120ms debounce; if it still chokes on iPhone
  SE 2nd gen, increase to 240ms or move recompute off-main via `Task`.
- **Custom back chevron loses NavigationStack swipe gesture.** Acceptable
  for a forced linear flow; document in CLAUDE_HANDOFF.md.

## Sources & references

### Origin

- **Brainstorm document:**
  [docs/brainstorms/2026-05-01-life-clock-reveal-onboarding-anchor-dial-brainstorm.md](docs/brainstorms/2026-05-01-life-clock-reveal-onboarding-anchor-dial-brainstorm.md)
  — this plan does not change any of the brainstorm's structural
  decisions (25-screen flow, anchor-dial semantics, reveal-driven order,
  free vs Pro split). It only polishes five UX rough edges discovered
  after the v2 flow shipped.

### Internal references

- Coordinator + screen registry:
  [OnboardingCoordinator.swift:21-181](products/life-clock-ios/Sources/Features/Onboarding/OnboardingCoordinator.swift),
  [OnboardingScreen.swift:11-62](products/life-clock-ios/Sources/Features/Onboarding/OnboardingScreen.swift)
- Persistent header (today): [LeadInScreens.swift:21-56](products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift)
- Scaffold renders header per-screen:
  [DataCollectionScreens.swift:55-95](products/life-clock-ios/Sources/Features/Onboarding/Screens/DataCollectionScreens.swift)
- Stepper to replace:
  [DataCollectionScreens.swift:676](products/life-clock-ios/Sources/Features/Onboarding/Screens/DataCollectionScreens.swift)
- HealthKit screen (no skip today):
  [DataCollectionScreens.swift:825-864](products/life-clock-ios/Sources/Features/Onboarding/Screens/DataCollectionScreens.swift)
- Single-dial demo:
  [LeadInScreens.swift:204-251](products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift)
- Dot grid + modes:
  [LifeGridDotView.swift:28-194](products/life-clock-ios/Sources/Shared/LifeGridDotView.swift)
- Engine adjustment factors that justify the four demo dials:
  [ClockEngine.swift:55-141](products/life-clock-ios/Sources/Engines/ClockEngine.swift)
- Draft + recompute path:
  [OnboardingDraft.swift:83-124](products/life-clock-ios/Sources/Features/Onboarding/OnboardingDraft.swift)

### Memory references

- `feedback_xcode_build_loop.md` — iterate to a green build via
  `xcodebuild` headless rather than waiting for paste-back; applies to
  every phase here.
- `feedback_life_clock_lighting_convention.md` — opacity 0.22, offset
  ratio (0.35, 0.85), radius ratio 0.55× of reference size. Applies if
  the persistent mascot needs a subtle background lighting pass during
  this work; do not reinvent the convention.

### Related work

- v2 onboarding plan:
  [docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md](docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md)
- Mascot animation primitive:
  [docs/plans/2026-05-02-feat-life-clock-mascot-animated-primitive-plan.md](docs/plans/2026-05-02-feat-life-clock-mascot-animated-primitive-plan.md)

### External research (deepen-plan)

- Apple HIG — Steppers / Sliders / Color / Authorizing access to health data /
  Designing for privacy (2024–2025 revisions).
- Apple — [Migrating from ObservableObject to @Observable](https://developer.apple.com/documentation/swiftui/migrating-from-the-observable-object-protocol-to-the-observable-macro).
- WCAG 2.2 — 1.4.1 Use of Color, 1.4.11 Non-text Contrast.
- NN/g — "Sliders: Definition and Best Practices"; "Placeholders in Form
  Fields Are Harmful" (Sherwin); "Stepper Input Fields"; "Progressive
  Disclosure" (Nielsen).
- Tversky & Kahneman 1974 — anchoring; Baymard 2022 form-design
  replication.
- Donny Wals — "Debouncing in Swift with async/await" (2024).
- Majid Jabrayilov — "Mastering NavigationStack in SwiftUI" series.
- Paul Hudson — Hacking with Swift articles on `safeAreaInset` identity
  behavior.
- Okabe & Ito 2008 — Color Universal Design palette; WWDC 2022 "Crafting
  accessible experiences."
- Mobbin — Cal AI iOS onboarding flow; PageFlows — MyFitnessPal onboarding;
  Growth.Design teardowns.
- RevenueCat blog — paywall placement / paywall tests (closest published
  analog for soft-exit conversion data).
- Appcues — "Mobile Permission Priming"; Respectlytics — "Event Naming
  Best Practices."
