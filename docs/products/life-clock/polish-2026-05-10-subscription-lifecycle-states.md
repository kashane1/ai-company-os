# Polish Session — life-clock — 2026-05-10 — subscription-lifecycle-states

## Mode

`freeform-polish`. Observer: design system + memory conventions + App Store Connect §3.1.2 + StoreKit 2 entitlement model.

**Operator brief.** App Store submission rejects on subscription mismatches.
Purchase path is polished; lifecycle states beyond it are largely uncovered.
Drive: (a) restore from fresh install with previously-purchased Apple ID; (b)
cancel-then-grace; (c) post-expiry demote (`OverrideSheet.notEntitled` defensive
path, locked-from `8b32965` a11y ids); (d) refund (`paymentQueue:didRevoke:` —
or its StoreKit 2 equivalent); (e) family sharing.

`LIFECLOCK_SIMULATOR_PRO_DISABLED=1` for the demoted state. Polish anything
Polish-tier; everything that needs StoreKit testing-state queues as Feature-
tier requiring real-device + sandbox-account.

Iteration cap **8** (used 2). Final-check: **yes** — gestural restore + paywall
dismissal.

Seeds:

| Variant | Vars |
|---|---|
| Demoted (Free under DEBUG sim) | `LIFECLOCK_SIMULATOR_PRO_DISABLED=1`, `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_USE_MOCK_HEALTH=1`, `LIFECLOCK_HEALTH_AUTH=authorized`, `LIFECLOCK_INITIAL_TAB=profile\|history` |

> **Recon gotcha (carried from 5/9 profile-section-sweep).** DEBUG simulator
> defaults to **Pro entitled** unless `LIFECLOCK_SIMULATOR_PRO_DISABLED=1` —
> see [SubscriptionStore.swift:100](../../../products/life-clock-ios/Sources/Services/SubscriptionStore.swift). The default sense is still surprising.

## Iterations

| Time | Commit | Type | Tier | Surface | Result |
|---|---|---|---|---|---|
| 01:15 | [`91f3e91`](../../../) | feat | Polish | ProfileView + SubscriptionStore | Three-state restore alert (restored / nothing-to-restore / failed) + `clearLastError()` so a stale prior error can't masquerade as a fresh failure |
| 01:19 | [`f0b4b65`](../../../) | feat | Polish | PaywallSheet | Restore toolbar button: spinner + disabled while in flight; inline "No prior purchases were found" hint when sync succeeds without granting entitlements |

## Stretch decisions (operator review)

None — both fixes are straight Polish-tier App-Store-rejection-risk
remediations with no design alternatives. Auto-dismissal on isPro flip in
PaywallSheet was preserved (existing `.onChange`); a celebratory toast was
deliberately not added since the haptic-on-success already runs.

## Asks

### Resolved this session

None.

### Outstanding (cycle-end batch)

**Q0 — `ProTouchpointsRecon` harness regression (baseline check).**
`testTouchpoint8_RestorePurchasesFromProfile` and
`testFinalAcceptance_PaywallSwipeDownDismissal` both fail on main against a
clean iPhone 17 Pro simulator, and the failure reproduces against the parent
commit's versions of the touched files. Pre-existing harness issue, not
introduced by this PR — but it blocked this session's planned UITest-backed
final-check. Recommend triaging before the sandbox-runs follow-up so those
runs have a green baseline.


The body of the operator's brief is explicitly **Feature-tier requiring real-
device + sandbox-account testing**. None of (b)–(e) are reachable from the
StoreKit-config simulator path; the loop polished what it could from the
demoted state and queues the rest as a single batch:

**Q1 — Cancel-then-still-in-grace.** When a Pro user cancels in iOS Settings
mid-period, does the app continue to show Pro until expiry? StoreKit 2
behavior: `Transaction.currentEntitlements` keeps returning the verified
transaction with `revocationDate == nil` until the period actually ends, so
[`SubscriptionStore.refreshEntitlements`](../../../products/life-clock-ios/Sources/Services/SubscriptionStore.swift) should correctly stay `isPro==true`.
Needs sandbox confirmation. **Setup:** sandbox Apple ID with active sub →
Settings → Apple ID → Subscriptions → Cancel → relaunch app within the
synthetic 5-minute "month" → expect Pro UI intact.

**Q2 — Post-expiry demote.** After the synthetic period elapses, does the
app gracefully demote? Expected: Pro UI hides, History fog returns (verified
manually below in demoted-state goldens), `OverrideSheet.notEntitled` defensive
path engages, locked-from `8b32965` a11y ids stay addressable. The defensive
path is **already covered by [EntitlementGatedWritesTests.swift](../../../products/life-clock-ios/Sources/Tests/EntitlementGatedWritesTests.swift)** (unit), which proves
`applyOverride` / `revertOverride` / `selectPlanQuest` throw `.notEntitled`
without entitlement and that the sheet [catches it and surfaces the per-tone message](../../../products/life-clock-ios/Sources/Features/History/OverrideSheet.swift:71). Real-device confirmation still needed.

