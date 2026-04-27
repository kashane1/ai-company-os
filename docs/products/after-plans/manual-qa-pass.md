# Manual QA Pass: After Plans v1.0

Structured test scenarios for manual QA before App Store submission. Run
these on a physical iPhone via TestFlight against the cloud Supabase
project. Some scenarios require a second person on a second device — those
are flagged.

This is a living checklist. Leave checkboxes empty until the first
TestFlight build is in hand.

Last updated: 2026-04-26

---

## Test Environment

- Device: iPhone running iOS 17.0+
- Network: test on WiFi/cellular **and** in Airplane Mode
- Permissions: After Plans should request **zero** OS permissions on first
  launch (no location, no contacts, no photos, no camera, no notifications)
- Backend: cloud Supabase project (not the local-dev stack used by
  `xcodebuild test`)
- Second device (for join/share scenarios): a second iPhone signed in as a
  different anonymous user is sufficient

---

## 1. First Launch + Onboarding

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 1.1 | Fresh install, launch app | Launches without crash, shows the first onboarding card | |
| 1.2 | Walk through all onboarding cards | Each card renders, Continue/Skip both reachable | |
| 1.3 | Tap Skip on any card | Lands on Home; no card dropped silently | |
| 1.4 | Complete onboarding, kill app, relaunch | Skips onboarding; lands directly on Home | |
| 1.5 | First launch makes zero permission prompts | No location, contacts, photos, camera, mic, or notifications dialog appears | |
| 1.6 | Anonymous auth bootstrap | Profile is created server-side; first name shown in app is non-empty | |

## 2. Context Selection

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 2.1 | Home shows the seeded launch contexts | Context cards render with title, trust note, proximity label | |
| 2.2 | Tap Current Context card | Drills into the context's plan list | |
| 2.3 | Switch between multiple contexts | Feed updates to the selected context's plans | |
| 2.4 | Empty context | "Be the first to start a plan after <context>" empty state shown, not an error | |

## 3. Create Plan — All Three Modes

PlanMode values: `defaultOption`, `openIntent`, `exact`.

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 3.1 | Create a plan in **Default option** mode with a one-line headline | Plan publishes; appears in feed; lifecycle = `open` | |
| 3.2 | Create a plan in **Open intent** mode (no place required) | Plan publishes with the open-intent framing visible; lifecycle = `open` | |
| 3.3 | Create a plan in **Exact** mode with a place set | Plan publishes; place is shown in detail; validation rejects empty place for this mode | |
| 3.4 | Try to publish without a headline | Publish stays disabled; explanatory copy visible | |
| 3.5 | Choose visibility = same-context-only | Plan visible only to others in the same context (verify with second device) | |
| 3.6 | Choose visibility = known-people | Plan visible to known people only (verify with second device) | |
| 3.7 | Choose visibility = invite-only | Plan does NOT appear in any feed; only resolves via direct invite link | |

## 4. Join + Lifecycle Transitions

Some of these need a second device.

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 4.1 | Tap Join on a plan in feed | Lifecycle promotes `open` → `forming`; Join button changes state | |
| 4.2 | Express interest (signal) without joining | Recorded server-side; UI reflects "interested" state | |
| 4.3 | Suggest a place on someone else's plan | Place appears on plan detail; lifecycle promotes `open` → `forming` if applicable | |
| 4.4 | Confirm the plan | Lifecycle goes to `confirmed`; confirm action no longer offered | |
| 4.5 | Mark active | Lifecycle goes to `active`; "wrap" action appears | |
| 4.6 | Wrap the plan | Lifecycle goes to `closed`; plan removed from feed; recap appears in history | |
| 4.7 | Try to join a closed plan | Action not available; plan shows closed state | |
| 4.8 | Try to confirm a plan you have not joined | Action gated correctly per lifecycle/role | |

## 5. Invite + Share — All Three Channels

