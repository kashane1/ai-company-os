---
status: pending
priority: p2
issue_id: 027
tags: [code-review, life-clock, legal, app-review]
dependencies: []
---

# Privacy policy needs notification disclosure

## Problem statement

Commit `5b7a403` ships a new user-facing data category:

- `UserProfile.dailyReminderEnabled` (Bool) — opt-in state
- `UserProfile.dailyReminderHour` (Int) — chosen reminder time
- `UNUserNotificationCenter` permission grant for `[.alert, .sound, .badge]`

The privacy policy markdown
(`docs/products/life-clock/legal/privacy-policy.md`) and the live
HTML version at https://kashane1.github.io/life-clock-legal/privacy-policy.html
were last touched in commit `6b4193b` — pre-notifications. Neither
mentions notifications.

App Review Guideline 5.1.1 (Data Collection and Storage) expects
disclosure of *what is collected and stored, including locally*, even
when the data never leaves the device. The privacy policy URL we just
shipped to ASC links here, so this is a real submission gap.

Severity: P2 — non-blocking for code, but blocking for App Store
submission. 30-minute fix.

## Findings

From data-integrity-guardian on commit 5b7a403:

> Privacy policy not updated. `docs/products/life-clock/legal/privacy-policy.md`
> last touched in `6b4193b` (pre-5b7a403). No mention of "notification"
> or "reminder" in the markdown. The 5b7a403 commit shipped a new
> user-facing data category (notification opt-in + scheduled hour
> stored in profile) without disclosure. The live HTML at
> `github.com/kashane1/life-clock-legal` needs the matching edit.

## Proposed solutions

### Option 1 (recommended): Add a one-paragraph disclosure to both surfaces

In `docs/products/life-clock/legal/privacy-policy.md` and the live
HTML, add a section under "Information You Enter Manually":

> **Daily reminder preference.** If you opt in to a daily reminder,
> Life Clock stores your reminder preference (on/off + chosen hour)
> on your device only, alongside your other profile data. Reminder
> notifications are scheduled and delivered **entirely on your iPhone**
> by iOS. We do not send notifications from a server, and we do not
> transmit your reminder preference anywhere. You can change or turn
> off the reminder at any time in Profile → Daily reminder, or in
> iOS Settings → Notifications → Life Clock.

Plus update the "What Data the App Does NOT Touch" list:

> - **No remote push notifications.** Reminders are scheduled
>   entirely on-device via iOS local notifications. We do not send
>   data to Apple's APNs or any push service.

- Pros: Honors the App Review 5.1.1 disclosure expectation; keeps the
  local-first promise explicit; mirrors the same plain-English voice
  the rest of the document uses.
- Cons: Two surfaces to update (markdown + HTML).
- Effort: Small (~30 minutes).
- Risk: None.

### Option 2: Defer

- Pros: No churn now.
- Cons: App Review may reject. The privacy URL is already wired into
  the code (`LifeClockConfiguration.privacyPolicyURL`) and would link
  to a stale page. Eventually has to be done; doing it now is cheap.
- Effort: None now, same later.
- Risk: App-Review rejection.

## Recommended action

Option 1, before any TestFlight build is uploaded. The privacy URL is
pointing to GitHub Pages right now; updating both files is a single
session task.

## Technical details

**Affected files:**

- `docs/products/life-clock/legal/privacy-policy.md` — source markdown.
- The live HTML in the `kashane1/life-clock-legal` repository
  (separate repo, separate clone). Edit `privacy-policy.html` there
  with the equivalent HTML structure used by the rest of the page.

**Not affected:** `terms-of-use.md` / `support.md` / `index.html` —
disclosure belongs in privacy policy.

## Acceptance criteria

- [ ] `docs/products/life-clock/legal/privacy-policy.md` includes a
      "Daily reminder preference" subsection under "Information You
      Enter Manually" matching Option 1's text.
- [ ] The "What Data the App Does NOT Touch" list adds a "No remote
      push notifications" bullet.
- [ ] Live HTML at
      `https://kashane1.github.io/life-clock-legal/privacy-policy.html`
      reflects both edits.
- [ ] "Last updated" date bumped on both surfaces.

## Work log

- 2026-04-30 — Created during `/workflows:review` of commit `5b7a403`.
  Source: data-integrity-guardian agent flagged the disclosure gap.

## Resources

- Source markdown: `docs/products/life-clock/legal/privacy-policy.md`
- Live HTML repo: https://github.com/kashane1/life-clock-legal
- Live URL:
  https://kashane1.github.io/life-clock-legal/privacy-policy.html
- App Review Guideline 5.1.1:
  https://developer.apple.com/app-store/review/guidelines/#data-collection-and-storage
