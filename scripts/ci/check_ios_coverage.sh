#!/usr/bin/env bash

set -euo pipefail

RESULT_BUNDLE="${1:-build/ios/FishingLogbook.xcresult}"
TARGET_NAME="${2:-${IOS_COVERAGE_TARGET:-Fishing Logbook.app}}"
MINIMUM="${IOS_COVERAGE_MIN:-}"

if [[ ! -d "$RESULT_BUNDLE" ]]; then
  echo "Expected result bundle at $RESULT_BUNDLE"
  exit 1
fi

report_json="$(xcrun xccov view --report --json "$RESULT_BUNDLE")"
line_coverage="$(
  printf '%s' "$report_json" | jq -r --arg target "$TARGET_NAME" '
    if type == "array" then
      (.[] | select(.name == $target) | .lineCoverage) // empty
    else
      (.targets[]? | select(.name == $target) | .lineCoverage) // empty
    end
  '
)"

if [[ -z "$line_coverage" ]]; then
  line_coverage="$(
    printf '%s' "$report_json" | jq -r '
      if type == "array" then
        .[0].lineCoverage // empty
      else
        .targets[0].lineCoverage // empty
      end
    '
  )"
  TARGET_NAME="$(
    printf '%s' "$report_json" | jq -r '
      if type == "array" then
        .[0].name // empty
      else
        .targets[0].name // empty
      end
    '
  )"
fi

if [[ -z "$line_coverage" || -z "$TARGET_NAME" ]]; then
  echo "Unable to find iOS coverage data in $RESULT_BUNDLE"
  exit 1
fi

coverage_percent="$(python3 -c "print(f'{float($line_coverage) * 100:.2f}')")"
echo "iOS line coverage for $TARGET_NAME: ${coverage_percent}%"

if [[ -z "$MINIMUM" ]]; then
  echo "iOS coverage threshold not enforced in this stage."
  exit 0
fi

if awk -v actual="$coverage_percent" -v minimum="$MINIMUM" 'BEGIN { exit !(actual + 0 >= minimum + 0) }'; then
  echo "iOS coverage meets threshold ${MINIMUM}%."
else
  echo "iOS coverage ${coverage_percent}% is below threshold ${MINIMUM}%."
  exit 1
fi
