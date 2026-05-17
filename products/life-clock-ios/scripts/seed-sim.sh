#!/usr/bin/env bash
#
# seed-sim.sh — build, install, and launch Life Clock on the Simulator with
# DEBUG seed data so the Future tab is populated without hand-recording days.
#
# Why this exists: SwiftData resets the store on an unmigrated @Model change,
# so hand-recorded multi-day data vanishes on every schema tweak. The app
# already ships a DEBUG-only seeder (LifeClockLaunchConfiguration
# .seedInitialStateIfNeeded) driven entirely by env vars. This script
# uninstalls first so the (idempotent, empty-store-only) seeder reliably
# fires, then installs and launches with the seed env applied.
#
# Usage:
#   scripts/seed-sim.sh              # 60 days of history, iPhone 17 Pro
#   scripts/seed-sim.sh 30           # 30 days of history
#   scripts/seed-sim.sh 60 "iPhone 17"   # custom simulator
#   NO_BUILD=1 scripts/seed-sim.sh   # skip xcodebuild, just wipe + relaunch
#
# Env knobs are documented in products/life-clock-ios/README.md and
# Sources/App/LifeClockLaunchConfiguration.swift.

set -euo pipefail

DAYS="${1:-60}"
SIM_NAME="${2:-iPhone 17 Pro}"
SCHEME="LifeClock"
BUNDLE_ID="io.aicompanyos.products.lifeclock"

cd "$(dirname "$0")/.."

echo "==> Booting simulator: $SIM_NAME"
xcrun simctl boot "$SIM_NAME" 2>/dev/null || true
open -a Simulator || true

if [[ "${NO_BUILD:-0}" != "1" ]]; then
  echo "==> Building $SCHEME for Simulator"
  xcodebuild build \
    -scheme "$SCHEME" \
    -configuration Debug \
    -destination "platform=iOS Simulator,name=$SIM_NAME" \
    -derivedDataPath build/DerivedData \
    -quiet
fi

APP_PATH=$(find build/DerivedData/Build/Products/Debug-iphonesimulator \
  -maxdepth 1 -name "LifeClock.app" -print -quit 2>/dev/null || true)
if [[ -z "$APP_PATH" ]]; then
  echo "ERROR: LifeClock.app not found. Run without NO_BUILD=1 first." >&2
  exit 1
fi

echo "==> Wiping prior install (clears SwiftData store so the seeder fires)"
xcrun simctl uninstall "$SIM_NAME" "$BUNDLE_ID" 2>/dev/null || true

echo "==> Installing $APP_PATH"
xcrun simctl install "$SIM_NAME" "$APP_PATH"

echo "==> Launching with $DAYS days of seeded history"
# simctl has no --environment flag; vars prefixed SIMCTL_CHILD_ in the
# caller's environment are forwarded (stripped of the prefix) to the app.
SIMCTL_CHILD_LIFECLOCK_JUMP_TO=futureFull \
SIMCTL_CHILD_LIFECLOCK_SEED_SNAPSHOTS="$DAYS" \
SIMCTL_CHILD_LIFECLOCK_FUTURE_TAB_UNLOCKED=1 \
xcrun simctl launch --terminate-running-process "$SIM_NAME" "$BUNDLE_ID"

echo "==> Done. Future tab is populated with $DAYS days."
