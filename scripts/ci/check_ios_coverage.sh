#!/usr/bin/env bash

set -euo pipefail

RESULT_BUNDLE="${1:-build/ios/FishingLogbook.xcresult}"
TARGET_NAME="${2:-${IOS_COVERAGE_TARGET:-Fishing Logbook.app}}"
MINIMUM="${IOS_COVERAGE_MIN:-}"
SCHEME_NAME="${IOS_COVERAGE_SCHEME:-}"
SUMMARY_FILE="${IOS_COVERAGE_SUMMARY_FILE:-}"

if [[ ! -d "$RESULT_BUNDLE" ]]; then
  echo "Expected result bundle at $RESULT_BUNDLE"
  exit 1
fi

report_json="$(xcrun xccov view --report --json "$RESULT_BUNDLE")"
target_json="$(
  printf '%s' "$report_json" | jq -c --arg target "$TARGET_NAME" '
    if type == "array" then
      (.[] | select(.name == $target)) // empty
    else
      (.targets[]? | select(.name == $target)) // empty
    end
  '
)"

if [[ -z "$target_json" ]]; then
  target_json="$(
    printf '%s' "$report_json" | jq -r '
      if type == "array" then
        .[0] // empty
      else
        .targets[0] // empty
      end
    '
  )"
fi

if [[ -z "$target_json" ]]; then
  echo "Unable to find iOS coverage data in $RESULT_BUNDLE"
  exit 1
fi

TARGET_NAME="$(printf '%s' "$target_json" | jq -r '.name // empty')"
line_coverage="$(printf '%s' "$target_json" | jq -r '.lineCoverage // empty')"
covered_lines="$(printf '%s' "$target_json" | jq -r '.coveredLines // empty')"
executable_lines="$(printf '%s' "$target_json" | jq -r '.executableLines // empty')"

if [[ -z "$line_coverage" || -z "$TARGET_NAME" || -z "$covered_lines" || -z "$executable_lines" ]]; then
  echo "Unable to read iOS coverage fields in $RESULT_BUNDLE"
  exit 1
fi

coverage_percent="$(python3 -c "print(f'{float($line_coverage) * 100:.2f}')")"
echo "iOS line coverage for $TARGET_NAME: ${coverage_percent}%"

if [[ -n "$SUMMARY_FILE" ]]; then
  mkdir -p "$(dirname "$SUMMARY_FILE")"
  result_bundle_path="$(cd "$(dirname "$RESULT_BUNDLE")" && pwd)/$(basename "$RESULT_BUNDLE")"
  jq -n \
    --arg scheme "$SCHEME_NAME" \
    --arg target_name "$TARGET_NAME" \
    --arg xcresult_path "$result_bundle_path" \
    --argjson covered_lines "$covered_lines" \
    --argjson executable_lines "$executable_lines" \
    --arg percentage "$coverage_percent" \
    '{
      scheme: $scheme,
      target_name: $target_name,
      xcresult_path: $xcresult_path,
      covered_lines: $covered_lines,
      executable_lines: $executable_lines,
      percentage: ($percentage | tonumber)
    }' > "$SUMMARY_FILE"
  echo "Wrote iOS coverage summary to $SUMMARY_FILE"
fi

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
