#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRODUCT="catchbook"
SIMULATOR_ID="${IOS_SIMULATOR_ID:-}"

usage() {
  cat <<'USAGE'
Usage: ./scripts/test_ios.sh [--product catchbook|life-clock|after-plans]

Runs one product's hermetic iOS test scheme on an available iPhone simulator.
The After Plans Supabase integration project is a separate opt-in workflow
documented in products/after-plans-ios/README.md.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --product)
      [[ $# -ge 2 ]] || { echo "--product requires a value" >&2; exit 2; }
      PRODUCT="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$PRODUCT" in
  catchbook)
    IOS_ROOT="$ROOT/products/catchbook-ios"
    PROJECT_NAME="Catchbook"
    SCHEME_NAME="Catchbook"
    COVERAGE_TARGET="Catchbook.app"
    ;;
  life-clock)
    IOS_ROOT="$ROOT/products/life-clock-ios"
    PROJECT_NAME="LifeClock"
    SCHEME_NAME="LifeClock"
    COVERAGE_TARGET="LifeClock.app"
    ;;
  after-plans)
    IOS_ROOT="$ROOT/products/after-plans-ios"
    PROJECT_NAME="AfterPlans"
    SCHEME_NAME="AfterPlans"
    COVERAGE_TARGET="AfterPlans.app"
    ;;
  *)
    echo "Unsupported product: $PRODUCT" >&2
    usage >&2
    exit 2
    ;;
esac

BUILD_ROOT="$ROOT/build/ios"
SUMMARY_ROOT="$ROOT/build/coverage"
RESULT_BUNDLE="$BUILD_ROOT/$PRODUCT.xcresult"
DERIVED_DATA="$BUILD_ROOT/$PRODUCT-DerivedData"
SUMMARY_FILE="$SUMMARY_ROOT/$PRODUCT-ios-coverage-summary.json"

mkdir -p "$BUILD_ROOT" "$SUMMARY_ROOT"
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
  echo "Unable to find an available iPhone simulator." >&2
  exit 1
fi

if ! xcrun simctl list devices available -j | jq -e --arg id "$SIMULATOR_ID" '
  [.devices[][] | select(.udid == $id and .isAvailable)] | length == 1
' >/dev/null; then
  echo "IOS_SIMULATOR_ID is not an available simulator: $SIMULATOR_ID" >&2
  exit 1
fi

echo "Testing $PRODUCT ($SCHEME_NAME) on simulator $SIMULATOR_ID"
xcodebuild test \
  -project "$IOS_ROOT/$PROJECT_NAME.xcodeproj" \
  -scheme "$SCHEME_NAME" \
  -destination "id=$SIMULATOR_ID" \
  -derivedDataPath "$DERIVED_DATA" \
  -resultBundlePath "$RESULT_BUNDLE" \
  -enableCodeCoverage YES

export IOS_COVERAGE_SCHEME="$SCHEME_NAME"
export IOS_COVERAGE_SUMMARY_FILE="$SUMMARY_FILE"
"$ROOT/scripts/ci/check_ios_coverage.sh" "$RESULT_BUNDLE" "$COVERAGE_TARGET"
