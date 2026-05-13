# Subscription Lifecycle Spec — Life Clock

> **Status:** Canonical product policy. Codifies the state matrix the app must handle for App Store submission readiness. The shipped purchase path is solid; this spec documents the *other* states (cancel-in-grace, post-expiry demote, refund, family sharing, restore) so future work doesn't regress and reviewers don't get surprises. Originated from `polish-2026-05-10-subscription-lifecycle-states.md` § Outstanding asks (Q1–Q5).

## One-line rule

**Entitlement is a function of `Transaction.currentEntitlements` — never of a cached flag.** Every Pro-gated feature consults `SubscriptionStore.isPro`; that value reflects the canonical StoreKit 2 entitlement state and updates in response to system-level subscription changes (cancel, refund, family sharing, expiry) without the app having to re-implement subscription logic.

## The state matrix (binding)

| State | StoreKit 2 signal | Expected app behavior | Test path |
|---|---|---|---|
| **Active Pro** | `Transaction.currentEntitlements` returns a verified transaction with `revocationDate == nil` and expiry in the future | All Pro gates open (`isPro == true`); Profile shows "Active" + Manage subscription row | StoreKit-config simulator with `LIFECLOCK_SIMULATOR_PRO_DISABLED` unset (default in DEBUG) |
| **Free** | `currentEntitlements` empty | All Pro gates closed; Profile shows "Upgrade to Pro" + Restore row; paywall offers reachable | `LIFECLOCK_SIMULATOR_PRO_DISABLED=1` |
| **Cancel-in-grace** | User cancelled in iOS Settings mid-period; transaction still in `currentEntitlements` with future expiry | Pro UI **stays intact until expiry**. `SubscriptionStore.refreshEntitlements` returns `isPro == true` for the remaining period. No "you cancelled" badge — Apple owns that surface in Settings. | Sandbox account; cancel via Settings → Apple ID → Subscriptions; relaunch within the synthetic period |
| **Post-expiry demoted** | `currentEntitlements` no longer returns the prior transaction | Pro UI hides cleanly; History fog returns over previously-revealed rows; Plan Editor edit chip routes to paywall; existing overrides remain visible (read-only); `OverrideSheet.notEntitled` defensive path fires when user attempts new writes. **No data loss** — the override store is durable across entitlement transitions. | Sandbox account or `LIFECLOCK_SIMULATOR_PRO_DISABLED=1` after a prior Pro purchase |
| **Refunded** | StoreKit 2 surfaces a revocation via `Transaction.updates` async sequence | App demotes on the same frame the revocation arrives. Same UI behavior as post-expiry. Existing overrides remain visible read-only — refund is a revocation of *new* writes, not of historical data the user already saw. | Real-device sandbox + App Store Connect Refund |
| **Restored (fresh install)** | First call to `refreshEntitlements` after fresh install surfaces the prior transaction | Pro state restored within the app session — no app restart required. PaywallSheet's `.onChange(of: subscriptions.isPro)` auto-dismisses if user happened to open the paywall mid-restore. | Fresh install on the same Apple ID; tap Profile → Restore purchases or Paywall → Restore |
| **Family sharing** | Family-shared subscription surfaces as a normal verified transaction in `currentEntitlements` | Treated as Active Pro. No special UI affordance — the sharing is transparent at the entitlement layer. | Family-shared sandbox account |
| **Failed restore (nothing to restore)** | `refreshEntitlements` returns empty after explicit `restore()` | Profile alert: "No prior purchases were found on this Apple ID."; Paywall toolbar `Restore` button surfaces "No prior purchases were found." inline hint. Distinct from a *failed* (errored) restore. | Run restore on a fresh Apple ID with no prior purchase |
| **Failed restore (network or auth error)** | `Product.products(for:)` or `Transaction.updates` throws | Profile alert with the error string (stripped of redundant prefixes after the 2026-05-10 polish). Paywall fineprint surfaces the error inline under the product list. | Sandbox account with network blocked |

## What the app must NEVER do

