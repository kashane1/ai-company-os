#!/usr/bin/env bash
# PostToolUse hook for Write: regenerate the XcodeGen project whenever a
# .swift file is written under products/<product>/Sources/, so newly-added
# files end up in the .xcodeproj without remembering to run `xcodegen
# generate`. Idempotent (no-op when nothing changed). Silent on no match.
#
# Stdin: Claude Code PostToolUse JSON. Extracts .tool_input.file_path,
# matches against products/<product>/Sources/... pattern, runs xcodegen
# in that product dir if a project.yml lives there.

set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Read stdin; tolerate empty input.
input="$(cat || true)"
[ -z "$input" ] && exit 0

file_path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""' 2>/dev/null || echo "")"
[ -z "$file_path" ] && exit 0

# Only act on .swift files
case "$file_path" in
  *.swift) ;;
  *) exit 0 ;;
esac

# Match /products/<product>/Sources/... and capture <product>
if [[ "$file_path" =~ /products/([^/]+)/Sources/ ]]; then
  product="${BASH_REMATCH[1]}"
else
  exit 0
fi

# Resolve product root: everything up to and including /products/<product>
product_root="${file_path%%/Sources/*}"
project_yml="$product_root/project.yml"

[ -f "$project_yml" ] || exit 0
command -v xcodegen >/dev/null 2>&1 || exit 0

# Run xcodegen quietly. Failures don't block the tool; just print to stderr.
(cd "$product_root" && xcodegen generate >/dev/null) || \
  echo "xcodegen-on-swift-write: regeneration failed in $product_root" >&2

exit 0
