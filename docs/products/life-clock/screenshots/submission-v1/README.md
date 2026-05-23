# App Store Screenshots — Submission v1

> Captured 2026-05-19 via `AppStoreScreenshotsRecon` UI test on iOS 26.5 simulators.
>
> **Branch:** `submission-prep-life-clock`
> **Fixture:** Day-30 Pro user, Coach tone, baseline Apple Health profile, fixed date 2026-05-15.

## Devices

| Folder | Device | Dimensions | App Store slot |
|---|---|---|---|
| `iphone-69/` | iPhone 17 Pro Max | 1320 × 2868 | 6.9" iPhone (required) |
| `ipad-13/` | iPad Pro 13-inch (M5) | 2064 × 2752 | 13" iPad Pro (required) |

Apple no longer requires 6.5" iPhone or 12.9" iPad if 6.9" + 13" are provided.

## Captions / order

Upload to ASC version page in this order. The filename prefix matches the upload slot.

| # | Filename | App Store caption |
|---|---|---|
| 01 | `01-see-your-life-clock.png` | See your Life Clock |
| 02 | `02-earn-time-with-habits.png` | Earn time with healthy habits |
| 03 | `03-apple-health-updates.png` | Personalize tone, palette, and reminders |
| 04 | `04-find-whats-costing-time.png` | Find what's costing you time |
| 05 | `05-daily-longevity-quests.png` | Complete daily longevity quests |
| 06 | `06-track-healthspan-trend.png` | Track your healthspan trend |

The captions originate from `docs/products/life-clock/APP_STORE_ASO.md` § First screenshots, lightly adapted to fit the actual surfaces the app renders today (post-refactor #3 captures Profile rather than Apple-Health connect, since the connect step is one-time in onboarding).

## Re-capture

```bash
cd products/life-clock-ios

# iPhone 6.9"
xcodebuild test -project LifeClock.xcodeproj -scheme LifeClock \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro Max,OS=26.5' \
  -only-testing:LifeClockUITests/AppStoreScreenshotsRecon

# iPad 13"
xcodebuild test -project LifeClock.xcodeproj -scheme LifeClock \
  -destination 'platform=iOS Simulator,name=iPad Pro 13-inch (M5),OS=26.5' \
  -only-testing:LifeClockUITests/AppStoreScreenshotsRecon
```

Captures land in `/tmp/lifeclock-appstore-screenshots/`. Copy to this folder.

To re-capture a single screen, append `/testCaptureNN<name>` to the `-only-testing` arg.

## Fixture knobs

If you want to test different states for marketing experiments:

| Env | Effect |
|---|---|
| `LIFECLOCK_FORCE_PALETTE=sunset-warm` | Warm sunset palette |
| `LIFECLOCK_SEED_TONE=firm_direct` | Firm/Direct tone (the dramatic register) |
| `LIFECLOCK_HEALTH_PROFILE=poor` + `LIFECLOCK_SEED_BAD_DAY=1` | Bad-day visual |
| `LIFECLOCK_FORCE_PAYWALL=1` | Land on PaywallSheet |

See `products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift` for the full list.
