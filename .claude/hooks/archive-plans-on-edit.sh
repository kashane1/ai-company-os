#!/usr/bin/env bash
# PostToolUse hook for Write/Edit: when a plan under docs/plans/ is edited,
# auto-archive any plan whose frontmatter status became finished (completed,
# shipped, superseded, ...). This makes "finished plan -> docs/plans/archive/"
# happen in real time, the moment an agent flips a plan's status — keeping the
# docs/plans/ working set small for token-efficient globbing.
#
# Idempotent (no-op when nothing is finished). Silent on no match. Never blocks
# the tool — failures only print to stderr.
#
# Stdin: Claude Code PostToolUse JSON. Extracts .tool_input.file_path, acts only
# when it is under docs/plans/ (not the archive/ subdir).

set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

input="$(cat || true)"
[ -z "$input" ] && exit 0

file_path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""' 2>/dev/null || echo "")"
[ -z "$file_path" ] && exit 0

# Only act on plan files in docs/plans/ but not already in docs/plans/archive/.
case "$file_path" in
  *docs/plans/archive/*) exit 0 ;;
  *docs/plans/*.md) ;;
  *) exit 0 ;;
esac

project_dir="${CLAUDE_PROJECT_DIR:-.}"
script="$project_dir/scripts/docs/archive_plans.py"
[ -f "$script" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

(cd "$project_dir" && python3 "$script") || \
  echo "archive-plans-on-edit: archiver failed" >&2

exit 0
