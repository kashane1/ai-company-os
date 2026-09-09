# Life Clock simulator captures — 2026-09-09

These are direct `simctl` screenshots of the tested debug app, captured from
the employer-readiness worktree. The captured app source is committed at
[`89abb681`](https://github.com/kashane1/ai-company-os/commit/89abb68186d8e877a3b0e506bc650550adafcaa4).
They were resized from 1320×2868 to 644×1400; no screen content was edited.

Capture environment: Xcode 26.6 (17F113), XcodeGen 2.45.4, iPhone 17 Pro Max
simulator `5A5E41B4-CD79-42C1-8055-9B8082F0962F`, iOS 26.5 (23F77), light
appearance. The app came from the successful `life-clock.xcresult` build.
`LIFECLOCK_UI_TEST=1` selected an in-memory SwiftData store and mock HealthKit,
so the images contain deterministic fixture data and no personal or live
service data.

## Files

- `today-authorized-first-day.png` — the first-day Today surface with an
  authorized baseline mock Health profile. App clock:
  `LIFECLOCK_FIXED_DATE=2026-09-09T12:00:00Z`; scenario `onboarded`; initial tab
  `today`; no history seeded. SHA-256:
  `f20dab2e3747683dc72385374a0cb87200ca69a1fff584bb6ad13de054294780`.
- `yesterday-wrap-up-day-7.png` — the actual returning-user wrap-up sheet over
  Today after seven seeded habit/snapshot days. The same fixed app clock and
  authorized baseline mock were used with `LIFECLOCK_SEED_STREAK=7` and
  `LIFECLOCK_SEED_SNAPSHOTS=7`. SHA-256:
  `b001d514ef45d8f9c095dc063568683d5422a7a3eeebcaeaea76c266c01b4df1`.

The device status-bar time reflects the host capture time; the app's engine
date was fixed by the fixture above.