- **Cache `isPro` to UserDefaults.** Entitlement is queried fresh every session via `SubscriptionStore` consuming `Transaction.currentEntitlements`. Caching invites stale-state regressions.
- **Block app startup on entitlement load.** `LifeClockApp.init()` wires the store but the app must usable in Free-state before `loadProducts()` / `refreshEntitlements` resolves. Loading state shows a `LifeClockSpinner(.regular)` inline; nothing modal.
- **Show "Cancelled" status anywhere.** Apple owns the cancellation surface (iOS Settings → Subscriptions). Reflecting cancel in-app reads as confrontational and isn't useful to the user.
- **Re-prompt the paywall when entitlement disappears.** Post-expiry demote is silent — Pro UI hides, but no modal "your subscription ended" sheet pops. The user discovers via the gated affordance (a History row's fog returning, the Plan Editor chip locking) and self-routes to Profile if they want to re-subscribe.
- **Erase historical data on demote.** Existing overrides, baseline, history all stay. Pro is correction-power on *new* writes, not retroactive deletion of past corrections.
- **Treat family-shared as second-class.** The family-shared transaction is verified by StoreKit and is identical to a personal purchase from the app's perspective.

## What the app must always do

- **Auto-dismiss PaywallSheet on `isPro` flip to true.** Handled by `.onChange(of: subscriptions.isPro)` in `PaywallSheet`.
- **Provide an in-app "Manage subscription" row for active Pro users** via `.manageSubscriptionsSheet(isPresented:)`. Lives in `ProfileView.swift` Subscription section. Closes the trust-gap submission-blocker from the 2026-05-12 pro-value audit.
- **Honor Reduce Motion on entitlement-triggered transitions.** The History fog returning after demote should fade with `Motion.Curve.smooth` at `Motion.Duration.beat`, with the standard `reduceMotion ? nil : ...` short-circuit.
- **Strip redundant prefixes from error copy.** "Restore failed: " from `lastError` doubled "Restore failed" in the alert title in the 2026-05-10 polish session — the `restorePurchases` flow now strips this on display.

## Outstanding sandbox-required validation (Q1–Q5 from polish-2026-05-10)

These verifications require real-device + sandbox-account and were queued out of the StoreKit-config simulator polish loop. Run them at the next sandbox session (and add UITest coverage with `SKTestSession` where feasible):

1. **Q1 — Cancel-then-still-in-grace.** Active sandbox sub → Settings cancel → relaunch within synthetic period → Pro UI intact?
2. **Q2 — Post-expiry demote.** After synthetic period elapses → Pro UI hides? History fog returns? No data loss?
3. **Q3 — Refund.** ASC refund a sandbox transaction → app demotes on next foreground? `Transaction.updates` revocation handler fires?
4. **Q4 — Restore from fresh install.** Delete app → reinstall → Restore in Profile → Pro restored same session?
5. **Q5 — Family sharing.** Family-shared sub → app reads as Pro? Promotion / demote on family-sharing changes?

Until these land, the submission-readiness flag remains conditionally yellow regardless of code coverage.

## Cross-references

- Source of truth (entitlements): [`Sources/Services/SubscriptionStore.swift`](../../../products/life-clock-ios/Sources/Services/SubscriptionStore.swift)
- Manage-subs affordance: [`Sources/Features/Profile/ProfileView.swift`](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift) (Subscription section)
- Override service (a key Pro-gated write surface): `Sources/Services/OverrideService.swift`
- Polish session that originated this spec: `polish-2026-05-10-subscription-lifecycle-states.md`
- Plan Editor lifecycle test: `polish-2026-05-07-plan-editor-cancel-restore-and-test-fix.md`
- App Store Connect: § 3.1.2 (auto-renew disclosure) — covered in `legal/terms-of-use.md` § Auto-Renewal Disclosure
- Free/Pro rule: [`MONETIZATION.md`](MONETIZATION.md) § Free vs Pro Rule

## Validation

The subscription lifecycle is fully on-spec when ALL of the following hold:

1. Every Pro-gated feature consults `SubscriptionStore.isPro`. No `UserDefaults` shortcut. No cached enum. (`grep -rE "UserDefaults.*isPro|cached.*Pro" Sources/` returns nothing.)
2. PaywallSheet auto-dismisses on `isPro` flip via `.onChange`.
3. Profile's Subscription section shows the Manage subscription row when `subscriptions.isPro == true`.
4. The five Q1–Q5 sandbox validations have a verified outcome (logged or covered by `SKTestSession` UITests).
5. Restore-purchases returns one of three terminal outcomes: restored / nothing-to-restore / failed-with-error. No silent failure path.
6. `EntitlementGatedWritesTests` continue to pin `.notEntitled` on `applyOverride`, `revertOverride`, and `selectPlanQuest`.

When (1)–(6) hold, the pro-value-readiness flag's subscription-lifecycle preconditions are met.
