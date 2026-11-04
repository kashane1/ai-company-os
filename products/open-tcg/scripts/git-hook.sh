#!/bin/sh
# Git hook: restart the OpenTCG background jobs when git changes the code they run.
# The KeepAlive jobs re-read stores.toml every cycle but keep the Python they
# started with, so a commit that changes both breaks them until they restart.
# Installed into the repository's hooks by `scripts/launchd.sh install`.
#   git-hook.sh post-commit | post-merge | post-checkout | post-rewrite [hook args]
set -u

here=$(cd "$(dirname "$0")" && pwd -P)
hook=$1
shift

# Act only in the checkout the jobs run from. Every worktree of this repository
# shares the hooks, and a commit in another worktree doesn't change the jobs' code.
jobs_dir=""
for plist in "$HOME"/Library/LaunchAgents/com.ai-company-os.open-tcg.*.plist; do
  jobs_dir=$(plutil -extract WorkingDirectory raw "$plist" 2>/dev/null) && break
done
[ -n "$jobs_dir" ] || exit 0
top=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
checkout_dir=$(cd "$top/products/open-tcg" 2>/dev/null && pwd -P) || exit 0
[ "$checkout_dir" = "$(cd "$jobs_dir" 2>/dev/null && pwd -P)" ] || exit 0

# A rebase runs post-checkout and post-commit along the way; post-rewrite covers it once.
is_rebasing() {
  [ -d "$(git rev-parse --git-path rebase-merge)" ] || [ -d "$(git rev-parse --git-path rebase-apply)" ]
}

case $hook in
  post-commit)
    is_rebasing && exit 0
    old=$(git rev-parse -q --verify HEAD~1) || exit 0
    new=HEAD
    ;;
  post-merge)
    old=ORIG_HEAD
    new=HEAD
    ;;
  post-checkout)
    # Third argument 1 = branch checkout; 0 = file checkout, which changes no commit.
    [ "${3:-0}" = 1 ] || exit 0
    is_rebasing && exit 0
    old=$1
    new=$2
    ;;
  post-rewrite)
    # An amend already ran post-commit.
    [ "${1:-}" = rebase ] || exit 0
    old=ORIG_HEAD
    new=HEAD
    ;;
  *)
    exit 0
    ;;
esac

job_definitions=$(git diff --name-only "$old" "$new" -- \
  ':(glob)products/open-tcg/scripts/*.plist' products/open-tcg/scripts/launchd.sh 2>/dev/null)
if [ -n "$job_definitions" ]; then
  echo "open-tcg: job definitions changed; run products/open-tcg/scripts/launchd.sh install" >&2
fi

code_changes=$(git diff --name-only "$old" "$new" -- \
  products/open-tcg/radar ':(glob)products/open-tcg/*.toml' 2>/dev/null)
[ -n "$code_changes" ] || exit 0
echo "open-tcg: radar code changed; restarting background jobs" >&2
"$here/launchd.sh" restart >&2 || echo "open-tcg: restart failed; run products/open-tcg/scripts/launchd.sh restart" >&2
exit 0