**Q3 — Refund / paymentQueue:didRevoke:.** No SK1 observer is wired (StoreKit
1 API). StoreKit 2 delivers revocation through `Transaction.updates`; the
listener task is started in `SubscriptionStore.init` and `handle(_:)` calls
`refreshEntitlements()` which filters `revocationDate != nil` out of
`entitledProductIDs`. Code path looks correct; needs sandbox refund
("Refund a Purchase" via Settings → Apple ID → Purchase History) to confirm
the entitlement actually drops on a running app and on a cold-launch.

**Q4 — Family Sharing.** All three SKUs in
[`Products.storekit`](../../../products/life-clock-ios/Sources/Services/Products.storekit) have `familyShareable: false`. App Store
Connect listings must agree. **Decision needed:** do we want family sharing
on Pro? (Pro / con: wider reach / per-seat ARPU dilution + revocation-via-
organizer surface area to test.) If yes, flip both the .storekit flag and
the App Store Connect IAP toggle, and add a sandbox test for organizer-
revoke.

**Q5 — Test-account & sandbox setup operator-handoff.** None of Q1–Q4 are
reproducible without:

- A sandbox Apple ID created in App Store Connect → Users and Access →
  Sandbox Testers (one per scenario; sandbox accounts can't toggle states
  freely). Recommend three: `lc-renew@`, `lc-cancel@`, `lc-refund@`.
- A real device signed into one of those sandbox IDs (Settings → App Store
  → Sandbox Account at the bottom — NOT the main Apple ID).
- App built in Release configuration or a Debug build with
  `LIFECLOCK_SIMULATOR_PRO_DISABLED` not set (so the dev hatch doesn't
  fake-grant Pro).
- Subscription period scaling for sandbox: 1 month becomes 5 minutes,
  1 year becomes 1 hour. Plan Q1/Q2 testing in those windows.

Recommend the operator open one PR per resolved Q (or a single
`subscription-lifecycle-sandbox-runs.md` log under
`docs/products/life-clock/`) once a sandbox-test session is run.

## Final check (degraded)

`request_access` for computer-use timed out twice in 5 minutes — same failure
mode the 5/9 `profile-section-sweep` log documented. Fell back to:

1. Static screenshot review of the demoted state via `simctl io booted
   screenshot` (linked above).
2. Code review of the new alert + spinner paths.
3. **Attempted UITest verification.** Added a `testTouchpoint8b_RestoreFiresAlert`
   that taps `profile.restore` and asserts one of the three alert titles
   appears. It failed at the post-tap re-existence check. Investigated by
   running the existing `testTouchpoint8_RestorePurchasesFromProfile`
   (reachability-only, no tap) on a clean simulator (`iPhone 17 Pro`,
   erased + rebooted, only-one-booted) — that **also failed** with
   `profile.restore must be reachable for free users` at line 152. To
   confirm not-introduced-by-this-PR, checked out the parent commit's
   versions of ProfileView/PaywallSheet/SubscriptionStore and re-ran T8 —
   **same failure**.

   T8 is broken on main; reverted the new T8b. The polish-tier fixes are
   shipped without an automated assertion. **This is the strongest
   Feature-tier ask of the session** beyond the lifecycle questions: the
   `ProTouchpointsRecon` harness needs a sanity sweep before any future
   subscription-touching polish run can rely on it. Suspected causes
   (un-investigated): `scrollUntilVisible` attempt count too low after the
   5/9 Profile section reorder pushed Subscription further down the form,
   or a NavigationStack toolbar rendering change in the current Xcode
   shifting Form-row visibility.

## Regressions caught

None. Touched surfaces:

- ProfileView Subscription section — visually identical until the user taps
  Restore (the alert is the only new surface).
- PaywallSheet toolbar Restore button — replaces "Restore" text with a
  ProgressView while restoring; otherwise identical.

Goldens captured (demoted state, post-fix):

- [Profile demoted (Subscription section below fold)](screenshots/2026-05-10-profile-demoted.png)
- [History demoted (fog + Pro teaser)](screenshots/2026-05-10-history-demoted-fog.png)

History fog confirms the post-expiry visual matches the demoted-from-fresh
visual — the path Q2 expects to land users on is the same one the loop
polished from.

## A11y identifiers added

- `paywall.restoreEmpty` — the inline "No prior purchases were found" hint
  on `PaywallSheet`. Existing locked-from-`8b32965` ids
  (`profile.upgrade`, `profile.restore`, `paywall.close`, `paywall.restore`,
  `paywall.screen`, `history.foggedUnlock`, `history.row.locked`) were
  re-verified and remain addressable in the demoted state.

## Vision updates

None proposed. The `Decided constraints` section in `vision.md` doesn't speak
to subscription mechanics; the lifecycle questions above are operational, not
visional.

## Next pass

Single ask, owned by operator: run a sandbox session on real device against
Q1–Q4, log to `polish-<date>-subscription-lifecycle-sandbox-runs.md`. The
unit + UI test coverage proves the code path; only the entitlement
state-machine in production StoreKit can confirm end-to-end.

Stretch follow-up: add a UITest that drives `profile.restore` in the
demoted seed and asserts the alert title is one of the three expected
strings. Today's commits ship with no UITest because the alert path is
straightforward and the demoted seed doesn't reach a real Apple ID. Worth
adding once a sandbox harness exists.
