#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IOS_ROOT="$ROOT/products/fishing-logbook-ios"
BUILD_ROOT="$ROOT/build/ios"
RESULT_BUNDLE="$BUILD_ROOT/FishingLogbook.xcresult"
DERIVED_DATA="$BUILD_ROOT/DerivedData"
SIMULATOR_ID="${IOS_SIMULATOR_ID:-}"

mkdir -p "$BUILD_ROOT"
rm -rf "$RESULT_BUNDLE" "$DERIVED_DATA"

xcodegen --spec "$IOS_ROOT/project.yml" --project "$IOS_ROOT" --quiet

if [[ -z "$SIMULATOR_ID" ]]; then
  SIMULATOR_ID="$(
    xcrun simctl list devices available -j | jq -r '
      .devices
      | to_entries
      | sort_by(.key)
      | reverse
      | map(.value[] | select(.isAvailable and (.name | startswith("iPhone"))))
      | .[0].udid // empty
    '
  )"
fi

if [[ -z "$SIMULATOR_ID" ]]; then
  echo "Unable to find an available iPhone simulator."
  exit 1
fi

xcodebuild test \
  -project "$IOS_ROOT/FishingLogbook.xcodeproj" \
  -scheme FishingLogbook \
  -destination "id=$SIMULATOR_ID" \
  -derivedDataPath "$DERIVED_DATA" \
  -resultBundlePath "$RESULT_BUNDLE" \
  -enableCodeCoverage YES

"$ROOT/scripts/ci/check_ios_coverage.sh" "$RESULT_BUNDLE"