InviteShareChannel values: `sameContext`, `knownPeople`, `nearbyQR`.

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 5.1 | Open invite share for a plan you host | Share sheet shows the three channels with low-pressure framing copy | |
| 5.2 | Share via **same-context** channel | Records share server-side; share sheet handoff works | |
| 5.3 | Share via **known-people** channel | Records share server-side; share sheet handoff works | |
| 5.4 | Share via **nearby QR** channel | QR code renders and is scannable from a second device's camera | |
| 5.5 | Tap a generated `afterplans://join/<code>` link in Messages on a second device | Opens the app; navigates to the resolved plan | |
| 5.6 | Resolve an invite for a closed plan | "No longer available" copy; no plan detail surfaced | |
| 5.7 | Resolve an invite for a plan you are blocked from | "No longer available" copy (indistinguishable from not-found by design) | |

## 6. Trust + Safety

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 6.1 | Open Safety Center from Profile | Safety center loads with report + block guidance | |
| 6.2 | Open Safety Center from a plan detail | Same safety center reachable inline | |
| 6.3 | Report a plan with a reason and optional note | Report submits; confirmation feedback shown | |
| 6.4 | Report a user with a reason | Report submits; confirmation feedback shown | |
| 6.5 | Block a user | Block applies immediately; that user's plans disappear from feed | |
| 6.6 | Blocked user no longer sees your hosted plans | Verify with second device | |
| 6.7 | Unblock a user from the block list | User reappears in feed if otherwise visible | |
| 6.8 | Closed plans do **not** show share affordances | Detail screen for `closed` plans hides invite/share buttons | |

## 7. Bounded Visibility — End-to-End

These verify the RLS policies on the backend, not just UI. Use two
anonymous users on two devices.

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 7.1 | User A creates a same-context-only plan in context X; User B is not a member of X | User B does not see the plan in any feed | |
| 7.2 | User B becomes a member of context X | User B's feed now includes the plan | |
| 7.3 | User A creates a known-people plan; User B has no shared history with A | User B does not see the plan | |
| 7.4 | After User B joins one of A's plans | User B can now see A's other known-people plans | |
| 7.5 | Invite-only plans do not appear in any feed under any condition | Only invite-link resolution surfaces them | |

## 8. Continuation — Recap + History

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 8.1 | View Activity tab after wrapping a plan | Plan appears with a warm recap line | |
| 8.2 | Recent partners chip row | Shows recent participants from past wrapped plans | |
| 8.3 | Repeat-context detection | A second wrap in the same context surfaces a "you've done this together before" cue | |

## 9. Eligibility

The eligibility posture is "intended for users 17 and older" (see
TRUST_SAFETY_GUARDRAILS.md). The exact gate mechanism is a founder
decision still pending.

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 9.1 | Onboarding age gate (if any is added) | Behaves per founder decision | |

## 10. Privacy Posture (zero-permissions sanity)

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 10.1 | Settings → Privacy & Security → Location Services → After Plans | App not listed (or listed as "Never asked") — no location string declared | |
| 10.2 | Settings → After Plans | No prior permission grants visible because none were requested | |
| 10.3 | Search Info.plist for `*Usage` keys | Only the deep-link CFBundleURLTypes; no permission strings | |

## 11. Network + Edge Cases

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 11.1 | Launch in Airplane Mode | App opens; clear "offline" / retry messaging on feed | |
| 11.2 | Lose network mid-create | Action surfaces a retry path; no silent data loss | |
| 11.3 | Kill app during plan creation | On relaunch, no half-created plan appears in feed | |
| 11.4 | Rapidly double-tap Publish | Only one plan created (idempotency) | |
| 11.5 | Rapidly double-tap Join | Only one participation row (idempotency) | |
| 11.6 | Rotate device | Portrait-locked is fine; UI does not break if rotation enabled | |
| 11.7 | Dark mode | All text readable; brand colors appropriate | |
| 11.8 | Dynamic Type (largest setting) | UI remains usable; no truncated CTAs on critical actions | |

## 12. Deep Links

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 12.1 | Tap `afterplans://join/<code>` in Messages on the test device | App opens, navigates to the plan resolved by `<code>` | |
| 12.2 | Tap `afterplans://join/<unknown-code>` | App opens, shows "no longer available" copy | |
| 12.3 | Tap `afterplans://` (bare scheme) | App opens to a sensible default (Home) | |

---

## Sign-Off

| Role | Name | Date | Result |
|------|------|------|--------|
| QA tester | | | |
| Developer | | | |
| Founder | | | |
