# LifeClock signed-text captures — 2026-09-09

Direct, unedited 1320×2868 XCTest screenshots of the tested debug app. The
captured product source is committed at `db184f018a5bd5789d8612fba53f55d1d77245bd`. These replace the
first-day Today illustration in the employer walkthrough; the earlier wrap-up
capture remains dated historical evidence.

Environment: Xcode 26.6 (17F113), XcodeGen 2.45.4, iPhone 17 Pro Max,
iOS 26.5 (23F77), simulator `93443872-9BB2-415C-A036-B12737100D5E`.
The full shared test command passed 452 tests and skipped the three documented
StoreKit cases. App-target line coverage was 68.30%.

The images are the `signed-drivers-light` and `signed-drivers-dark` attachments
from `LifeClockUITests.testSignedEstimateInLightAndDarkAppearance` in
`build/ios/life-clock.xcresult`. The fixture uses `LIFECLOCK_UI_TEST=1`, scenario
`onboarded`, mock HealthKit, authorized mock health state, fixed app date
`2026-09-09T12:00:00Z`, and the respective forced color scheme. The status-bar
clock reflects host capture time. There is no personal or live health data.

Both captures show the signed headline and normal-size driver values. The
native-color regression test resolves positive and negative text against
`systemBackground` and `secondarySystemBackground` in light and dark appearance
and requires at least 4.5:1 contrast in all eight combinations. The old palette
failed the light-appearance cases. Numeric signs and existing accessibility
labels/values remain available; meaning does not depend on hue alone.

The screenshots illustrate positive values. Negative colors are covered by the
native-color test. This is bounded contrast and simulator evidence, not a full
accessibility audit or a measured health outcome.

| File | SHA-256 |
|---|---|
| [today-signed-light.png](today-signed-light.png) | `7d88938b4552d7d5eb244e5d474a4cdce561a4e366ff27043e4c047733895eab` |
| [today-signed-dark.png](today-signed-dark.png) | `bfe6bcd5e048de061b4536b35527a564199c2b4fa0bd2e0a2ada80e89f360f9f` |
