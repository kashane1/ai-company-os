# Polish Session — life-clock — 2026-05-16 — paywall-shared-core-extraction

## Mode

`fix-list` — backlog prompt **PV-P2** from
`docs/products/life-clock/pro-value-backlog-2026-05-15-standard.md`
§ "PaywallPrimaryView ↔ PaywallSheet shared-core extraction (the in-code
TODO)". Resumed from a prior session that crashed mid-refactor leaving
uncommitted partial work (a drafted `PaywallProductsView.swift` + edited
`PaywallPrimaryView.swift` / `PaywallSheet.swift`) that did not compile.
This session finished the partial work — it did not restart it.

Strict no-behavior-change contract (App-Review-sensitive, Apple
3.1.2(c) equal-prominence): pricing strings, per-month-equivalent,
Restore behavior, auto-renew fineprint, and the 5-perk block must be
byte-identical before/after on BOTH paywall surfaces.

## Iterations

- [12:30] `<refactor-sha>` — refactor(life-clock): extract shared PaywallProductsView core composed by both paywall surfaces — Polish — Paywall (onboarding + re-engagement)
- [12:35] `<fix-sha>` — fix(life-clock): @MainActor-isolate runReengagementRestore so SubscriptionStore reads compile — Polish — Paywall core
- [12:55] `<chore-sha>` — chore(life-clock): PV-P2 session log — Polish — n/a

(The refactor + actor-isolation fix are split into two commits per the
boundary instruction: `refactor(...)` for the extraction, `fix(...)`
for the actor-isolation correction.)

## Actor-isolation root cause + fix

`PaywallProductsView.runReengagementRestore(_:)` was drafted as a plain
`static func ... async` (nonisolated). It reads
`subscriptions.lastError` and `subscriptions.isPro` after the restore.
`SubscriptionStore` is `@MainActor`-isolated (declared
`@MainActor @Observable final class` at
`Sources/Services/SubscriptionStore.swift:11`), so both `lastError`
(`private(set) var`, line 17) and `isPro` (computed, line 21) are
MainActor-isolated. The Swift 6 / strict-concurrency compiler rejected
the read from the nonisolated `static func`:

```
PaywallProductsView.swift:67:65: main actor-isolated property 'isPro' can not be referenced from a nonisolated autoclosure
PaywallProductsView.swift:67:30: main actor-isolated property 'lastError' cannot be accessed from outside of the actor
```

(The "autoclosure" framing is the `&&` short-circuit operand on
line 67, not an `assert`/`#Preview`.)

**Fix:** annotate `runReengagementRestore` `@MainActor`. Both call
sites already run on the main actor — `PaywallSheet.runRestore()` is a
method on a SwiftUI `View` (MainActor) and `PaywallPrimaryView` never
calls it (it uses its own inline `refreshEntitlements()` path,
unchanged). Adding the annotation observes the isolation the callers
already satisfy; it changes no runtime behavior. After the fix the
headless build was fully green with no further errors.

## Golden-lock verification (no-behavior-change contract)

Verified by **exhaustive source diff** of `git diff HEAD` on both
surfaces, comment-stripped, against the extracted core (the contract's
golden-lock standard for string identity — stronger than a pixel diff
for verifying *string* byte-identity; see "Outstanding" for the
runtime-recapture caveat):

- **PaywallSheet (`.reengagement`)**: `productList` / `productRow` /
  `savingsBadge` / `monthlyEquivalent` / `productSlug` / `periodLabel`
  / `proBullet` were *removed* from `PaywallSheet` and moved
  character-for-character into `PaywallProductListView` /
  `PaywallPerksView` with `surface: .reengagement`. Same strings
  (`"Save ~48%"`, `"Best value"`, `"Auto-renews yearly/monthly"`,
  `"One-time purchase"`, `"… / month equivalent"`), same fonts, same
  `paywall.product.<slug>.savings` ids, same `selectedProductID`
  binding, same `.animation(...)`. The lone nuance: original
  `proBullet` had no `.fixedSize`; shared `PaywallPerksView` applies
  `.fixedSize(horizontal: false, vertical: false)` for `.reengagement`
  — a documented SwiftUI no-op (both axes flexible == default), so
  rendering is byte-identical. The re-engagement sheet retains NO
  nested `paywall.perks` element (`OnboardingPerksA11y(active:false)`),
  matching its pre-extraction AX tree exactly.
- **PaywallSheet restore**: old `clearLastError() → restore() →
  (lastError==nil && !isPro)` == `runReengagementRestore`'s body and
  return value exactly. Only the `restoring = false` reset moved
  *after* the empty-detection read instead of before; neither
  `lastError` nor `isPro` depends on `restoring`, so no observable
  effect. Auto-renew fineprint string + Terms/Privacy links untouched.
- **PaywallPrimaryView (`.onboarding`)**: `selectedTier: Tier = .annual`
  → `selectedProductID: String? = PaywallProductID.annual.rawValue`
  (same default tier). The old `Tier` enum's `productID` mapping is
  preserved verbatim inside `PaywallProductListView`. `tierToggle()` /
  `tierRow` / `priceString` / `perMonthEquivalent` /
  `paywallTierAccessibilityID` moved verbatim — identical
  `"$49.99 / yr"` / `"$7.99 / mo"` / `"$129.99"` /
  `"≈ $4.17 / mo equivalent"` fallbacks, identical
  `paywall.tier.annual/monthly/lifetime` ids. `proPerks` (combined
  `paywall.perks`, `.fixedSize(...vertical:true)`) →
  `PaywallPerksView(surface:.onboarding)` which sets `vertical:true`
  and `OnboardingPerksA11y(active:true)` → identical AX tree + wrap.
  `purchase()` resolves the same product
  (`products.first{ $0.id == selectedProductID }` ≡ old
  `product(for: selectedTier)`) and reports the same telemetry
  productID. Personalized headline/body, soft-skip, always-visible
  auto-renew line, Continue, and Restore stay in the onboarding shell,
  unchanged.

