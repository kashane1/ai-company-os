# Sandbox Validation Runbook — Life Clock

> **Status:** Operator runbook. Click-by-click instructions for validating the 5 subscription-lifecycle scenarios that can't be tested against the local `Products.storekit` config or the iOS 26 simulator (Apple's `SKTestSession.buyProduct` is broken on iOS 26 sim — tracked in [flutter/flutter#184678](https://github.com/flutter/flutter/issues/184678) — so the existing `SubscriptionStoreTests` skip on every simulator we have).
>
> Sister doc: [`subscription-lifecycle-spec.md`](subscription-lifecycle-spec.md) (the state matrix this runbook validates). Sister: [`submission-runbook.md`](submission-runbook.md) (the broader submission flight plan; this runbook is one of its pre-flight steps).

## Why this exists

Q1–Q5 in [`subscription-lifecycle-spec.md`](subscription-lifecycle-spec.md) § Outstanding require real-device + sandbox Apple ID. The Apple sandbox infrastructure is where:

- Synthetic-month subscription cycling lives (sandbox subs renew every 5 min instead of monthly)
- Real `Transaction.updates` async sequence delivers from Apple's servers
- ASC-side refund triggers exist
- Family sharing configures

None of these exist on the local `.storekit` config — that's a mock with no state machine.

## Pre-flight setup (one-time, ~15 min)

You only do this once per environment. Re-use across all 5 Qs.

### 1. App Store Connect — sandbox tester + IAP products configured

- [ ] **ASC → Users and Access → Sandbox → Testers** — create one sandbox tester with a unique email (use a `+sandbox` alias, e.g. `kashane+sandbox@…`). Apple won't send mail to it — the address is just an identifier.
- [ ] **Disable 2FA** on the sandbox tester (sandbox auth doesn't support 2FA reliably).
- [ ] **ASC → My Apps → Life Clock → Monetization → In-App Purchases** — confirm all three products exist with the right IDs:
  - `com.lifeclock.pro.monthly` at $7.99
  - `com.lifeclock.pro.annual` at $49.99
  - `com.lifeclock.pro.lifetime` at $129.99
- [ ] Status of each = **"Ready to Submit"** or better (sandbox uses any non-rejected status).

If any of those rows fail, the cause is documented in [`ASC_CHECKLIST.md`](ASC_CHECKLIST.md) Phase 5.

### 2. Build configuration — Synced StoreKit, not local

- [ ] Open Xcode → `LifeClock.xcodeproj` (regenerate via `xcodegen generate` if absent).
- [ ] **Product → Scheme → Edit Scheme** → **Run** → **Options** tab.
- [ ] **StoreKit Configuration:** set to **None** (this disables the local `Products.storekit` mock; the app hits real sandbox).
- [ ] **Build Configuration:** Debug (sandbox works in Debug; release-signed sandbox is also fine).
- [ ] Save scheme.

⚠ When you're done sandbox-testing, revert this to `Products.storekit` so dev simulator builds keep working without a real Apple ID prompt.

### 3. Real device — signed in as the sandbox tester

- [ ] **Settings → App Store → Sandbox Account** (iOS 12+) — sign in with the sandbox tester credentials. This is *separate* from your regular Apple ID; the device stays signed in to your normal account for everything else, and sandbox kicks in only when an app makes IAP requests.
- [ ] Plug the device into the Mac running Xcode.
- [ ] Xcode top bar → select the real device as the destination.

### 4. Install + launch fresh

- [ ] **Product → Run** to install + launch the app on the device.
- [ ] Walk the onboarding flow once (or skip via JUMP_TO if you have a debug fixture).
- [ ] You should land on Today in a Free state — confirm via Profile → Subscription shows the "Upgrade to Pro" pitch row (with the tone-aware subline shipped in Sprint A2).

You're ready to run the Qs.

---

## The 5 validation passes

Run in this order — Q1 → Q4 → Q2 → Q3 → Q5 — because setup transitions stack cheaply this way.

### Q1 — Cancel-in-grace (most common user scenario, ~5 min)

**What you're validating:** users who cancel mid-period keep Pro until expiry. If this breaks, every user who cancels feels cheated.

**Steps:**

1. **Buy annual Pro** in the app: Profile → Upgrade to Pro → tap "Continue with annual" → Apple's sandbox sheet → confirm purchase.
2. Verify: Profile Subscription section flips to show "Active" + the **"Manage subscription"** row (the Sprint A2 P1 fix).
3. Verify: Today's Plan-Editor chip is unlocked, History fog is gone, Future tab's What-If slider thumbs are full-opacity (not `.opacity(0.5)` per Sprint C1 lock-glyph rules).
4. **Cancel the sub:** tap "Manage subscription" → iOS-native sheet opens → tap Cancel → confirm.
5. Return to the app. Foreground the app (cmd-Tab on device-attached Xcode, or background → re-open).
6. **EXPECTED:** within ~2 seconds, Profile still shows "Active" + Manage subscription row. Pro UI everywhere intact.

**Pass criteria:**
- ✅ `subscriptions.isPro == true` (Pro UI intact)
- ✅ "Manage subscription" row still appears
- ✅ No "Cancelled" badge anywhere (Apple owns that surface — confirmed by [`subscription-lifecycle-spec.md`](subscription-lifecycle-spec.md) § What the app must NEVER do)

**Fail modes to flag:**
- ❌ App immediately demotes to Free → bug in `SubscriptionStore.refreshEntitlements` honoring `revocationDate == nil`
- ❌ App shows a "Cancelled" badge → violation of subscription-lifecycle-spec; remove the badge
- ❌ Manage subscription row disappears → wrong condition on the `.manageSubscriptionsSheet` modifier

**Screenshot to capture:** Profile Subscription section in active-and-cancelled-but-still-in-grace state. File as `sandbox/2026-MM-DD-Q1-cancel-in-grace.png`.

### Q4 — Restore from fresh install (App Review § 3.1.1 mandatory, ~5 min)

**What you're validating:** Apple reviewers literally do this. Delete app → reinstall → tap Restore → Pro returns same session, no app restart.

**Steps:**

1. From Q1 you still have an active Pro sub (cancelled but in grace). Even better — Pro persists across the test.
2. **Delete the app from the device:** long-press → Remove App → Delete App.
3. **Reinstall:** Xcode → Product → Run again, OR install from TestFlight if you're testing the TestFlight build.
4. Walk through onboarding to land on Today as Free (Free state expected, no entitlement yet).
5. Verify: Profile → Subscription section shows the "Upgrade to Pro" pitch row (Sprint A2).
6. **Tap "Restore purchases"** in Profile.
7. **EXPECTED:** within ~2 seconds, the Profile Subscription section flips to "Active" + Manage subscription row. No app restart required.

**Pass criteria:**
- ✅ Free → Pro flip within same session
- ✅ Restore alert shows "Pro restored" (the three-state outcome from Sprint commits — `restored / nothingToRestore / failed`)
- ✅ All Pro UI (Today Plan-Editor unlock, History fog lifted, Future What-If unlocked) refreshes without restart

**Fail modes:**
- ❌ "Nothing to restore" alert when there's an active sub → either you're not signed into the same sandbox Apple ID (re-check Settings → Sandbox Account) or `SubscriptionStore.restore()` isn't iterating `Transaction.currentEntitlements`
- ❌ App needs a restart to flip → `PaywallSheet` or `ProfileView` isn't observing `subscriptions.isPro` via `@Observable`
- ❌ Restore button stays in `restoring` state → loader gate isn't released; check `restorePurchases()` `defer` block

**Screenshot:** the moment after Restore where Pro UI returns. File as `sandbox/2026-MM-DD-Q4-restore-fresh-install.png`.

### Q2 — Post-expiry demote (data-integrity gate, ~8 min counting wait)

**What you're validating:** when a sub expires, Pro UI hides cleanly AND existing overrides remain visible (read-only). The latter is a trust-critical promise from [`override-contract.md`](override-contract.md) § Grace period.

**Steps:**

1. With active Pro from prior tests, **apply an override** to set up the data-integrity check:
   - History → tap any past day → DayDetailView → tap a HK-derived row → edit value to something different from the HK value → save.
   - Verify the "Adjusted" chip appears on that row.
2. **Wait for the sandbox sub to actually expire.** Sandbox cycles are short — 5 min for the synthetic "month," 1 hour for the synthetic "year." If you bought annual in Q1, this is a 1-hour wait. If you can re-buy monthly here, it's 5 min.
3. **Re-buy monthly** if needed: Profile → Upgrade → pick Monthly → confirm. (Tip: sandbox doesn't actually charge.)
4. **Wait ~5 minutes** for monthly synthetic expiry. Make tea.
5. Foreground the app. Pull the History tab to refresh.
6. **EXPECTED:** Pro UI hides cleanly. History fog returns over older rows. Plan-Editor chip locks. Future What-If thumbs dim to `.opacity(0.5)`. **But the overridden day still shows the overridden value with the "Adjusted" chip.**

**Pass criteria:**
- ✅ `subscriptions.isPro` flipped to `false`
- ✅ Pro-gated UI re-locks (fog, chip lock, slider opacity)
- ✅ Overrides are still visible — `OverrideAwareSnapshot.proAdjusted` keeps returning the corrected value for the read path
- ✅ Attempting to add a NEW override throws `.notEntitled` (try editing another row → Pro paywall appears)

**Fail modes (high-impact):**
- ❌ Overrides disappear → **data-integrity regression**, violates `override-contract.md`. The engine's read path is incorrectly Pro-gating. **High-pain bug, file blocker.**
- ❌ Pro UI stays unlocked → `Transaction.updates` not being consumed. Check `SubscriptionStore.observeTransactionUpdates()` Task lifecycle.
- ❌ App crashes on the demote frame → SwiftData race; mostly `@MainActor` not enforced on the demote handler.

**Screenshot:** History day-detail showing the overridden row with "Adjusted" chip + fog over older rows. File as `sandbox/2026-MM-DD-Q2-post-expiry-overrides-intact.png`.

### Q3 — Refund (high-impact-when-broken, ~5 min)

**What you're validating:** when a user gets refunded, the app demotes cleanly. Apple sends a revocation via `Transaction.updates`; the app must respond on next foreground.

**Steps:**

1. From Q2 you have an active monthly sub (or buy one fresh).
2. **In ASC dashboard:** Sales and Trends → Payments and Financial Reports → find the sandbox transaction → click → **Refund**. Sandbox refunds are instant.
3. Return to the device. Foreground the app.
4. **EXPECTED:** within a few seconds (StoreKit 2 may take up to 30 sec to propagate the revocation), Pro UI demotes — same behavior as Q2.

**Pass criteria:**
- Same UI behavior as Q2 (demote cleanly, overrides intact)
- The refund happens via revocation, not expiry — implementation difference: `Transaction.updates` async sequence delivers a revoked transaction
- No "you were refunded" banner (App owns nothing here; the email from Apple is the only acknowledgment)

**Fail modes:**
- ❌ App stays Pro indefinitely → `Transaction.updates` Task not running; check `SubscriptionStore.init()` for the listener task setup
- ❌ Crash on revocation → guard the revocation handler; check `@MainActor` annotations

**Screenshot:** same Profile-demoted state as Q2 (this is mostly a back-channel test).

### Q5 — Family sharing (lowest priority, ~10 min, optional post-launch)

**What you're validating:** if you ever enable family sharing on the Pro annual product, family members get access. StoreKit 2 handles this transparently — there's not much app-side logic to test.

**Setup is heaviest here:**

1. ASC → My Apps → Life Clock → Monetization → In-App Purchases → `com.lifeclock.pro.annual` → **Family Sharing: Enabled** (must be set BEFORE the family member tries to access).
2. Create a second sandbox tester (the "family member").
3. Configure a sandbox family group with both testers — this is finicky; Apple's docs at [Test in-app purchases](https://developer.apple.com/documentation/storekit/in-app_purchase/testing_in-app_purchases_with_sandbox/) are the source.
4. Buy annual on tester #1's device.
5. Sign tester #2's device into sandbox.
6. Family-share the sub via Settings → Apple ID → Family Sharing.
7. **EXPECTED:** Tester #2's app reads as Pro.

**Pass criteria:** Tester #2's `subscriptions.isPro == true` without buying.

**Recommendation:** SKIP for v1 submission. Family-sharing is a Pro-feature add-on, not a launch blocker. App Review doesn't test it. Validate post-launch when you have a real family member to test with.

---

## What to do after the sandbox session

1. **All passed** → check off the 5 Qs in [`subscription-lifecycle-spec.md`](subscription-lifecycle-spec.md) § Validation. Update [`PHASE_STATUS.md`](PHASE_STATUS.md) to mark submission-readiness flag from yellow → green.
2. **Q1/Q4/Q2 passed, Q3/Q5 deferred** → submission-readiness goes yellow but unblocked. Note carryover in `PHASE_STATUS.md`.
3. **Any high-impact failure** → file a polish-tier prompt (or escalate to vision-question if the bug needs an architectural fix). Tag with `subscription-lifecycle-regression`.
4. **Revert the scheme** → Xcode → Edit Scheme → Run → StoreKit Configuration back to `Products.storekit`. Dev sim builds break without it.

## When Apple fixes the iOS 26 sim SKTestSession bug

The codebase's existing `SubscriptionStoreTests.skipIfStoreKitTestSessionBroken()` will start passing instead of skipping. Track [flutter/flutter#184678](https://github.com/flutter/flutter/issues/184678) — Apple usually fixes these in minor iOS releases. Once fixed:

- The existing test suite covers Q3 (refund-via-revocation) automatically
- Add SKTestSession-based tests for Q1 (cancel-in-grace via `setCancellationDate`) and Q2 (post-expiry via `expireSubscription`)
- Q4 partial coverage (entitlement-read on a fresh `SubscriptionStore` instance — already covered)
- Q5 stays manual; `SKTestSession` doesn't simulate family sharing

## Cross-references

- State matrix: [`subscription-lifecycle-spec.md`](subscription-lifecycle-spec.md)
- Override read-path during demote: [`override-contract.md`](override-contract.md) § Grace period
- App-side gates: [`Tests/EntitlementGatedWritesTests.swift`](../../../products/life-clock-ios/Tests/EntitlementGatedWritesTests.swift)
- Existing SKTestSession tests: [`Tests/SubscriptionStoreTests.swift`](../../../products/life-clock-ios/Tests/SubscriptionStoreTests.swift) (skipping on iOS 26+)
- App Store Connect setup: [`ASC_CHECKLIST.md`](ASC_CHECKLIST.md) Phase 5
- Submission pre-flight: [`submission-runbook.md`](submission-runbook.md) § Pre-flight
