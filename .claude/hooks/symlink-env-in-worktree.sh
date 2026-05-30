#!/usr/bin/env bash
# Symlink gitignored env files from the main repo into a Claude Code worktree.
#
# Worktrees only check out *tracked* files, and .env / .env.local are gitignored
# (see .gitignore), so they are absent in a fresh worktree under
# .claude/worktrees/<name>/. This runs on SessionStart and links them from the
# main checkout so worker sessions in worktrees can read the same secrets.
#
# Idempotent and safe: no-op in the main checkout, no-op if a link already
# exists, and it never fails a session start (always exits 0). The symlink
# targets sit outside the worktree, so git leaves them untracked/ignored.

# Locate the main repo (--git-common-dir points at the main repo's .git, even
# from inside a linked worktree). Bail quietly if we're not in a git repo.
main_git=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
case "$main_git" in
  /*) ;;                          # already absolute (typical inside a worktree)
  *) main_git="$(pwd)/$main_git" ;;  # relative (typical in the main checkout)
esac
main_root=$(cd "$(dirname "$main_git")" 2>/dev/null && pwd) || exit 0
wt_root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0

[ -n "$main_root" ] && [ -n "$wt_root" ] || exit 0

# In the main checkout there is nothing to link.
[ "$main_root" = "$wt_root" ] && exit 0

for f in .env .env.local; do
  if [ -e "$main_root/$f" ] && [ ! -e "$wt_root/$f" ] && [ ! -L "$wt_root/$f" ]; then
    ln -s "$main_root/$f" "$wt_root/$f" 2>/dev/null || true
  fi
done

exit 0