**Verdict: byte-identical on both surfaces (static golden-lock PASS).**

### SubscriptionStore re-injection

Both shells already own the `@Environment(SubscriptionStore.self)`
boundary; the extracted views read the store via their own
`@Environment` and inherit it through whichever shell composes them
(`PaywallProductListView` declares
`@Environment(SubscriptionStore.self) private var subscriptions`). No
new sheet/cover boundary was introduced by the extraction —
`PaywallSheet` is presented by its existing call sites which already
re-inject per `feedback_observable_environment_sheets.md` (commit
`5b0b397` precedent). No env-missing crash is possible by
construction; the refactor adds no presentation boundary.

### A11y identifiers preserved

`paywall.tier.annual/monthly/lifetime`, `paywall.restore`,
`paywall.close`, `paywall.perks` (onboarding only, combined),
`paywall.product.<slug>.savings`, `paywall.screen`,
`onboarding.paywallPrimary` — all preserved on their original
surfaces. The existing paywall UITests
(`UITests/LifeClockUITests.swift` `testOnboardingV2FlowReachesPaywall`
asserting `paywall.tier.annual` + `paywall.perks` + perk titles, and
`testPaywallCloseIsAgentDriveable` asserting `paywall.close` on the
`LIFECLOCK_FORCE_PAYWALL=1` re-engagement path) are **unmodified**
(no git change under `UITests/`) and remain satisfiable — every
identifier and label they assert is preserved verbatim by the
extraction.

## Build status

`xcodegen generate` → `LifeClock.xcodeproj` regenerated;
`PaywallProductsView.swift` auto-globbed in (4 pbxproj references
confirmed). Headless `xcodebuild build -scheme LifeClock` to
**iPhone 17 Pro Max** sim
(`942B6264-62E2-4663-8230-80E9133C824E`, iOS 26.3):
**`** BUILD SUCCEEDED **`** with the actor-isolation fix applied. No
remaining Swift errors after the two reported ones were cleared.

## Regressions caught

None — pure structural move, byte-identical source diff on both
surfaces. No screens other than the two paywall surfaces are touched.

## A11y identifiers added

None (PV-P2 is a refactor; all existing ids preserved, none added).

## Vision updates

None.

## Asks

### Resolved this session

- (Implicit) "Force one merged rendering vs. per-surface variant behind
  a `Surface` enum?" → the drafted approach (per-surface variant) is
  the only one that satisfies the byte-identical contract; a merged
  rendering would change strings/ids on one surface. Kept the drafted
  design. No operator input required — the contract dictates the
  answer.

### Outstanding (cycle-end batch)

1. **Live runtime re-verification was environmentally blocked — NOT
   performed.** The contract requested a final computer-use checkpoint
   (both entry paths visually verified, equal-prominence pricing). This
   could not run this session:
   - `xcrun simctl launch` returns
     `The request was denied by service delegate (SBMainWorkspace)`
     for **every** device (the known-good UDID, a freshly-booted
     shutdown device, both runtimes) and even for a plain no-env
     launch. This is a host-level CoreSimulator/launchd condition,
     **not** caused by PV-P2 (the build is green; the denial is
     identical with zero PV-P2 env vars).
   - The computer-use fallback is also blocked: the Mac is at the
     macOS login/lock window (`com.apple.loginwindow` frontmost), so
     the Simulator window is not visible/interactable and the screen
     cannot be unlocked by an agent.

   **Options:**
   a. Operator unlocks the Mac + resolves the simctl SBMainWorkspace
      denial (often: quit Simulator.app, `xcrun simctl shutdown all`,
      `killall -9 com.apple.CoreSimulator.CoreSimulatorService`,
      reboot a device), then re-runs the two paywall UITests
      (`testOnboardingV2FlowReachesPaywall`,
      `testPaywallCloseIsAgentDriveable`) + a manual both-path
      visual pass. (Recommended — closes the App-Review checkpoint.)
   b. Accept the static golden-lock proof as sufficient for the
      no-behavior-change contract (source diff proves *string*
      byte-identity more conclusively than a pixel diff; the build is
      green; UITests are unmodified and satisfiable by construction)
      and defer the live visual pass to the next session that has a
      working Simulator + unlocked Mac.
   c. Re-run only the headless paywall UITests (no visual pass) once
      the Simulator service is restored — partial closure of the
      checkpoint.

2. **Pre-existing unrelated test breakage (informational, NOT
   introduced by PV-P2):**
   `Tests/LifeClockLaunchConfigurationTests.swift:43:35: error: missing
   argument for parameter 'seedBadDayYesterday' in call`. The `Tests`
   unit target is untouched by this session (no git change under
   `Tests/`); this is a stale launch-config test signature unrelated
   to the paywall. It blocks `xcodebuild test` (the scheme builds the
   unit target before UITests) but is out of PV-P2's edit boundary
   (paywall files only). Flagging for a separate fix.

## Next pass

- Run the live both-path visual + UITest verification once the
  Simulator service + Mac lock are resolved (Outstanding #1).
- Separately fix the unrelated `LifeClockLaunchConfigurationTests`
  `seedBadDayYesterday` signature drift so `xcodebuild test` is green
  again (Outstanding #2 — out of PV-P2 scope).
